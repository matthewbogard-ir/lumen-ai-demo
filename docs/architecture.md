# Longines AI Boutique Demo — Architecture & Infrastructure

## Overview

A web-based AI brand consultant demo for Longines (Swatch Group). An AI-powered avatar assists users in exploring the Longines watch catalog through natural conversation, displaying product cards and side-by-side comparisons in real time. The system captures conversation transcripts and sends lead summary emails after each session.

**Live URL:** https://ai-longines-demo.purplebush-d6b18060.westus2.azurecontainerapps.io/

---

## System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     User's Browser                       │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  index.html  │  │ Napster SDK  │  │  watches.json  │  │
│  │  (App Logic) │  │  (WebRTC)    │  │  (25 watches)  │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────────┘  │
│         │                 │                               │
│         │     ┌───────────┴───────────┐                  │
│         │     │  AI Avatar (WebRTC)   │                  │
│         │     │  Speech ↔ Text        │                  │
│         │     │  Function Calls       │                  │
│         │     └───────────┬───────────┘                  │
└─────────┼─────────────────┼──────────────────────────────┘
          │                 │
          │ POST transcripts│ WebRTC stream
          ▼                 ▼
┌─────────────────┐  ┌─────────────────────┐
│ Session Monitor │  │  Napster Spaces API  │
│ (Container App) │  │  (Avatar backend)    │
│                 │  │                      │
│ /api/register   │  │  - Experience config │
│ /api/transcript │  │  - Knowledge base    │
│ /process        │  │    (8 PDFs, 51.6MB)  │
│                 │  │  - Persona prompt    │
│ Summarize w/    │  │  - Scenario prompt   │
│ Azure OpenAI    │  └─────────────────────┘
│ Send via Gmail  │
└─────────────────┘
```

---

## Infrastructure

### Azure Resources

| Resource | Type | SKU / Spec | Region | Purpose |
|----------|------|------------|--------|---------|
| `ai-longines-demo` | Container App | 0.5 vCPU, 1GB RAM, 0-10 replicas | West US 2 | Frontend (nginx + static files) |
| `longines-session-monitor` | Container App | 0.25 vCPU, 0.5GB RAM, 1 replica (always-on) | West US 2 | Lead summary API |
| `ailonginesdemo` | Container Registry | Basic SKU | West US 2 | Docker image storage |
| `oai-demo-nike` | Azure OpenAI | GPT-4o deployment | East US | Conversation summarization |
| `ai-longines-demo-env` | Container Apps Environment | Consumption plan | West US 2 | Shared environment |

**Resource Group:** `rg-ai-longines-demo`
**Subscription:** `7b4a0809-1ba8-4eeb-921c-693ded3b7702`

### Estimated Monthly Azure Cost

| Resource | Estimated Cost | Notes |
|----------|---------------|-------|
| Container App (frontend) | ~$0-5/mo | Scales to 0 when idle (consumption plan) |
| Container App (session monitor) | ~$15-20/mo | Always-on (minReplicas: 1), 0.25 vCPU |
| Container Registry (Basic) | ~$5/mo | Fixed cost for Basic SKU |
| Azure OpenAI (GPT-4o) | ~$1-5/mo | Only used when /process is triggered |
| **Total** | **~$21-30/mo** | Mostly idle; spikes only during demos |

**To monitor costs:**
- Azure Portal → Cost Management + Billing → Cost Analysis
- Filter by resource group: `rg-ai-longines-demo`
- Direct link: https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/costanalysis

**To reduce costs when not demoing:**
- Scale session monitor to 0: `az containerapp update --name longines-session-monitor --resource-group rg-ai-longines-demo --min-replicas 0`
- Frontend already scales to 0 automatically

### External Services

| Service | Account | Purpose | Cost |
|---------|---------|---------|------|
| Napster Spaces | API key in .env.local | AI avatar (WebRTC, speech, knowledge base) | Per Napster contract |
| Gmail SMTP | matthew.bogard@napster.com | Lead summary email delivery | Free (Google Workspace) |
| GitHub | theinfinitereality/ai-nike-demo | Source code (branch: longines-demo) | Free |

---

## Application Logic

### 1. Page Load & Initialization

```
Page Load
  ├─ Load watches.json (25 watches, 5 collections)
  ├─ Render background (main-watches-bg.png — Longines website screenshot)
  ├─ Show email gate modal
  └─ Wait for user email submission
```

### 2. Email Gate & Avatar Start

When the user enters their email and clicks "Begin Experience":

1. Email stored in `agentEmail`
2. Profile ID generated: `profile_{timestamp}_{randomString}`
3. POST to session monitor `/api/register-email`
4. Modal hidden, avatar container revealed
5. Napster Spaces SDK initialized with experience ID
6. Avatar appears and greets the user

### 3. Conversation & Watch Matching

The avatar communicates via WebRTC. When it mentions a watch, it triggers a function call (`fetch-site-results`) that the frontend intercepts:

**Matching Pipeline — 7-Tier Fuzzy Search:**

| Tier | Strategy | Example |
|------|----------|---------|
| 1 | Exact full name | "The Longines Master Collection Moon Phase 40mm" |
| 2 | Exact short name (strips "The Longines" prefix) | "Master Collection Moon Phase 40mm" |
| 3 | Substring match (longest name wins) | "Moon Phase" in name |
| 4 | Reference number | "L2.909.4.78.3" |
| 5 | Slug match | "master-collection-moon-phase" |
| 5.5 | Keyword priority (distinctive terms in name) | "flyback" → Spirit Flyback, "gmt" → HydroConquest GMT |
| 6 | Collection match with keyword refinement | "Spirit" collection + "zulu" → Spirit Zulu Time |
| 7 | Weighted fuzzy scoring | HIGH_VALUE_TERMS score 3x |

**Comparison Detection:**
- Query split on: "vs", "versus", "compared to", "or", "and"
- Second watch lookup excludes the first to prevent duplicates
- Displayed side-by-side in a modal overlay

### 4. Product Display

- **Single watch:** Full-screen modal with image, specs table, price, description, link to longines.com
- **Comparison:** Same modal, two cards in a responsive grid
- **Auto-replace:** New product requests replace the current modal without needing to close it first

### 5. Transcript Capture & Lead Summary

```
During conversation:
  ├─ SDK onData callback captures user + assistant messages
  ├─ Messages added to conversationTranscript array
  ├─ POST to /api/submit-transcript every 30 seconds
  └─ Final POST on page unload (sendBeacon)

After demo (manual trigger):
  $ curl -X POST https://longines-session-monitor.purplebush-d6b18060.westus2.azurecontainerapps.io/process

  ├─ Session monitor retrieves all unprocessed sessions
  ├─ Summarizes conversation with Azure OpenAI GPT-4o
  ├─ Sends lead summary email via Gmail SMTP
  └─ Clears processed sessions from memory
```

**Note:** Session data is stored in-memory. Container restarts clear all data.

---

## Watch Catalog

25 watches across 5 collections, stored in `data/watches.json`:

| Collection | Count | Price Range | Example |
|------------|-------|-------------|---------|
| Master Collection | 5 | $2,100 - $3,200 | Moon Phase 40mm, Chronograph 40mm |
| Conquest (HydroConquest) | 5 | $1,700 - $2,600 | HydroConquest 41mm, GMT 41mm |
| Spirit | 5 | $2,350 - $3,250 | Spirit 40mm, Flyback 42mm, Zulu Time 42mm |
| Elegance | 5 | $1,050 - $2,200 | DolceVita 23.3x37mm, PrimaLuna 30mm |
| Heritage | 5 | $2,050 - $3,500 | Legend Diver 36mm, Chronograph 1946 |

Each entry includes: name, collection, slug, description, specs (reference, calibre, case, water resistance, crystal, dial color, power reserve, functions), price, image URL, and product page URL.

7 watches use a generic HydroConquest fallback image.

---

## Knowledge Base

8 PDFs uploaded to the Napster Spaces experience as the avatar's knowledge base:

| File | Size |
|------|------|
| 1LONGINEScombined-compressed.pdf | 1.4 MB |
| 2LONGINES-combined-compressed.pdf | 7.7 MB |
| 3LONGINES-combined-compressed.pdf | 3.0 MB |
| 4LONGINES-combined-compressed.pdf | 16.8 MB |
| 5LONGINES-combined-compressed.pdf | 21.7 MB |
| 6LONGINES-combined-compressed.pdf | 487 KB |
| 7LONGINES-combined-compressed.pdf | 10.8 MB |
| 8Longines_EN-compressed.pdf | 354 KB |
| **Total** | **51.6 MB** |

Located at: `/napster-ai-suite/watch-product-pdfs/`

---

## Deployment

### Build & Deploy Commands

```bash
# From ai-nike-demo/ directory

# 1. Build container image
az acr build --registry ailonginesdemo \
  --image ai-longines-demo:latest \
  --file Dockerfile .

# 2. Deploy to Container App
az containerapp update \
  --name ai-longines-demo \
  --resource-group rg-ai-longines-demo \
  --image ailonginesdemo.azurecr.io/ai-longines-demo:latest
```

### Container Secrets (Session Monitor)

Configured via Azure CLI, not in source:
- `GMAIL_APP_PASSWORD` — Google Workspace app password
- `SMTP_USERNAME` — matthew.bogard@napster.com
- `AZURE_OPENAI_API_KEY` — For GPT-4o summarization
- `AZURE_OPENAI_ENDPOINT` — https://eastus.api.cognitive.microsoft.com/
- `NAPSTER_API_KEY` — Napster Spaces API access

Local secrets stored in `scripts/.env.local` (gitignored).

### Dockerfile

```dockerfile
FROM nginx:alpine
COPY nginx-cloudrun.conf /etc/nginx/nginx.conf
COPY index.html /usr/share/nginx/html/index.html
COPY main-watches-bg.png /usr/share/nginx/html/main-watches-bg.png
COPY sdk/ /usr/share/nginx/html/sdk/
COPY data/ /usr/share/nginx/html/data/
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
```

### Local Development

```bash
cd ai-nike-demo
python3 -m http.server 8080
# Open http://localhost:8080
```

---

## Key File Inventory

| File | Purpose |
|------|---------|
| `index.html` | Entire frontend application (~1,665 lines) |
| `main-watches-bg.png` | Background image (Longines website screenshot) |
| `data/watches.json` | Watch catalog (25 entries) |
| `sdk/napster-spaces-sdk.umd.js` | Napster avatar SDK (2.6 MB) |
| `sdk/napster-spaces-sdk.css` | SDK styles (681 KB) |
| `Dockerfile` | Container build instructions |
| `nginx-cloudrun.conf` | Nginx server configuration |
| `scripts/update_longines_prompt.py` | Avatar prompt update script |
| `scripts/.env.local` | Local secrets (gitignored) |
| `docs/demo-flows.md` | 6 predictable demo flows |
| `docs/longines-v2-spec.md` | V2 feature spec & task tracker |
| `docs/architecture.md` | This document |

---

## Git

- **Repository:** https://github.com/theinfinitereality/ai-nike-demo
- **Branch:** `longines-demo`
- **Experimental branch:** `longines-iframe-background-experiment` (live iframe background — works locally but broken on deploy)
