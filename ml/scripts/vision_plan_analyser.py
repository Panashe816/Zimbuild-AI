import base64
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# ============================================================
# ZIMBUILD AI
# VISION-BASED ARCHITECTURAL PLAN ANALYSER
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

IMAGE_PATH = Path(
    r"C:\Users\TMC CLIENT\Downloads\WhatsApp Image 2026-10-03 at 12.06.11.jpeg"
)

# IMPORTANT:
# Use a NEW OpenRouter key because the previous key was exposed.
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = "google/gemini-2.5-pro"

# 100 = 1:100
USER_SCALE_RATIO = 100


# ============================================================
# IMAGE ENCODING
# ============================================================

def encode_image(image_path):

    if not image_path.exists():
        raise FileNotFoundError(
            f"Architectural plan not found:\n{image_path}"
        )

    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()

    return base64.b64encode(image_bytes).decode("utf-8")


# ============================================================
# PLAN ANALYSIS
# ============================================================

def analyse_plan():

    print("=" * 80)
    print("ZIMBUILD AI - VISION ARCHITECTURAL PLAN ANALYSIS")
    print("=" * 80)

    print()
    print("Architectural plan:")
    print(IMAGE_PATH)

    print()
    print("Vision model:")
    print(MODEL)

    print()
    print("User-selected drawing scale:")
    print(f"1:{USER_SCALE_RATIO}")

    # --------------------------------------------------------
    # Validate API key
    # --------------------------------------------------------

    if (
        not OPENROUTER_API_KEY
        or OPENROUTER_API_KEY == "PASTE_NEW_OPENROUTER_KEY_HERE"
    ):
        raise ValueError(
            "Please paste your NEW OpenRouter API key "
            "into OPENROUTER_API_KEY."
        )

    # --------------------------------------------------------
    # Validate image
    # --------------------------------------------------------

    if not IMAGE_PATH.exists():
        raise FileNotFoundError(
            f"Architectural plan does not exist:\n{IMAGE_PATH}"
        )

    # --------------------------------------------------------
    # Encode image
    # --------------------------------------------------------

    print()
    print("Reading original architectural photograph...")

    image_base64 = encode_image(IMAGE_PATH)

    print("Image encoded successfully.")

    # ========================================================
    # PROMPT
    # ========================================================

    prompt = f"""
You are the architectural-plan interpretation component of
ZimBuild AI, a construction quantity-estimation and Bill of
Quantities system for residential buildings in Zimbabwe.

You are analysing the ORIGINAL architectural floor-plan
photograph supplied with this request.

The user has explicitly selected:

DRAWING SCALE = 1:{USER_SCALE_RATIO}

The user's selected scale is authoritative.

Do NOT replace the user's selected scale.

Your task is to extract as much reliable architectural
measurement information as possible from the drawing.

The information will be passed to a deterministic quantity,
material, pricing and Bill of Quantities engine.

============================================================
IMPORTANT RULES
============================================================

1. DO NOT INVENT INFORMATION.

If a measurement, wall, door, window, room or roof feature
cannot be reliably identified, return null or mark it
uncertain.

2. USE THE PRINTED DIMENSION CHAINS.

Read the dimension strings around the building carefully.

3. TRACE WALLS SYSTEMATICALLY.

Do not merely identify wall types.

Identify individual physical wall segments.

For every identifiable wall segment provide:

- wall ID
- external or internal
- start location
- end location
- length
- thickness
- measurement source
- confidence

4. DO NOT DOUBLE COUNT WALLS.

A shared wall between two rooms is one physical wall.

5. EXTERNAL WALLS.

Identify the perimeter wall segments individually.

6. INTERNAL WALLS.

Identify internal partition wall segments individually.

7. WALL THICKNESS.

Use explicitly printed values.

The drawing appears to contain values such as:

230 mm
115 mm

Do not assume every wall has the same thickness.

8. DOORS.

Identify visible door openings and door symbols.

For each identifiable door provide:

- ID
- width
- location
- connected rooms
- confidence

9. WINDOWS.

Inspect the external walls carefully.

Identify visible window openings/symbols.

For each identifiable window provide:

- ID
- width if visible
- height if visible
- location
- room
- confidence

10. ROOMS.

Identify every visible room.

For each room provide:

- room ID
- room name/type
- dimensions
- floor area
- measurement source
- confidence

11. FLOOR AREA.

Look carefully for an explicitly printed total floor area.

If the drawing explicitly states a floor area, use it.

12. DIMENSIONS.

Extract important visible dimensions.

Preserve the printed value and unit.

13. SCALE.

The user-selected scale is:

1:{USER_SCALE_RATIO}

Report it.

If another printed scale is visible, report it separately.

Do NOT override the user's scale.

14. ROOF.

Only report roof information if actually visible.

Do not invent roof area.

============================================================
WALL LENGTH CALCULATION
============================================================

The quantity engine requires TOTAL WALL LENGTH.

Therefore:

A. Identify every visible external wall segment.

B. Identify every visible internal wall segment.

C. Determine each segment length using:

- printed dimensions
- dimension chains
- room dimensions
- geometric relationships

D. Mark each measurement as:

"printed"

"derived_from_dimensions"

or

"visual_estimate"

E. Prefer printed dimensions.

F. Calculate:

total_external_wall_length_m

total_internal_wall_length_m

total_wall_length_m

G. Do not double-count shared walls.

============================================================
OPENINGS
============================================================

Where possible calculate:

total_door_opening_width_m

total_window_opening_width_m

Do not invent opening heights.

============================================================
ROOM AREAS
============================================================

For every room:

area = width × length

Use printed dimensions where available.

Calculate:

calculated_room_area_total_m2

If a printed total floor area exists, report it separately.

============================================================
NO PRICING
============================================================

Do NOT calculate:

- cement prices
- brick prices
- sand prices
- labour prices
- transport prices
- construction cost

Those calculations belong to ZimBuild AI.

============================================================
RETURN ONLY VALID JSON
============================================================

Use exactly this structure:

{{
  "analysis_status": "success",

  "scale": {{
    "user_selected_ratio": {USER_SCALE_RATIO},
    "user_selected_label": "1:{USER_SCALE_RATIO}",
    "printed_scale_detected": null,
    "scale_conflict": false
  }},

  "drawing": {{
    "description": "",
    "is_complete_floor_plan": null,
    "units": null,
    "printed_total_floor_area_m2": null,
    "important_dimensions": []
  }},

  "walls": {{
    "count": null,
    "external_walls": [],
    "internal_walls": [],
    "total_external_wall_length_m": null,
    "total_internal_wall_length_m": null,
    "total_wall_length_m": null,
    "wall_thicknesses_m": []
  }},

  "rooms": {{
    "count": null,
    "rooms": [],
    "calculated_room_area_total_m2": null
  }},

  "doors": {{
    "count": null,
    "items": [],
    "total_door_opening_width_m": null
  }},

  "windows": {{
    "count": null,
    "items": [],
    "total_window_opening_width_m": null
  }},

  "floor": {{
    "printed_total_floor_area_m2": null,
    "calculated_total_floor_area_m2": null,
    "recommended_floor_area_m2": null
  }},

  "roof": {{
    "present": false,
    "type": null,
    "area_m2": null,
    "evidence": ""
  }},

  "confidence": {{
    "overall": null,
    "walls": null,
    "wall_lengths": null,
    "wall_thickness": null,
    "dimensions": null,
    "rooms": null,
    "doors": null,
    "windows": null,
    "floor_area": null,
    "roof": null
  }},

  "warnings": []
}}
"""

    # ========================================================
    # OPENROUTER PAYLOAD
    # ========================================================

    payload = {
        "model": MODEL,

        "messages": [
            {
                "role": "user",

                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url":
                                "data:image/jpeg;base64,"
                                + image_base64
                        }
                    }
                ]
            }
        ],

        "temperature": 0.1,

        "response_format": {
            "type": "json_object"
        }
    }

    # ========================================================
    # SEND REQUEST
    # ========================================================

    print()
    print("=" * 80)
    print("SENDING ORIGINAL PLAN TO VISION MODEL")
    print("=" * 80)

    print()
    print("Model:", MODEL)
    print("Scale:", f"1:{USER_SCALE_RATIO}")
    print()
    print("Please wait...")

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",

        headers={
            "Authorization":
                f"Bearer {OPENROUTER_API_KEY}",

            "Content-Type":
                "application/json",

            "HTTP-Referer":
                "http://localhost:8000",

            "X-Title":
                "ZimBuild AI"
        },

        json=payload,

        timeout=240
    )

    print()
    print("HTTP STATUS:", response.status_code)

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    if response.status_code != 200:

        print()
        print("=" * 80)
        print("OPENROUTER ERROR")
        print("=" * 80)

        print(response.text)

        response.raise_for_status()

    # ========================================================
    # PARSE RESPONSE
    # ========================================================

    result = response.json()

    try:

        content = (
            result["choices"][0]
            ["message"]
            ["content"]
        )

    except (
        KeyError,
        IndexError,
        TypeError
    ) as error:

        print()
        print("Unexpected OpenRouter response:")

        print(
            json.dumps(
                result,
                indent=2
            )
        )

        raise RuntimeError(
            f"Could not extract model response: {error}"
        )

    # ========================================================
    # JSON RESULT
    # ========================================================

    print()
    print("=" * 80)
    print("VISION MODEL ANALYSIS")
    print("=" * 80)
    print()

    try:

        analysis = json.loads(content)

    except json.JSONDecodeError:

        print(
            "MODEL DID NOT RETURN VALID JSON."
        )

        print()
        print(content)

        raise

    print(
        json.dumps(
            analysis,
            indent=2,
            ensure_ascii=False
        )
    )

    # ========================================================
    # SAVE RESULT
    # ========================================================

    output_path = (
        PROJECT_ROOT
        / "ml"
        / "results"
        / "vision_plan_analysis.json"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as output_file:

        json.dump(
            analysis,
            output_file,
            indent=2,
            ensure_ascii=False
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 80)
    print("VISION ANALYSIS COMPLETE")
    print("=" * 80)

    walls = analysis.get(
        "walls",
        {}
    )

    rooms = analysis.get(
        "rooms",
        {}
    )

    doors = analysis.get(
        "doors",
        {}
    )

    windows = analysis.get(
        "windows",
        {}
    )

    floor = analysis.get(
        "floor",
        {}
    )

    print()
    print(
        "External wall length:",
        walls.get(
            "total_external_wall_length_m"
        )
    )

    print(
        "Internal wall length:",
        walls.get(
            "total_internal_wall_length_m"
        )
    )

    print(
        "TOTAL wall length:",
        walls.get(
            "total_wall_length_m"
        )
    )

    print(
        "Wall count:",
        walls.get(
            "count"
        )
    )

    print(
        "Room count:",
        rooms.get(
            "count"
        )
    )

    print(
        "Door count:",
        doors.get(
            "count"
        )
    )

    print(
        "Window count:",
        windows.get(
            "count"
        )
    )

    print(
        "Printed floor area:",
        floor.get(
            "printed_total_floor_area_m2"
        )
    )

    print(
        "Recommended floor area:",
        floor.get(
            "recommended_floor_area_m2"
        )
    )

    print()
    print(
        "Saved:",
        output_path
    )

    print("=" * 80)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    analyse_plan()
