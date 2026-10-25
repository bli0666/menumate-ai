#!/usr/bin/env python3
import json
import os
import threading
import urllib.request
import urllib.error
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
API_URL = "https://api.openai.com/v1/responses"
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
MAX_BODY = 20 * 1024 * 1024

EXTRACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "menu_language": {"type": "string"},
        "menu_title": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "original_name": {"type": "string"},
                    "translated_name": {"type": "string"},
                    "price": {"type": "string"},
                    "section": {"type": "string"},
                    "visible_description": {"type": "string"},
                    "explicit_ingredients": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"]
                    }
                },
                "required": [
                    "original_name", "translated_name", "price", "section",
                    "visible_description", "explicit_ingredients", "confidence"
                ]
            }
        },
        "extraction_warnings": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["menu_language", "menu_title", "items", "extraction_warnings"]
}

RECOMMENDATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "analysis_language": {"type": "string"},
        "overall_note": {"type": "string"},
        "recommended_meal": {
            "type": "array",
            "minItems": 1,
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "rank": {"type": "integer"},
                    "course": {
                        "type": "string",
                        "enum": ["Appetizer", "Main", "Side", "Drink", "Dessert", "Other"]
                    },
                    "course_label_in_user_language": {"type": "string"},
                    "original_name": {"type": "string"},
                    "name_in_user_language": {"type": "string"},
                    "price": {"type": "string"},
                    "category": {"type": "string"},
                    "why_recommended": {"type": "string"},
                    "allergen_assessment": {"type": "string"},
                    "health_consideration": {"type": "string"},
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"]
                    },
                    "staff_question": {"type": "string"}
                },
                "required": [
                    "rank", "course", "course_label_in_user_language",
                    "original_name", "name_in_user_language", "price", "category",
                    "why_recommended", "allergen_assessment",
                    "health_consideration", "confidence", "staff_question"
                ]
            }
        },
        "high_risk_notes": {
            "type": "array",
            "items": {"type": "string"}
        },
        "source_limitations": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": [
        "analysis_language", "overall_note", "recommended_meal",
        "high_risk_notes", "source_limitations"
    ]
}

def api_key():
    return os.environ.get("OPENAI_API_KEY", "").strip()

def call_openai(payload):
    key = api_key()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Start the app with start.command "
            "or export an API key before running app.py."
        )
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=150) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
            msg = parsed.get("error", {}).get("message", detail)
        except Exception:
            msg = detail
        raise RuntimeError(f"OpenAI API error ({e.code}): {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error while contacting OpenAI: {e}") from e

def extract_output_text(response):
    if isinstance(response.get("output_text"), str) and response["output_text"].strip():
        return response["output_text"].strip()
    pieces = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                pieces.append(content["text"])
    if pieces:
        return "\n".join(pieces).strip()
    raise RuntimeError("The model returned no readable text output.")

def structured_response(schema_name, schema, input_payload, instructions=""):
    payload = {
        "model": MODEL,
        "input": input_payload,
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": schema,
                "strict": True
            }
        }
    }
    if instructions:
        payload["instructions"] = instructions
    response = call_openai(payload)
    raw = extract_output_text(response)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError("The AI returned an invalid structured response.") from e

def extract_uploaded_menu(image_data_url, mother_language):
    prompt = f"""
You are performing MENU TRANSCRIPTION ONLY.

IMPORTANT:
- Analyze ONLY the restaurant menu visible in the uploaded image in this request.
- There is NO sample menu and NO preset menu. Ignore any prior examples or familiar dishes.
- Never invent a dish just because it is common in that cuisine.
- Extract every clearly visible food/drink item you can read, its visible price, section, description,
  and any ingredients explicitly written on the menu.
- If a detail is not visible, return an empty string or empty array instead of guessing.
- translated_name should be translated/explained in: {mother_language}.
- Keep original_name exactly as it appears on the uploaded menu when possible.
- If text is blurry or partially unreadable, lower confidence and mention it in extraction_warnings.
""".strip()

    return structured_response(
        "uploaded_menu_extraction",
        EXTRACTION_SCHEMA,
        [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {
                    "type": "input_image",
                    "image_url": image_data_url,
                    "detail": "high"
                }
            ]
        }],
        instructions=(
            "Do not use outside menu knowledge to add items. "
            "This step must faithfully transcribe the uploaded image only."
        )
    )

def recommend_from_extracted_menu(profile, extracted):
    language = (profile.get("mother_language") or "English").strip()
    profile_json = json.dumps(profile, ensure_ascii=False, indent=2)
    menu_json = json.dumps(extracted, ensure_ascii=False, indent=2)

    prompt = f"""
You are the recommendation engine for a restaurant-menu assistant.

USER PROFILE
{profile_json}

ACTUAL MENU EXTRACTED FROM THE USER'S UPLOADED IMAGE
{menu_json}

Return the answer primarily in the user's mother language: {language}.

GOAL
Create a personalized recommended meal of 3–5 DISTINCT items when the extracted menu has enough
appropriate choices. Organize the recommendation like an actual meal whenever possible:
- one Appetizer
- one Main
- one Drink
- optionally one Side
- optionally one Dessert
Only use courses that are actually available on the uploaded menu. If the menu has no drinks,
desserts, or appetizers, do NOT invent them.

STRICT MENU-GROUNDING RULE
Every recommended original_name MUST exactly match an original_name from the extracted menu above.
Do not recommend anything that is not in that extracted menu.

DIVERSITY RULE
Avoid near-duplicates. Do not fill the recommendation with multiple dishes based on the same
main protein/base or nearly identical preparation. As a default, choose at most one fish/seafood
dish, one chicken dish, one beef/pork dish, one noodle/rice main, etc., unless the menu is too
limited to create 3 distinct appropriate choices.

SAFETY RULES
- Severe allergy safety has priority over preference. Never call any item "safe."
- If an item's visible description or explicit ingredients conflict with an allergy, do not recommend it.
- If hidden ingredients, sauces, or cross-contact are uncertain, clearly say so and give a short
  staff_question the user can ask before ordering.
- Health conditions are context only. Do not diagnose or give medical treatment. Use cautious,
  general nutrition language.
- Prefer fewer than 3 recommendations rather than inventing dishes or recommending an obvious
  allergy conflict.

Keep the result concise enough for a mobile app.
""".strip()

    result = structured_response(
        "personalized_recommended_meal",
        RECOMMENDATION_SCHEMA,
        prompt,
        instructions=(
            "Choose only from the extracted uploaded menu. "
            "Never substitute a sample menu or generic cuisine knowledge."
        )
    )

    # Hard validation: recommendations must refer to an actually extracted dish.
    valid_names = {str(x.get("original_name", "")).strip() for x in extracted.get("items", [])}
    filtered = []
    seen_names = set()
    for rec in result.get("recommended_meal", []):
        name = str(rec.get("original_name", "")).strip()
        if name in valid_names and name not in seen_names:
            filtered.append(rec)
            seen_names.add(name)
    result["recommended_meal"] = filtered[:5]

    if not result["recommended_meal"]:
        raise RuntimeError(
            "The menu was read, but the AI could not produce a grounded recommendation "
            "from the extracted items. Try a clearer menu photo."
        )
    return result

def analyze_menu(profile, image_data_url):
    language = (profile.get("mother_language") or "English").strip()
    extracted = extract_uploaded_menu(image_data_url, language)
    if not extracted.get("items"):
        raise RuntimeError(
            "No readable menu items were found in the uploaded image. "
            "Try a clearer, closer photo of the menu."
        )
    recommendation = recommend_from_extracted_menu(profile, extracted)
    return {"extracted_menu": extracted, "recommendation": recommendation}

def chat_about_menu(profile, analysis_bundle, question):
    language = (profile.get("mother_language") or "English").strip()
    context = json.dumps(
        {"profile": profile, "uploaded_menu_analysis": analysis_bundle},
        ensure_ascii=False
    )
    prompt = f"""
Answer the user's follow-up question about THEIR UPLOADED MENU.

Respond in the user's mother language: {language}.
Use only the supplied uploaded-menu extraction, recommendations, and user profile as factual context.
Do not bring in a sample menu.
Do not guarantee allergy safety. If ingredients or cross-contact are uncertain, say so and recommend
confirming directly with restaurant staff.
Do not provide diagnosis or medical treatment.
Keep the answer concise and useful for dining.

CONTEXT:
{context}

QUESTION:
{question}
""".strip()

    payload = {"model": MODEL, "input": prompt}
    response = call_openai(payload)
    return extract_output_text(response)

class Handler(BaseHTTPRequestHandler):
    server_version = "MenuMateLocal/3.2"

    def _send_json(self, status, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY:
            raise ValueError("Request body is empty or too large.")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            data = INDEX.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path == "/api/status":
            self._send_json(200, {"ready": bool(api_key()), "model": MODEL, "version": "3.2"})
            return

        self.send_error(404)

    def do_POST(self):
        try:
            data = self._read_json()

            if self.path == "/api/analyze":
                profile = data.get("profile") or {}
                image_data_url = data.get("image_data_url") or ""
                if not image_data_url.startswith("data:image/"):
                    raise ValueError("Please upload a valid menu image.")
                result = analyze_menu(profile, image_data_url)
                self._send_json(200, {"analysis": result})
                return

            if self.path == "/api/chat":
                profile = data.get("profile") or {}
                analysis = data.get("analysis") or {}
                question = (data.get("question") or "").strip()
                if not question:
                    raise ValueError("Please enter a question.")
                answer = chat_about_menu(profile, analysis, question)
                self._send_json(200, {"answer": answer})
                return

            self.send_error(404)

        except ValueError as e:
            self._send_json(400, {"error": str(e)})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def log_message(self, fmt, *args):
        print(f"[MenuMate V3] {self.address_string()} - {fmt % args}")

def main():
    url = f"http://{HOST}:{PORT}"
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"MenuMate AI V3.2 is running at {url}")
    print(f"Model: {MODEL}")
    if not api_key():
        print("WARNING: OPENAI_API_KEY is not set. AI analysis will not work until it is set.")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
