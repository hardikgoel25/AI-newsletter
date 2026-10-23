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

    if not isinstance(data.get("highlights"), list):
        data["highlights"] = []

    if not isinstance(data.get("sections"), list):
        data["sections"] = []

    if not isinstance(data.get("image_keywords"), list):
        data["image_keywords"] = []
    data.setdefault("footer", {})
    data.setdefault("company_name", "Unknown Company")
    data.setdefault("newsletter_type", "")
    data.setdefault("hero_title", "")
    data.setdefault("subtitle", "")
    data.setdefault("summary", "")
    data.setdefault("date", "")
    data.setdefault("tone", "")
    data.setdefault("estimated_read_time", "")
    data.setdefault("hero_image_prompt", "")

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
    "instagram",
    "facebook",
    "youtube",
    "github",
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
        
    normalized_highlights = []

    for item in data["highlights"]:
        if isinstance(item, dict):
            normalized_highlights.append({
            "icon": item.get("icon", "⭐"),
            "title": item.get("title", ""),
            "subtitle": item.get("subtitle", "")
        })

    data["highlights"] = normalized_highlights

        
    normalized_sections = []

    for section in data["sections"]:
        if isinstance(section, dict):
            normalized_sections.append({
                "title": section.get("title", ""),
                "icon": section.get("icon", "📰"),
                "content": section.get("content", ""),
                "priority": section.get("priority", 999)
            })

    data["sections"] = normalized_sections

    # -------------------------
    # Sort Sections by Priority
    # -------------------------

    if data["sections"]:
        data["sections"] = sorted(
            data["sections"],
            key=lambda x: (
    int(x["priority"])
    if str(x.get("priority", "")).isdigit()
    else 999
)
        )

    return data