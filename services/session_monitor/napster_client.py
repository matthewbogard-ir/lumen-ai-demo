"""Napster Spaces API Client for session analytics."""

import requests
from typing import List, Optional
from dataclasses import dataclass
import logging

from .config import NAPSTER_API_BASE_URL, EXPERIENCE_ID, secrets

logger = logging.getLogger(__name__)


@dataclass
class TranscriptEntry:
    """A single entry in a conversation transcript."""
    text: str
    role: str
    timestamp: int


@dataclass
class SessionTranscript:
    """Full transcript for a session."""
    session_id: str
    entries: List[TranscriptEntry]

    def to_conversation_text(self) -> str:
        lines = []
        for entry in self.entries:
            speaker = "AI Assistant" if entry.role == "agent" else "Customer"
            lines.append(f"{speaker}: {entry.text}")
        return "\n".join(lines)

    def has_meaningful_content(self) -> bool:
        user_messages = [e for e in self.entries if e.role == "user"]
        return len(user_messages) >= 1 and len(self.entries) >= 2

    def get_first_timestamp(self) -> Optional[int]:
        if self.entries and len(self.entries) > 0:
            return self.entries[0].timestamp
        return None


class NapsterSpacesClient:
    """Client for Napster Spaces API analytics endpoints."""

    def __init__(self, api_key: str = None, experience_id: str = EXPERIENCE_ID, base_url: str = NAPSTER_API_BASE_URL):
        if api_key is None:
            api_key = secrets.NAPSTER_API_KEY
        self.api_key = api_key
        self.experience_id = experience_id
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        })

    def get_session_ids(self) -> List[str]:
        url = f"{self.base_url}/{self.experience_id}/analytics/sessions"
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                session_ids = data.get("sessionIds", [])
                logger.info(f"Retrieved {len(session_ids)} sessions")
                return session_ids
            else:
                logger.error(f"API returned unsuccessful response: {data}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get sessions: {e}")
            return []

    def get_transcript(self, session_id: str) -> Optional[SessionTranscript]:
        url = f"{self.base_url}/{self.experience_id}/analytics/transcripts/{session_id}"
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get("success") and "transcript" in data:
                entries = [
                    TranscriptEntry(
                        text=entry.get("text", ""),
                        role=entry.get("role", "unknown"),
                        timestamp=entry.get("timeStamp", 0)
                    )
                    for entry in data["transcript"]
                ]
                transcript = SessionTranscript(session_id=session_id, entries=entries)
                logger.info(f"Retrieved transcript for session {session_id[:20]}... ({len(entries)} entries)")
                return transcript
            else:
                logger.warning(f"No transcript data for session {session_id[:20]}...")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get transcript for session {session_id[:20]}...: {e}")
            return None

    def get_all_transcripts(self, session_ids: List[str]) -> List[SessionTranscript]:
        transcripts = []
        for session_id in session_ids:
            transcript = self.get_transcript(session_id)
            if transcript and transcript.has_meaningful_content():
                transcripts.append(transcript)
        return transcripts

    def get_transcripts_with_status(self, session_ids: List[str]) -> tuple:
        transcripts_with_content = []
        sessions_with_no_data = []
        sessions_with_no_meaningful_content = []

        for session_id in session_ids:
            transcript = self.get_transcript(session_id)
            if transcript is None:
                sessions_with_no_data.append(session_id)
            elif not transcript.has_meaningful_content():
                sessions_with_no_meaningful_content.append(session_id)
            else:
                transcripts_with_content.append(transcript)

        return transcripts_with_content, sessions_with_no_data, sessions_with_no_meaningful_content
