import json
import re


def parse_llm_response(response: str) -> dict:
    """
    Parse and normalize JSON returned by the LLM.
    """

    response = response.strip()

    # Remove markdown fences
    response = re.sub(r"^```(?:json)?\s*", "", response, flags=re.IGNORECASE)
    response = re.sub(r"\s*```$", "", response)

    # Extract first JSON object
    match = re.search(r"\{.*\}", response, re.DOTALL)

    if not match:
        raise ValueError("No valid JSON found in LLM response.")

    data = json.loads(match.group())

    # -------------------------
    # Normalize Highlights
    # -------------------------

    highlights = data.get("highlights", [])

    if highlights and isinstance(highlights[0], str):

        icon_map = {
            "AI": "🚀",
            "Launch": "🚀",
            "User": "👥",
            "Office": "🏢",
            "Engineer": "💼",
            "Hiring": "💼",
            "Award": "🏆",
            "Azure": "☁️",
            "Cloud": "☁️",
            "API": "🔗",
            "Partnership": "🤝",
            "Growth": "📈"
        }

        def choose_icon(text):
            for keyword, icon in icon_map.items():
                if keyword.lower() in text.lower():
                    return icon
            return "⭐"

        normalized = []

        for item in highlights:
            normalized.append({
                "icon": choose_icon(item),
                "title": item if len(item) <= 35 else item[:35] + "...",
                "subtitle": ""
            })

        data["highlights"] = normalized

    # -------------------------
    # Sort Sections
    # -------------------------

    if "sections" in data:
        data["sections"] = sorted(
            data["sections"],
            key=lambda x: x.get("priority", 999)
        )

    return data