"""State management for tracking processed sessions."""

import json
import os
import logging
from typing import Set, Optional, List, Dict
from datetime import datetime

from .config import (
    PROCESSED_SESSIONS_FILE, AZURE_STORAGE_ACCOUNT_URL,
    AZURE_STORAGE_CONTAINER, BLOB_STATE_PREFIX
)

logger = logging.getLogger(__name__)


class StateManager:
    """Manages state of processed sessions to avoid duplicate notifications."""

    def __init__(self, state_file: str = PROCESSED_SESSIONS_FILE):
        self.state_file = state_file
        self._processed_sessions: Set[str] = set()
        self._blob_service_client = None
        self._container_client = None

        if AZURE_STORAGE_ACCOUNT_URL:
            self._init_azure_blob()

        self._load_state()

    def _init_azure_blob(self):
        try:
            from azure.identity import DefaultAzureCredential
            from azure.storage.blob import BlobServiceClient
            credential = DefaultAzureCredential()
            self._blob_service_client = BlobServiceClient(
                account_url=AZURE_STORAGE_ACCOUNT_URL,
                credential=credential
            )
            self._container_client = self._blob_service_client.get_container_client(
                AZURE_STORAGE_CONTAINER
            )
            logger.info(f"Initialized Azure Blob Storage: {AZURE_STORAGE_ACCOUNT_URL}/{AZURE_STORAGE_CONTAINER}")
        except ImportError:
            logger.warning("azure-storage-blob not installed, using local file storage")
        except Exception as e:
            logger.error(f"Failed to initialize Azure Blob Storage: {e}")

    def _load_state(self):
        data = None
        if self._container_client:
            data = self._load_from_blob()
        if data is None:
            data = self._load_from_file()
        if data:
            self._processed_sessions = set(data.get("processed_sessions", []))
            logger.info(f"Loaded {len(self._processed_sessions)} processed sessions from state")
        else:
            logger.info("No existing state found, starting fresh")

    def _load_from_blob(self) -> Optional[Dict]:
        try:
            blob_name = f"{BLOB_STATE_PREFIX}processed_sessions.json"
            blob_client = self._container_client.get_blob_client(blob_name)
            content = blob_client.download_blob().readall().decode("utf-8")
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to load state from Azure Blob: {e}")
        return None

    def _load_from_file(self) -> Optional[Dict]:
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load state from file: {e}")
        return None

    def _save_state(self):
        data = {
            "processed_sessions": list(self._processed_sessions),
            "last_updated": datetime.utcnow().isoformat()
        }
        if self._container_client:
            self._save_to_blob(data)
        self._save_to_file(data)

    def _save_to_blob(self, data: dict):
        try:
            blob_name = f"{BLOB_STATE_PREFIX}processed_sessions.json"
            blob_client = self._container_client.get_blob_client(blob_name)
            blob_client.upload_blob(
                json.dumps(data, indent=2),
                overwrite=True
            )
            logger.info(f"Saved state to Azure Blob: {blob_name}")
        except Exception as e:
            logger.error(f"Failed to save state to Azure Blob: {e}")

    def _save_to_file(self, data: dict):
        try:
            os.makedirs(os.path.dirname(self.state_file) or ".", exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved state to file: {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state to file: {e}")

    def is_processed(self, session_id: str) -> bool:
        return session_id in self._processed_sessions

    def mark_processed(self, session_id: str):
        self._processed_sessions.add(session_id)
        self._save_state()

    def get_unprocessed(self, session_ids: List[str]) -> List[str]:
        unprocessed = [sid for sid in session_ids if not self.is_processed(sid)]
        logger.info(f"Found {len(unprocessed)} unprocessed sessions out of {len(session_ids)}")
        return unprocessed

    def get_processed_count(self) -> int:
        return len(self._processed_sessions)
