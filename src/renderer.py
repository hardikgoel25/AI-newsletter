from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from src.image_fetcher import download_image

# -----------------------------
# Project Paths
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"

# -----------------------------
# Jinja2 Environment
# -----------------------------
env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=True
)


def render_newsletter(newsletter_data):
    """
    Render newsletter HTML.

    Features:
    - Automatic theme selection
    - Automatic hero image generation
    - Optional uploaded hero image
    - Optional uploaded logo
    """

    data = newsletter_data.copy()

    # -----------------------------
    # Theme / Template
    # -----------------------------
    theme = data.get("theme", "dark").lower()
    default_template = (
        "newsletter_light" if theme == "light" else "newsletter_dark"
    )

    try:
        template = env.get_template(f"{default_template}.html")
    except TemplateNotFound as e:
        raise FileNotFoundError(
            f"Template '{default_template}.html' not found."
        ) from e

    # -----------------------------
    # Logo
    # -----------------------------
    if data.get("custom_logo"):
        for ext in [".svg", ".png", ".webp", ".jpg", ".jpeg"]:
            logo = BASE_DIR / f"generated/logo{ext}"
            if logo.exists():
                data["logo"] = f"../generated/logo{ext}"
                break
    else:
        if (BASE_DIR / "assets/logo.svg").exists():
            data["logo"] = "../assets/logo.svg"
        else:
            data["logo"] = "../assets/logo.png"

    # Fallback if no uploaded logo found
    if "logo" not in data:
        if (BASE_DIR / "assets/logo.svg").exists():
            data["logo"] = "../assets/logo.svg"
        else:
            data["logo"] = "../assets/logo.png"

    # -----------------------------
    # Hero Image
    # -----------------------------
    if data.get("custom_banner"):
        data["hero_placeholder"] = "../generated/banner.jpg"
    else:
        banner = download_image(data.get("image_keywords", []))
        if banner:
            data["hero_placeholder"] = "../generated/banner.jpg"
        else:
            data["hero_placeholder"] = "../assets/placeholder.png"

    # -----------------------------
    # CSS
    # -----------------------------
    data["css_file"] = "../assets/css/style.css"

    return template.render(**data)


def save_html(html, filename="newsletter.html"):
    """
    Save rendered newsletter HTML.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / filename

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[INFO] Newsletter saved to: {output_file}")

    return output_file
