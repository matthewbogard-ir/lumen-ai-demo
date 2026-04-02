#!/usr/bin/env python3
"""
Session Monitor Service for Longines AI Brand Consultant.

This service:
1. Periodically checks for new sessions from Napster Spaces API
2. Gets transcripts for completed consultations
3. Summarizes conversations using Azure OpenAI (watch consultation insights)
4. Sends email reports with customer analytics and newsletter CTA

Usage:
    python -m services.session_monitor.main --once
    python -m services.session_monitor.main --daemon
    python -m services.session_monitor.main --api
"""

import argparse
import logging
import sys
import time
from datetime import datetime

from .config import CHECK_INTERVAL_SECONDS, secrets
from .napster_client import NapsterSpacesClient
from .state_manager import StateManager
from .summarizer import AzureOpenAISummarizer
from .email_sender import EmailSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


class SessionMonitor:
    """Main service that monitors sessions and sends analytics reports."""

    def __init__(self):
        logger.info("Initializing Longines Session Monitor Service...")
        self.napster_client = NapsterSpacesClient()
        self.state_manager = StateManager()
        self.summarizer = AzureOpenAISummarizer()
        self.email_sender = EmailSender()
        logger.info("Session Monitor Service initialized successfully")

    def _group_summaries_by_profile(self, summaries):
        from .api import get_profile_for_session

        groups = {}
        for summary in summaries:
            profile_id = get_profile_for_session(summary.session_id)
            if profile_id not in groups:
                groups[profile_id] = []
            groups[profile_id].append(summary)
        return groups

    def _build_transcript_from_submitted(self, session_id, entries):
        """Build a SessionTranscript from frontend-submitted transcript data."""
        from .napster_client import TranscriptEntry, SessionTranscript
        transcript_entries = []
        for entry in entries:
            transcript_entries.append(TranscriptEntry(
                text=entry.get("text", ""),
                role=entry.get("role", "unknown"),
                timestamp=entry.get("timestamp", 0)
            ))
        return SessionTranscript(session_id=session_id, entries=transcript_entries)

    def check_and_notify(self) -> int:
        logger.info("=" * 60)
        logger.info(f"Starting session check at {datetime.now().isoformat()}")

        from .api import get_linked_session_ids, get_submitted_transcript
        all_session_ids = get_linked_session_ids()
        if not all_session_ids:
            logger.info("No linked sessions found in storage")
            return 0

        logger.info(f"Found {len(all_session_ids)} linked session(s) in storage")

        new_session_ids = self.state_manager.get_unprocessed(all_session_ids)
        if not new_session_ids:
            logger.info("No new sessions to process")
            return 0

        logger.info(f"Found {len(new_session_ids)} new session(s) to process")

        # Try submitted transcripts first, fall back to Napster API
        transcripts = []
        sessions_no_data = []
        sessions_no_content = []

        for session_id in new_session_ids:
            submitted = get_submitted_transcript(session_id)
            if submitted:
                transcript = self._build_transcript_from_submitted(session_id, submitted)
                if transcript.has_meaningful_content():
                    transcripts.append(transcript)
                    logger.info(f"Using submitted transcript for session {session_id[:20]}... ({len(submitted)} messages)")
                else:
                    sessions_no_content.append(session_id)
            else:
                # Fall back to Napster API
                api_transcript = self.napster_client.get_transcript(session_id)
                if api_transcript is None:
                    sessions_no_data.append(session_id)
                elif not api_transcript.has_meaningful_content():
                    sessions_no_content.append(session_id)
                else:
                    transcripts.append(api_transcript)

        for session_id in sessions_no_content:
            self.state_manager.mark_processed(session_id)

        if sessions_no_content:
            logger.info(f"Marked {len(sessions_no_content)} session(s) as processed (no meaningful content)")

        if sessions_no_data:
            logger.info(f"{len(sessions_no_data)} session(s) have no transcript data yet - will retry later")

        if not transcripts:
            logger.info("No transcripts with meaningful content to process")
            return 0

        logger.info(f"Retrieved {len(transcripts)} transcript(s) with meaningful content")

        summaries = self.summarizer.summarize_multiple(transcripts)
        if not summaries:
            logger.warning("Failed to generate any summaries")
            return 0

        logger.info(f"Generated {len(summaries)} summary(ies)")

        # Group by profile and send to correct recipients
        from .api import get_email_for_profile

        grouped_by_profile = self._group_summaries_by_profile(summaries)

        grouped_by_email = {}
        for profile_id, profile_summaries in grouped_by_profile.items():
            if not profile_id:
                logger.warning(f"Skipping {len(profile_summaries)} session(s) - no profile_id linked")
                continue

            recipient_email = get_email_for_profile(profile_id)
            if not recipient_email:
                logger.warning(f"Skipping {len(profile_summaries)} session(s) for profile {profile_id} - no email")
                continue

            if recipient_email not in grouped_by_email:
                grouped_by_email[recipient_email] = []
            grouped_by_email[recipient_email].extend(profile_summaries)

        emails_sent = 0
        for recipient_email, email_summaries in grouped_by_email.items():
            logger.info(f"Sending {len(email_summaries)} summary(ies) to {recipient_email}")
            if self.email_sender.send_notification(email_summaries, recipient_email=recipient_email):
                emails_sent += 1

        for transcript in transcripts:
            self.state_manager.mark_processed(transcript.session_id)

        if emails_sent > 0:
            logger.info(f"Successfully processed {len(summaries)} session(s) and sent {emails_sent} email(s)")
        else:
            logger.warning(f"Processed {len(summaries)} session(s) but no emails could be sent")

        return len(summaries)

    def run_daemon(self, interval: int = CHECK_INTERVAL_SECONDS):
        logger.info(f"Starting daemon mode with {interval} second interval")
        while True:
            try:
                self.check_and_notify()
            except Exception as e:
                logger.error(f"Error during check cycle: {e}", exc_info=True)
            logger.info(f"Sleeping for {interval} seconds until next check...")
            time.sleep(interval)


def main():
    import os

    parser = argparse.ArgumentParser(description="Longines Session Monitor Service")
    parser.add_argument("--api", action="store_true", help="Run as HTTP API server")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=CHECK_INTERVAL_SECONDS)
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8080)))

    args = parser.parse_args()

    if args.api:
        from .api import run_server
        logger.info("Starting in API server mode...")
        try:
            run_server(host="0.0.0.0", port=args.port)
        except KeyboardInterrupt:
            logger.info("Shutting down API server...")
        return

    if not secrets.AZURE_OPENAI_API_KEY:
        logger.error("Azure OpenAI API key is required. Set AZURE_OPENAI_API_KEY env var.")
        sys.exit(1)

    try:
        monitor = SessionMonitor()
        if args.daemon:
            monitor.run_daemon(args.interval)
        else:
            processed = monitor.check_and_notify()
            logger.info(f"Completed. Processed {processed} session(s)")
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
