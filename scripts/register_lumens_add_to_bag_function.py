#!/usr/bin/env python3
"""Register the add_to_bag function for the Lumens AI avatar.
Run this AFTER register_lumens_compare_function.py — paste the Library ID below."""

import requests
import json

API_KEY = "47112013-debf-45c2-83bf-3236937aadcb"
EXPERIENCE_ID = "YmFlZDM0ZTctZWE5My00MTY3LTg1MzgtNTcwOGQ3MDZlMWY0OmE1ODdhNDhmLTdiYTQtNGQ3ZC1hOGNkLWM4YWMxYjE3NTM0ZQ=="

# PASTE THE LIBRARY ID FROM THE FIRST REGISTRATION HERE:
FUNCTIONS_LIBRARY_ID = "4bacec22-9814-47d1-82d4-ab139a42ef1c"

FUNCTION_SCHEMA = {
    "experience_id": EXPERIENCE_ID,
    "payload": {
        "data": {
            "name": "add_to_bag",
            "description": "Add one or two Lumens products to the customer's shopping bag. Use this when the customer says they want to buy, add to cart/bag, or purchase a product. If the customer says 'add both' after a comparison, provide both product names.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name_1": {
                        "type": "string",
                        "description": "The name of the product to add to bag. Use names like 'PH 5 Pendant', 'Arco LED Floor Lamp', 'CH24 Wishbone Chair', etc."
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

if FUNCTIONS_LIBRARY_ID:
    FUNCTION_SCHEMA["payload"]["functions_library_id"] = FUNCTIONS_LIBRARY_ID


def register_function():
    url = "https://spaces-api.napsterai.dev/v1/experiences/avatars/register-function"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    print("=" * 60)
    print("Lumens - Register add_to_bag")
    print("=" * 60)
    print(f"\nExperience ID: {EXPERIENCE_ID}")
    if FUNCTIONS_LIBRARY_ID:
        print(f"Library ID: {FUNCTIONS_LIBRARY_ID}")
    else:
        print("WARNING: No Library ID set! Paste it from the first registration.")

    response = requests.post(url, headers=headers, json=FUNCTION_SCHEMA, timeout=30)

    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {response.text}")

    if response.status_code in (200, 201):
        result = response.json()
        print("\nadd_to_bag registered successfully!")
        if 'functionsLibraryId' in result:
            print(f"\n*** LIBRARY ID: {result['functionsLibraryId']} ***")
        return result
    else:
        print(f"\nFailed. Status: {response.status_code}")
        return None


if __name__ == "__main__":
    register_function()
