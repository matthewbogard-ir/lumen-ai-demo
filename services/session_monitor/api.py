"""
Simple API for Longines Session Monitor Service.

Provides endpoints for:
- Registering demo user email (recipient for analytics reports)
- Mapping session IDs to profiles
- Health check
- Triggering session processing
"""

import os
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from typing import Optional, Dict

from .config import AZURE_STORAGE_ACCOUNT_URL, AZURE_STORAGE_CONTAINER, BLOB_STATE_PREFIX

logger = logging.getLogger(__name__)

EMAILS_FILE = os.environ.get("EMAILS_FILE", "/tmp/registered_emails.json")
SESSION_EMAILS_FILE = os.environ.get("SESSION_EMAILS_FILE", "/tmp/session_customer_emails.json")
TRANSCRIPTS_FILE = os.environ.get("TRANSCRIPTS_FILE", "/tmp/submitted_transcripts.json")


def _get_container_client():
    """Get Azure Blob container client (lazy init)."""
    if not AZURE_STORAGE_ACCOUNT_URL:
        return None
    try:
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient
        credential = DefaultAzureCredential()
        blob_service = BlobServiceClient(
            account_url=AZURE_STORAGE_ACCOUNT_URL,
            credential=credential
        )
        return blob_service.get_container_client(AZURE_STORAGE_CONTAINER)
    except Exception as e:
        logger.warning(f"Failed to get Azure Blob container client: {e}")
        return None


def _load_blob_json(blob_name: str) -> Optional[dict]:
    """Load JSON from Azure Blob Storage."""
    container = _get_container_client()
    if not container:
        return None
    try:
        blob_client = container.get_blob_client(blob_name)
        content = blob_client.download_blob().readall().decode("utf-8")
        return json.loads(content)
    except Exception as e:
        logger.warning(f"Failed to load {blob_name} from Azure Blob: {e}")
    return None


def _save_blob_json(blob_name: str, data: dict):
    """Save JSON to Azure Blob Storage."""
    container = _get_container_client()
    if not container:
        return
    try:
        blob_client = container.get_blob_client(blob_name)
        blob_client.upload_blob(json.dumps(data, indent=2), overwrite=True)
    except Exception as e:
        logger.warning(f"Failed to save {blob_name} to Azure Blob: {e}")


def load_emails() -> dict:
    data = _load_blob_json(f"{BLOB_STATE_PREFIX}registered_emails.json")
    if data:
        return data

    try:
        if os.path.exists(EMAILS_FILE):
            with open(EMAILS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load emails from file: {e}")

    return {"emails": [], "primary": None}


def save_emails(data: dict):
    _save_blob_json(f"{BLOB_STATE_PREFIX}registered_emails.json", data)

    try:
        os.makedirs(os.path.dirname(EMAILS_FILE) or ".", exist_ok=True)
        with open(EMAILS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save emails to file: {e}")


def register_email(email: str, profile_id: str = None) -> bool:
    if not email or "@" not in email:
        return False

    data = load_emails()
    if "profiles" not in data:
        data["profiles"] = {}

    if email not in data["emails"]:
        data["emails"].append(email)

    data["primary"] = email

    if profile_id:
        from datetime import datetime
        data["profiles"][profile_id] = {
            "email": email,
            "created_at": datetime.now().isoformat()
        }

    save_emails(data)
    logger.info(f"Registered email: {email}")
    return True


def get_email_for_profile(profile_id: str) -> Optional[str]:
    data = load_emails()
    profiles = data.get("profiles", {})
    profile = profiles.get(profile_id)
    if profile:
        return profile.get("email")
    return None


def get_primary_email() -> Optional[str]:
    data = load_emails()
    return data.get("primary")


def get_all_emails() -> list:
    data = load_emails()
    return data.get("emails", [])


# Session mapping functions

def load_session_emails() -> Dict[str, str]:
    data = _load_blob_json(f"{BLOB_STATE_PREFIX}session_customer_emails.json")
    if data:
        return data

    try:
        if os.path.exists(SESSION_EMAILS_FILE):
            with open(SESSION_EMAILS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load session emails from file: {e}")

    return {}


def save_session_emails(data: Dict[str, str]):
    _save_blob_json(f"{BLOB_STATE_PREFIX}session_customer_emails.json", data)

    try:
        os.makedirs(os.path.dirname(SESSION_EMAILS_FILE) or ".", exist_ok=True)
        with open(SESSION_EMAILS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save session emails to file: {e}")


def link_session_to_profile(session_id: str, profile_id: str) -> bool:
    if not session_id or not profile_id:
        return False

    from datetime import datetime
    data = load_session_emails()

    if session_id in data and isinstance(data[session_id], dict):
        data[session_id]["profile_id"] = profile_id
    else:
        data[session_id] = {
            "customer_email": None,
            "profile_id": profile_id,
            "created_at": datetime.now().isoformat()
        }
    save_session_emails(data)
    logger.info(f"Linked session {session_id[:20]}... to profile {profile_id}")
    return True


def get_customer_email(session_id: str) -> Optional[str]:
    data = load_session_emails()
    entry = data.get(session_id)
    if isinstance(entry, dict):
        return entry.get("customer_email")
    return entry


def get_profile_for_session(session_id: str) -> Optional[str]:
    data = load_session_emails()
    entry = data.get(session_id)
    if isinstance(entry, dict) and entry.get("profile_id"):
        return entry.get("profile_id")
    return None


def get_linked_session_ids() -> list:
    data = load_session_emails()
    linked_sessions = []
    for session_id, entry in data.items():
        if isinstance(entry, dict) and entry.get("profile_id"):
            linked_sessions.append(session_id)
    return linked_sessions


# Submitted transcript functions

def load_transcripts() -> dict:
    data = _load_blob_json(f"{BLOB_STATE_PREFIX}submitted_transcripts.json")
    if data:
        return data

    try:
        if os.path.exists(TRANSCRIPTS_FILE):
            with open(TRANSCRIPTS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load transcripts from file: {e}")

    return {}


def save_transcripts(data: dict):
    _save_blob_json(f"{BLOB_STATE_PREFIX}submitted_transcripts.json", data)

    try:
        os.makedirs(os.path.dirname(TRANSCRIPTS_FILE) or ".", exist_ok=True)
        with open(TRANSCRIPTS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save transcripts to file: {e}")


def submit_transcript(session_id: str, profile_id: str, transcript: list) -> bool:
    if not session_id or not transcript:
        return False

    data = load_transcripts()
    data[session_id] = {
        "profile_id": profile_id,
        "transcript": transcript,
        "submitted_at": __import__("datetime").datetime.now().isoformat()
    }
    save_transcripts(data)
    logger.info(f"Stored transcript for session {session_id[:20]}... ({len(transcript)} messages)")

    # Also ensure session is linked to profile
    if profile_id:
        link_session_to_profile(session_id, profile_id)

    return True


def get_submitted_transcript(session_id: str) -> Optional[list]:
    data = load_transcripts()
    entry = data.get(session_id)
    if entry:
        return entry.get("transcript")
    return None


class APIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the API."""

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self._send_json(200, {"status": "ok"})

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._send_json(200, {"status": "healthy", "service": "longines-session-monitor"})

        elif parsed.path == "/api/emails":
            emails = get_all_emails()
            primary = get_primary_email()
            self._send_json(200, {"emails": emails, "primary": primary, "count": len(emails)})

        elif parsed.path == "/api/session-emails":
            session_emails = load_session_emails()
            self._send_json(200, {"session_emails": session_emails, "count": len(session_emails)})

        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/register-email":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode()
                data = json.loads(body) if body else {}

                email = data.get("email", "").strip().lower()
                profile_id = data.get("profile_id", "").strip() or None

                if register_email(email, profile_id):
                    self._send_json(200, {"success": True, "message": f"Email {email} registered", "profile_id": profile_id})
                else:
                    self._send_json(400, {"success": False, "error": "Invalid email address"})
            except Exception as e:
                logger.error(f"Error registering email: {e}")
                self._send_json(500, {"error": str(e)})

        elif parsed.path == "/api/link-session":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode()
                data = json.loads(body) if body else {}

                session_id = data.get("session_id", "").strip()
                profile_id = data.get("profile_id", "").strip()

                if link_session_to_profile(session_id, profile_id):
                    self._send_json(200, {"success": True, "message": "Session linked to profile"})
                else:
                    self._send_json(400, {"success": False, "error": "Invalid session_id or profile_id"})
            except Exception as e:
                logger.error(f"Error linking session: {e}")
                self._send_json(500, {"error": str(e)})

        elif parsed.path == "/api/submit-transcript":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode()
                data = json.loads(body) if body else {}

                session_id = data.get("session_id", "").strip()
                profile_id = data.get("profile_id", "").strip()
                transcript = data.get("transcript", [])

                if submit_transcript(session_id, profile_id, transcript):
                    self._send_json(200, {"success": True, "message": f"Transcript stored ({len(transcript)} messages)"})
                else:
                    self._send_json(400, {"success": False, "error": "Invalid session_id or empty transcript"})
            except Exception as e:
                logger.error(f"Error submitting transcript: {e}")
                self._send_json(500, {"error": str(e)})

        elif parsed.path in ("/", "/process"):
            try:
                from .main import SessionMonitor
                logger.info("Processing sessions triggered via HTTP POST...")
                monitor = SessionMonitor()
                processed = monitor.check_and_notify()
                self._send_json(200, {"success": True, "sessions_processed": processed})
            except Exception as e:
                logger.error(f"Error processing sessions: {e}")
                self._send_json(500, {"error": str(e)})

        else:
            self._send_json(404, {"error": "Not found"})

    def log_message(self, format, *args):
        logger.info(f"{self.address_string()} - {format % args}")


def run_server(host: str = "0.0.0.0", port: int = 8080):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    server = HTTPServer((host, port), APIHandler)
    logger.info(f"Starting Longines Session Monitor API on {host}:{port}")
    logger.info("Endpoints:")
    logger.info("  GET  /health              - Health check")
    logger.info("  POST /api/register-email  - Register demo user email with profile_id")
    logger.info("  POST /api/link-session    - Link Napster session to demo profile")
    logger.info("  GET  /api/emails          - Get registered emails")
    logger.info("  GET  /api/session-emails  - Get all session mappings")
    logger.info("  POST / or /process        - Trigger session processing")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down API server...")
        server.shutdown()


if __name__ == "__main__":
    run_server()
