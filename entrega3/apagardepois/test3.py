import os
import json
from google import genai
from google.genai import types

# Make sure your API key is in the environment
# export GEMINI_API_KEY="YOUR_KEY"
api_key = "AIzaSyD9B6oxfcrndLrDIzocgY2Sx91E8ADPz14"
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set")

# Initialize client
client = genai.Client(api_key=api_key)

# Simple test query
prompt = "Generate 3 example search queries about drug labels. Return a JSON array of strings."

try:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=types.Part.from_text(text=prompt),
        config=types.GenerateContentConfig(
            max_output_tokens=200
        )
    )

    # Attempt to parse JSON array
    text = response.text.strip()
    start = text.find("[")
    end = text.rfind("]") + 1
    json_text = text[start:end] if start != -1 and end != -1 else text

    queries = json.loads(json_text)
    print("✅ Gemini returned queries:")
    for q in queries:
        print("-", q)

except Exception as e:
    print("⚠️ Error calling Gemini:", e)
