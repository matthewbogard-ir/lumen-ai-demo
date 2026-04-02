# Deployment Guide

## Azure Container Registry

**Registry:** `acrlonginesdemo.azurecr.io`
**Image:** `acrlonginesdemo.azurecr.io/ai-longines-demo`

> WARNING: There is also `ailonginesdemo.azurecr.io` which is a DIFFERENT registry.
> The container app pulls from `acrlonginesdemo`. Do NOT push to `ailonginesdemo`.

### Login

```bash
az acr login --name acrlonginesdemo
```

## Azure Container Apps

**Resource Group:** `rg-ai-longines-demo`

| Service | Container App Name | Min Replicas |
|---|---|---|
| Frontend | `ai-longines-demo` | 1 |
| Session Monitor | `longines-session-monitor` | 1 |

## Build & Deploy (Frontend)

Must build for `linux/amd64` (not ARM — local Mac builds won't work on Azure).

```bash
cd ai-nike-demo

# Build and push in one step
docker buildx build --platform linux/amd64 \
  -t acrlonginesdemo.azurecr.io/ai-longines-demo:YOUR_TAG \
  --push .

# Deploy
az containerapp update \
  --name ai-longines-demo \
  --resource-group rg-ai-longines-demo \
  --image acrlonginesdemo.azurecr.io/ai-longines-demo:YOUR_TAG
```

## Verify Deployment

Always verify the correct image is running after deploy:

```bash
az containerapp revision list \
  --name ai-longines-demo \
  --resource-group rg-ai-longines-demo \
  --query "[].{name:name, active:properties.active, image:properties.template.containers[0].image}" \
  -o table
```

## Deployed URL

`https://ai-longines-demo.purplebush-d6b18060.westus2.azurecontainerapps.io/`

## Avatar Prompt

The avatar prompt is managed via the Napster Spaces UI at `spaces.napsterai.dev` (Prompt tab).
It is NOT deployed with the code. Updating the prompt in the UI takes effect immediately.

Prompt versions are tracked in `scripts/prompts/`:
- `longines-prompt-v1.txt` — original prompt
- `longines-prompt-v2-paste-this.txt` — current prompt (natural language + always-show-product)

## Session Monitor

**Deployed URL:** `https://longines-session-monitor.purplebush-d6b18060.westus2.azurecontainerapps.io/`

The session monitor uses in-memory storage. Container restarts wipe all queued sessions.
