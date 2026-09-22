"""Turns a few plain-language answers into scene/motion prompts via GPT.

Lets someone who's never written an AI prompt in their life answer four
simple questions instead — this fills in the same scene_prompt/motion_prompt
fields you'd otherwise have to write by hand.
"""
import json

from . import config

SYSTEM_PROMPT = """You write prompts for two AI models used in a product-video pipeline:
1. An image-editing model that composites a product cutout into a new background scene.
2. A video-generation model that animates that finished image into a short cinematic clip.

Given a few plain-language answers from a non-expert user, write:
- "scene_prompt": one vivid sentence describing the background/setting/lighting to place the product into. Do NOT describe the product itself (shape, label, color) - the model already has the product image; only describe the environment around it.
- "motion_prompt": one vivid sentence describing camera movement and scene motion for a 5-second video clip (e.g. push-in, orbit, drifting particles, light sweep). Keep it physically plausible.
- "caption": a short, punchy one-line marketing caption for the product (under 10 words), or an empty string if there isn't enough information to write one.

Respond with ONLY a JSON object with exactly these three keys - no markdown, no commentary, no extra keys.
"""


def generate_prompts(product: str, vibe: str, setting: str, action: str, notes: str = "") -> dict:
    from openai import OpenAI

    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set in .env / Settings")

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    user_prompt = (
        f"Product: {product}\n"
        f"Desired vibe/mood: {vibe}\n"
        f"Setting/location: {setting}\n"
        f"Key action/motion: {action}\n"
    )
    if notes:
        user_prompt += f"Extra notes: {notes}\n"

    resp = client.chat.completions.create(
        model=config.OPENAI_TEXT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )
    data = json.loads(resp.choices[0].message.content)
    return {
        "scene_prompt": data.get("scene_prompt", ""),
        "motion_prompt": data.get("motion_prompt", ""),
        "caption": data.get("caption", ""),
    }
