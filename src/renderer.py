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
    autoescape=True,
)


def render_newsletter(newsletter_data):
    """
    Render newsletter HTML.

    Features
    --------
    - Automatic theme selection
    - Uploaded/custom logo support
    - Uploaded/custom banner support
    - Automatic Unsplash banner search
    """

    data = newsletter_data.copy()
    data.setdefault("manual_image_keywords", [])
    data.setdefault("company_name", "")

    # -----------------------------
    # Theme
    # -----------------------------
    theme = data.get("theme", "dark").lower()

    template_name = (
        "newsletter_light.html"
        if theme == "light"
        else "newsletter_dark.html"
    )

    try:
        template = env.get_template(template_name)
    except TemplateNotFound as e:
        raise FileNotFoundError(
            f"Template '{template_name}' not found."
        ) from e

    # -----------------------------
    # Ensure Footer Exists
    # -----------------------------
    if not isinstance(data.get("footer"), dict):
        data["footer"] = {}

    # -----------------------------
    # Logo
    # -----------------------------
    default_logo = (
        "../assets/logo.svg"
        if (BASE_DIR / "assets/logo.svg").exists()
        else "../assets/logo.png"
    )

    if data.get("custom_logo"):
        for ext in [".svg", ".png", ".webp", ".jpg", ".jpeg"]:
            logo = BASE_DIR / f"generated/logo{ext}"

            if logo.exists():
                data["logo"] = f"../generated/logo{ext}"
                break
        else:
            data["logo"] = default_logo
    else:
        data["logo"] = default_logo

    # -----------------------------
    # Hero Image
    # -----------------------------
    if data.get("custom_banner"):
        data["hero_placeholder"] = "../generated/banner.jpg"

    else:

        keywords = data.get("manual_image_keywords")

        if not keywords:
            keywords = data.get("image_keywords", [])

        company_name = data.get("company_name", "")

        banner = download_image(
            company_name=company_name,
            keywords=keywords,
            filename="banner.jpg",
        )

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