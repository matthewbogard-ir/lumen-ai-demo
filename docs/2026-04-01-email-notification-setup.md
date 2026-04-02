# Email Notification System Setup Guide

How to set up the automatic follow-up email system for a new demo. This covers deploying the session monitor API and processor, wiring the frontend, and testing.

---

## Prerequisites

- Azure CLI (`az`) logged in to the Prototyping subscription
- Docker installed and running
- Access to the shared container registry: `acrlonginesdemo.azurecr.io`
- The demo frontend already deployed as an Azure Container App
- A Napster Spaces experience ID for the demo

## Overview

The email system has three parts:

1. **Frontend (index.html)** - Captures the user's email, links sessions to profiles, and submits conversation transcripts to the session monitor API.
2. **Session Monitor API** - Receives data from the frontend, stores it, and exposes a `/process` endpoint to trigger email generation.
3. **Session Processor** - Runs on a loop (every 5 minutes by default), automatically processing new sessions and sending emails.

The flow:
```
User enters email -> Frontend registers email with API
User starts conversation -> Frontend links session ID to profile
Conversation messages come in -> Frontend submits transcript to API
Processor runs (or you curl /process) -> Summarizes transcript via Azure OpenAI -> Sends email via Gmail SMTP
```

---

## Step 1: Set the SESSION_MONITOR_API_URL in the Frontend

In `index.html`, find this line:

```javascript
const SESSION_MONITOR_API_URL = '';
```

You will set this to the session monitor API URL after deploying it in step 3. Leave it blank for now if you haven't deployed yet.

The frontend code already handles:
- `POST /api/register-email` - called when user enters their email in the modal
- `POST /api/link-session` - called when the Napster SDK fires `NAPSTER_SPACES_SESSION_STARTED`
- `POST /api/submit-transcript` - called to send conversation transcript directly (this bypasses the Napster API entirely)

**Important:** The `/api/submit-transcript` endpoint is critical. It means the session monitor does NOT need Napster API access to read transcripts -- the frontend sends them directly. This avoids API key permission issues.

---

## Step 2: Build the Session Monitor API Image

From the repo root:

```bash
# Login to the container registry
az acr login --name acrlonginesdemo

# Build the API image
docker build --platform linux/amd64 \
  -f services/session_monitor/Dockerfile.api \
  -t acrlonginesdemo.azurecr.io/<demo-name>-session-monitor-api:v1 .

# Push it
docker push acrlonginesdemo.azurecr.io/<demo-name>-session-monitor-api:v1
```

**Always build from the current code** in the repo. Do NOT reuse old Docker images from other demos -- they may be missing endpoints like `/api/submit-transcript`.

---

## Step 3: Deploy the Session Monitor API

```bash
az containerapp create \
  --name <demo-name>-session-monitor-api \
  --resource-group <your-resource-group> \
  --environment $(az containerapp show --name <demo-frontend-app> --resource-group <your-resource-group> --query "properties.managedEnvironmentId" -o tsv) \
  --image acrlonginesdemo.azurecr.io/<demo-name>-session-monitor-api:v1 \
  --registry-server acrlonginesdemo.azurecr.io \
  --registry-identity system \
  --target-port 8080 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 1 \
  --env-vars \
    NAPSTER_API_KEY=<your-napster-api-key> \
    AZURE_OPENAI_API_KEY=<your-azure-openai-api-key> \
    AZURE_OPENAI_ENDPOINT=https://eastus.api.cognitive.microsoft.com/ \
    AZURE_OPENAI_DEPLOYMENT=gpt-4o \
    GMAIL_APP_PASSWORD=<your-gmail-app-password> \
    EXPERIENCE_ID=<your-base64-experience-id> \
    AZURE_STORAGE_CONTAINER=state \
    AZURE_STORAGE_ACCOUNT_URL=https://stdemolongines.blob.core.windows.net/ \
    SENDER_EMAIL=demo-sales@napster.com \
    SMTP_USERNAME=marcin.gierlak@napster.com \
    RECIPIENT_EMAIL=<fallback-email-if-no-modal> \
  -o table
```

This will output the FQDN. Copy it.

---

## Step 4: Update the Frontend with the API URL

Now go back to `index.html` and set:

```javascript
const SESSION_MONITOR_API_URL = 'https://<demo-name>-session-monitor-api.<env-id>.westus2.azurecontainerapps.io';
```

Rebuild and redeploy the frontend container.

---

## Step 5: Deploy the Session Processor (Auto-Polling)

This is optional but recommended. It runs in a loop and automatically sends emails without needing to curl.

```bash
# Build the processor image
docker build --platform linux/amd64 \
  -f services/session_monitor/Dockerfile.processor \
  -t acrlonginesdemo.azurecr.io/<demo-name>-session-processor:v1 .

docker push acrlonginesdemo.azurecr.io/<demo-name>-session-processor:v1

az containerapp create \
  --name <demo-name>-session-processor \
  --resource-group <your-resource-group> \
  --environment $(az containerapp show --name <demo-frontend-app> --resource-group <your-resource-group> --query "properties.managedEnvironmentId" -o tsv) \
  --image acrlonginesdemo.azurecr.io/<demo-name>-session-processor:v1 \
  --registry-server acrlonginesdemo.azurecr.io \
  --registry-identity system \
  --ingress internal \
  --target-port 8080 \
  --min-replicas 1 \
  --max-replicas 1 \
  --env-vars \
    NAPSTER_API_KEY=<your-napster-api-key> \
    AZURE_OPENAI_API_KEY=<your-azure-openai-api-key> \
    AZURE_OPENAI_ENDPOINT=https://eastus.api.cognitive.microsoft.com/ \
    AZURE_OPENAI_DEPLOYMENT=gpt-4o \
    GMAIL_APP_PASSWORD=<your-gmail-app-password> \
    EXPERIENCE_ID=<your-base64-experience-id> \
    AZURE_STORAGE_CONTAINER=state \
    AZURE_STORAGE_ACCOUNT_URL=https://stdemolongines.blob.core.windows.net/ \
    SENDER_EMAIL=demo-sales@napster.com \
    SMTP_USERNAME=marcin.gierlak@napster.com \
    RECIPIENT_EMAIL=<fallback-email> \
    CHECK_INTERVAL_SECONDS=300 \
  -o table
```

Note: `--ingress internal` because this doesn't need public access. `--min-replicas 1` so it's always running.

---

## Step 6: Test

1. Open the deployed demo site
2. Enter your email in the modal
3. Have a conversation with the avatar
4. Either wait 5 minutes for the processor, or manually trigger:

```bash
curl -X POST https://<demo-name>-session-monitor-api.<env-id>.westus2.azurecontainerapps.io/process
```

Expected response: `{"success": true, "sessions_processed": N}`

---

## Troubleshooting

### "Processed 0 sessions"
- Check that `SESSION_MONITOR_API_URL` is not empty in index.html
- Check the browser console Network tab for failed requests to the session monitor
- Check logs: `az containerapp logs show --name <api-name> --resource-group <rg> --tail 50`
- Look for `POST /api/link-session` and `POST /api/submit-transcript` in the logs

### "Email configuration incomplete"
- Make sure `SENDER_EMAIL`, `SMTP_USERNAME`, and `GMAIL_APP_PASSWORD` env vars are set
- Add them: `az containerapp update --name <api-name> --resource-group <rg> --set-env-vars SENDER_EMAIL=demo-sales@napster.com SMTP_USERNAME=marcin.gierlak@napster.com`

### "401 Unauthorized" on transcript fetch
- This means the Napster API key doesn't have access to the experience
- **This is fine** as long as the frontend is submitting transcripts via `/api/submit-transcript`
- If you see this error but sessions are still processing, it's because it fell back to the submitted transcripts successfully

### Old Docker image missing endpoints
- If `/api/submit-transcript` returns 404, the Docker image is outdated
- **Always build from current repo code**, never reuse images from other demos
- Rebuild: `docker build --platform linux/amd64 -f services/session_monitor/Dockerfile.api -t <image>:<tag> .`

---

## Environment Variables Reference

| Variable | Description | Example |
|---|---|---|
| EXPERIENCE_ID | Base64 Napster Spaces experience ID | `YmFlZDM0ZTct...` |
| NAPSTER_API_KEY | Napster Spaces API key | `47112013-debf-...` |
| AZURE_OPENAI_API_KEY | Azure OpenAI key for GPT-4o summarization | `DdFF4ot8k...` |
| AZURE_OPENAI_ENDPOINT | Azure OpenAI endpoint URL | `https://eastus.api.cognitive.microsoft.com/` |
| AZURE_OPENAI_DEPLOYMENT | Model deployment name | `gpt-4o` |
| GMAIL_APP_PASSWORD | Gmail app password for SMTP | `bptxmmem...` |
| SENDER_EMAIL | From address on emails | `demo-sales@napster.com` |
| SMTP_USERNAME | Gmail account for SMTP auth | `marcin.gierlak@napster.com` |
| RECIPIENT_EMAIL | Fallback recipient (override) | `you@company.com` |
| AZURE_STORAGE_ACCOUNT_URL | Blob storage for persistent state | `https://stdemolongines.blob.core.windows.net/` |
| AZURE_STORAGE_CONTAINER | Blob container name | `state` |
| CHECK_INTERVAL_SECONDS | Processor polling interval | `300` (5 min) |

---

## Lumens Demo Specific Values

- **Experience ID:** `YmFlZDM0ZTctZWE5My00MTY3LTg1MzgtNTcwOGQ3MDZlMWY0OmE1ODdhNDhmLTdiYTQtNGQ3ZC1hOGNkLWM4YWMxYjE3NTM0ZQ==`
- **Frontend URL:** `https://ai-lumens-demo.mangostone-16490d2b.westus2.azurecontainerapps.io`
- **Session Monitor API:** `https://lumens-session-monitor-api.mangostone-16490d2b.westus2.azurecontainerapps.io`
- **Resource Group:** `rg-ai-lumens-demo`
- **Container Registry:** `acrlonginesdemo.azurecr.io`
