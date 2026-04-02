"""Configuration for Longines Session Monitor Service."""

import os
import logging

logger = logging.getLogger(__name__)


def _get_secret(secret_id: str, env_var: str = None) -> str:
    """Get a secret from environment variable, file mount, or Azure Key Vault."""
    if env_var:
        value = os.environ.get(env_var, "")
        if value:
            return value

    secret_path = f"/secrets/{secret_id}"
    if os.path.exists(secret_path):
        try:
            with open(secret_path, "r") as f:
                return f.read().strip()
        except Exception as e:
            logger.warning(f"Failed to read secret from {secret_path}: {e}")

    vault_url = os.environ.get("AZURE_KEY_VAULT_URL")
    if vault_url:
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=vault_url, credential=credential)
            secret = client.get_secret(secret_id)
            return secret.value
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Failed to access Azure Key Vault for {secret_id}: {e}")

    return ""


# Napster Spaces API Configuration
NAPSTER_API_BASE_URL = "https://spaces-api.napsterai.dev/v1/experiences"

EXPERIENCE_ID = os.environ.get(
    "EXPERIENCE_ID",
    "YmFlZDM0ZTctZWE5My00MTY3LTg1MzgtNTcwOGQ3MDZlMWY0OjEyY2ExYTIxLWE2YWYtNDdjYi1iODE4LTgzZmYzYmE4YjFkMA=="
)


# Sensitive Credentials
def get_napster_api_key() -> str:
    return _get_secret("napster-api-key", "NAPSTER_API_KEY")

def get_azure_openai_api_key() -> str:
    return _get_secret("azure-openai-api-key", "AZURE_OPENAI_API_KEY")

def get_gmail_app_password() -> str:
    return _get_secret("gmail-app-password", "GMAIL_APP_PASSWORD")


# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

# Email Configuration
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "demo-sales@napster.com")
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "marcin.gierlak@napster.com")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "")

# Brand Configuration
BRAND_NAME = "Longines"
BRAND_TAGLINE = "Elegance is an Attitude"
BRAND_SUPPORT = "longines.com/en-us/contact"

# Service Configuration
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL_SECONDS", "300"))
PROCESSED_SESSIONS_FILE = os.environ.get("PROCESSED_SESSIONS_FILE", "/tmp/processed_sessions.json")

# Azure Blob Storage Configuration
AZURE_STORAGE_ACCOUNT_URL = os.environ.get("AZURE_STORAGE_ACCOUNT_URL", "")
AZURE_STORAGE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER", "state")
BLOB_STATE_PREFIX = "session_monitor/"


class _SecretConfig:
    _napster_api_key = None
    _azure_openai_api_key = None
    _gmail_app_password = None

    @property
    def NAPSTER_API_KEY(self) -> str:
        if self._napster_api_key is None:
            self._napster_api_key = get_napster_api_key()
        return self._napster_api_key

    @property
    def AZURE_OPENAI_API_KEY(self) -> str:
        if self._azure_openai_api_key is None:
            self._azure_openai_api_key = get_azure_openai_api_key()
        return self._azure_openai_api_key

    @property
    def SENDER_APP_PASSWORD(self) -> str:
        if self._gmail_app_password is None:
            self._gmail_app_password = get_gmail_app_password()
        return self._gmail_app_password


secrets = _SecretConfig()
