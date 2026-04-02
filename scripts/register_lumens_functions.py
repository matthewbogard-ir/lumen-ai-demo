#!/usr/bin/env python3
"""Register both Lumens functions, grouped under the same Library ID."""

import requests
import json

API_KEY = "47112013-debf-45c2-83bf-3236937aadcb"
EXPERIENCE_ID = "YmFlZDM0ZTctZWE5My00MTY3LTg1MzgtNTcwOGQ3MDZlMWY0OmE1ODdhNDhmLTdiYTQtNGQ3ZC1hOGNkLWM4YWMxYjE3NTM0ZQ=="
URL = "https://spaces-api.napsterai.dev/v1/experiences/avatars/register-function"

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# Function 1: show_product_compare
func1 = {
    "experience_id": EXPERIENCE_ID,
    "payload": {
        "data": {
            "name": "show_product_compare",
            "description": "Display one or two Lumens products on the webpage. Call this function with one product_name to show a single product, or with two product names to show a side-by-side comparison.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name_1": {
                        "type": "string",
                        "description": "The name of the product to display."
                    },
                    "product_name_2": {
                        "type": "string",
                        "description": "Optional. The name of a second product for side-by-side comparison."
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

# Function 2: add_to_bag
func2_base = {
    "experience_id": EXPERIENCE_ID,
    "payload": {
        "data": {
            "name": "add_to_bag",
            "description": "Add one or two Lumens products to the customer's shopping bag. Use this when the customer says they want to buy, add to cart/bag, or purchase a product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name_1": {
                        "type": "string",
                        "description": "The name of the product to add to bag."
                    },
                    "product_name_2": {
                        "type": "string",
                        "description": "Optional. The name of a second product to add to bag."
                    }
                },
                "required": ["product_name_1"]
            }
        },
        "flow": "implicit",
        "receive_messages": True
    }
}


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
print("Step 2: Register add_to_bag (with libraryId)")
print("=" * 60)

# Try multiple ways to pass the library ID
func2_base["payload"]["libraryId"] = library_id
func2_base["libraryId"] = library_id

print(f"Payload: {json.dumps(func2_base, indent=2)}")

r2 = requests.post(URL, headers=HEADERS, json=func2_base, timeout=30)
print(f"\nStatus: {r2.status_code}")
print(f"Response: {r2.text}")

if r2.status_code in (200, 201):
    result2 = r2.json()
    lib2 = result2.get('libraryId')
    print(f"\n*** LIBRARY ID (func2): {lib2} ***")
    if lib2 == library_id:
        print("SUCCESS: Both functions share the same Library ID!")
    else:
        print(f"WARNING: Different Library ID returned. func1={library_id}, func2={lib2}")
        print("Functions may not be grouped. Try using the SECOND library ID in index.html.")

print("\n" + "=" * 60)
print(f"Use this in index.html:")
print(f"  const FUNCTIONS_LIBRARY_ID = '{library_id}';")
print("=" * 60)
