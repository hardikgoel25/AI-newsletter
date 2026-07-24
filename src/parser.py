import json
import re


def parse_llm_response(response: str) -> dict:
    """
    Parse and normalize JSON returned by the LLM.
    """

    response = response.strip()

    # -------------------------
    # Remove Markdown Fences
    # -------------------------

    response = re.sub(
        r"^```(?:json)?\s*",
        "",
        response,
        flags=re.IGNORECASE,
    )

    response = re.sub(
        r"\s*```$",
        "",
        response,
    )

    # -------------------------
    # Extract JSON Object
    # -------------------------

    match = re.search(
        r"\{.*\}",
        response,
        re.DOTALL,
    )

    if not match:
        raise ValueError("No valid JSON found in LLM response.")

    try:
        data = json.loads(match.group())
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON returned by LLM:\n{e}"
        ) from e

    # -------------------------
    # Ensure Required Keys
    # -------------------------

    data.setdefault("highlights", [])
    data.setdefault("sections", [])
    data.setdefault("image_keywords", [])
    data.setdefault("footer", {})

    # -------------------------
    # Ensure Footer Keys
    # -------------------------

    footer = data["footer"]

    for key in [
        "tagline",
        "website",
        "contact_email",
        "phone",
        "address",
        "linkedin",
        "twitter",
        "copyright",
        "subscription_note",
        "privacy",
        "terms",
        "unsubscribe",
    ]:
        footer.setdefault(key, "")

    # -------------------------
    # Normalize Highlights
    # (Backward Compatibility)
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
            "Growth": "📈",
        }

        def choose_icon(text):
            for keyword, icon in icon_map.items():
                if keyword.lower() in text.lower():
                    return icon
            return "⭐"

        normalized = []

        for item in highlights:
            normalized.append(
                {
                    "icon": choose_icon(item),
                    "title": item if len(item) <= 35 else item[:35] + "...",
                    "subtitle": "",
                }
            )

        data["highlights"] = normalized

    # -------------------------
    # Sort Sections by Priority
    # -------------------------

    if data["sections"]:
        data["sections"] = sorted(
            data["sections"],
            key=lambda x: int(x.get("priority", 999)),
        )

    return data