#!/usr/bin/env python3
"""Register the show_product_compare function for the Lumens AI avatar."""

import requests
import json

API_KEY = "47112013-debf-45c2-83bf-3236937aadcb"
EXPERIENCE_ID = "YmFlZDM0ZTctZWE5My00MTY3LTg1MzgtNTcwOGQ3MDZlMWY0OmE1ODdhNDhmLTdiYTQtNGQ3ZC1hOGNkLWM4YWMxYjE3NTM0ZQ=="

FUNCTION_SCHEMA = {
    "experience_id": EXPERIENCE_ID,
    "payload": {
        "data": {
            "name": "show_product_compare",
            "description": "Display one or two Lumens products on the webpage. Call this function with one product_name to show a single product, or with two product names to show a side-by-side comparison. Use this whenever discussing a specific product, recommending a light/furniture piece, or comparing two products.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name_1": {
                        "type": "string",
                        "description": "The name of the product to display. Use names like 'PH 5 Pendant', 'Nelson Saucer Bubble Pendant', 'Heracleum III LED Chandelier', 'AJ Wall Sconce', 'IC Wall/Ceiling Light', 'Twiggy Arc Floor Lamp', 'Arco LED Floor Lamp', 'Grasshopper Floor Lamp', 'Tolomeo LED Floor Lamp', 'Flowerpot VP3 Table Lamp', 'Tolomeo Classic Table Lamp', 'Zephyr LED Smart Ceiling Fan', 'Torque Smart Ceiling Fan', 'Lispenard Sofa', 'Paramount Lounge Chair', 'CH24 Wishbone Chair', 'Eames Molded Plywood Dining Chair', 'Quill Medium Rug', or 'Shade Rug'."
                    },
                    "product_name_2": {
                        "type": "string",
                        "description": "Optional. The name of a second product to compare side-by-side. Only provide this when comparing two products."
                    },
                    "comparison_reason": {
                        "type": "string",
                        "description": "Brief explanation of why the product is being shown or compared (e.g., 'Customer asked about pendant lights', 'Comparing floor lamps', 'Recommending based on room')."
                    }
                },
                "required": ["product_name_1", "comparison_reason"]
            }
        },
        "flow": "implicit",
        "receive_messages": True
    }
}


def register_function():
    url = "https://spaces-api.napsterai.dev/v1/experiences/avatars/register-function"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    print("=" * 60)
    print("Lumens - Register show_product_compare")
    print("=" * 60)
    print(f"\nExperience ID: {EXPERIENCE_ID}")

    response = requests.post(url, headers=headers, json=FUNCTION_SCHEMA, timeout=30)

    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {response.text}")

    if response.status_code in (200, 201):
        result = response.json()
        print("\nshow_product_compare registered successfully!")
        if 'functionsLibraryId' in result:
            print(f"\n*** LIBRARY ID: {result['functionsLibraryId']} ***")
            print("Use this Library ID when registering the next function!")
        return result
    else:
        print(f"\nFailed. Status: {response.status_code}")
        return None


if __name__ == "__main__":
    register_function()
