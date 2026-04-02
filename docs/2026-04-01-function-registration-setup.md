# Napster Spaces Function Registration Setup Guide

How to register functions (like product comparison, add to cart) with the Napster Spaces platform for a new demo. This must be done before the avatar can trigger client-side actions.

---

## What This Does

The avatar (AI) needs to call functions like "show this product" or "add to cart." These functions run in the browser, but the avatar needs to know they exist. You register them with the Spaces API, which gives you a **Library ID**. You then pass that Library ID to the SDK so it knows which functions to listen for.

---

## Prerequisites

- Python 3 with `requests` installed (`pip install requests`)
- The Napster Spaces API key: `47112013-debf-45c2-83bf-3236937aadcb`
- Your experience ID (the base64 string from the embed code)

---

## Step 1: Create the Registration Script

Create a file like `scripts/register_<demo>_functions.py`. Here's the template:

```python
#!/usr/bin/env python3
"""Register functions for <Demo Name>, grouped under the same Library ID."""

import requests
import json

API_KEY = "47112013-debf-45c2-83bf-3236937aadcb"
EXPERIENCE_ID = "<your-base64-experience-id>"
URL = "https://spaces-api.napsterai.dev/v1/experiences/avatars/register-function"

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# ============================================================
# FUNCTION 1: show_product_compare
# ============================================================
# This is typically the first function you register.
# The response will include a libraryId -- save it.

func1 = {
    "experience_id": EXPERIENCE_ID,
    "payload": {
        "data": {
            "name": "show_product_compare",
            "description": "Display one or two products on the webpage. Call with one product_name to show a single product, or two product names for side-by-side comparison.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name_1": {
                        "type": "string",
                        "description": "The name of the product to display."
                    },
                    "product_name_2": {
                        "type": "string",
                        "description": "Optional. Second product for side-by-side comparison."
                    },
                    "comparison_reason": {
                        "type": "string",
                        "description": "Brief reason for showing this product."
                    }
                },
                "required": ["product_name_1", "comparison_reason"]
            }
        },
        "flow": "implicit",
        "receive_messages": True
    }
}

# ============================================================
# FUNCTION 2: add_to_bag
# ============================================================
# When registering the second function, pass the libraryId
# from the first registration to group them together.

func2_base = {
    "experience_id": EXPERIENCE_ID,
    "payload": {
        "data": {
            "name": "add_to_bag",
            "description": "Add one or two products to the customer's shopping bag. Use when the customer says they want to buy or add to cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name_1": {
                        "type": "string",
                        "description": "The name of the product to add to bag."
                    },
                    "product_name_2": {
                        "type": "string",
                        "description": "Optional. Second product to add to bag."
                    }
                },
                "required": ["product_name_1"]
            }
        },
        "flow": "implicit",
        "receive_messages": True
    }
}


# ============================================================
# REGISTER
# ============================================================

print("=" * 60)
print("Step 1: Register show_product_compare")
print("=" * 60)

r1 = requests.post(URL, headers=HEADERS, json=func1, timeout=30)
print(f"Status: {r1.status_code}")
print(f"Response: {r1.text}")

library_id = None
if r1.status_code in (200, 201):
    result = r1.json()
    library_id = result.get('libraryId')
    print(f"\n*** LIBRARY ID: {library_id} ***\n")

if not library_id:
    print("ERROR: No library ID returned. Cannot register second function.")
    exit(1)

print("=" * 60)
print("Step 2: Register add_to_bag (grouped with libraryId)")
print("=" * 60)

# Pass libraryId in both locations to ensure grouping
func2_base["payload"]["libraryId"] = library_id
func2_base["libraryId"] = library_id

r2 = requests.post(URL, headers=HEADERS, json=func2_base, timeout=30)
print(f"Status: {r2.status_code}")
print(f"Response: {r2.text}")

if r2.status_code in (200, 201):
    result2 = r2.json()
    lib2 = result2.get('libraryId')
    if lib2 == library_id:
        print("\nSUCCESS: Both functions share the same Library ID!")
    else:
        print(f"\nWARNING: Different Library IDs. func1={library_id}, func2={lib2}")
        print("Use the SECOND library ID if they differ.")
        library_id = lib2

print("\n" + "=" * 60)
print("DONE. Put this in index.html:")
print(f"  const FUNCTIONS_LIBRARY_ID = '{library_id}';")
print("=" * 60)
```

---

## Step 2: Run It

```bash
python3 scripts/register_<demo>_functions.py
```

Expected output:
```
Step 1: Register show_product_compare
Status: 200
Response: {"success":true,"libraryId":"abc123-...","function":"show_product_compare"}

*** LIBRARY ID: abc123-... ***

Step 2: Register add_to_bag (grouped with libraryId)
Status: 200
Response: {"success":true,"libraryId":"abc123-...","function":"add_to_bag"}

SUCCESS: Both functions share the same Library ID!

DONE. Put this in index.html:
  const FUNCTIONS_LIBRARY_ID = 'abc123-...';
```

---

## Step 3: Update index.html

Take the Library ID from the script output and set it in `index.html`:

```javascript
const FUNCTIONS_LIBRARY_ID = '<library-id-from-script>';
```

Then in the SDK init:

```javascript
spacesInstance = await window.napsterSpacesSDK.init({
    experienceId: EXPERIENCE_ID,
    container: '#avatar-sdk-container',
    startWithoutPreview: true,
    functionsLibraryId: FUNCTIONS_LIBRARY_ID,
    functions: ['show_product_compare', 'add_to_bag'],
    features: {
        backgroundRemoval: { enabled: true },
        waveform: { enabled: true, color: '#C9A96E' },
        // ...
    },
});
```

The `functions` array must exactly match the `name` values you registered.

---

## Key Concepts

### Library ID
- The first function you register creates a new Library ID
- The second function should be registered WITH that Library ID to group them together
- Pass `libraryId` in the payload when registering subsequent functions
- If they end up with different Library IDs, use the last one returned

### Function Schema
- `name`: Must match exactly what you put in the SDK `functions` array
- `description`: Tells the AI when to call this function -- be specific
- `parameters`: JSON Schema format describing what arguments the AI should pass
- `flow: "implicit"`: The function is called automatically (no user confirmation)
- `receive_messages: true`: The function receives message data

### API Endpoint
```
POST https://spaces-api.napsterai.dev/v1/experiences/avatars/register-function
Headers:
  Content-Type: application/json
  X-API-Key: 47112013-debf-45c2-83bf-3236937aadcb
```

---

## Troubleshooting

### Avatar doesn't call functions
- Verify `functionsLibraryId` in SDK init matches the Library ID from registration
- Verify `functions` array names match exactly (case-sensitive)
- Check browser console for SDK debug messages about function calls
- The avatar prompt should mention the functions -- e.g., "ALWAYS show product cards when mentioning specific products"

### Functions registered but not grouped
- If the second function returns a different Library ID, the grouping may have failed
- Try passing `libraryId` in both `payload.libraryId` and top-level `libraryId`
- If they still differ, use the Library ID from the LAST registered function

### Re-registering functions
- You can re-run the registration script safely -- it will overwrite existing registrations
- You'll get new Library IDs each time, so update index.html accordingly

---

## Lumens Demo Specific Values

- **Experience ID:** `YmFlZDM0ZTctZWE5My00MTY3LTg1MzgtNTcwOGQ3MDZlMWY0OmE1ODdhNDhmLTdiYTQtNGQ3ZC1hOGNkLWM4YWMxYjE3NTM0ZQ==`
- **Library ID:** `4da5a4b7-1079-454c-9129-e5d62b1b5cf9`
- **Functions:** `show_product_compare`, `add_to_bag`
- **Registration scripts:** `scripts/register_lumens_functions.py`
