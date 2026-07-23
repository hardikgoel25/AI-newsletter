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
    - Auto template selection
    - Automatic hero image generation
    - Optional uploaded hero image
    - Optional uploaded logo
    """

    template_name = newsletter_data.get("template", "newsletter")

    try:
        template = env.get_template(f"{template_name}.html")
    except TemplateNotFound:
        print(f"[INFO] Template '{template_name}.html' not found. Using 'newsletter.html'.")
        template = env.get_template("newsletter.html")

    data = newsletter_data.copy()

    # =====================================================
    # Logo
    # =====================================================

    if data.get("custom_logo"):
        if (BASE_DIR / "generated/logo.svg").exists():
                data["logo"] = "../generated/logo.svg"
        
        elif (BASE_DIR / "generated/logo.png").exists():
                data["logo"] = "../generated/logo.png"
        
        elif (BASE_DIR / "generated/logo.webp").exists():
                data["logo"] = "../generated/logo.webp"
        
        elif (BASE_DIR / "generated/logo.jpg").exists():
                data["logo"] = "../generated/logo.jpg"
        
        elif (BASE_DIR / "generated/logo.jpeg").exists():
                data["logo"] = "../generated/logo.jpeg"     
    else:
        if (BASE_DIR / "assets/logo.svg").exists():
            data["logo"] = "../assets/logo.svg"
        else:
            data["logo"] = "../assets/logo.png"

    # =====================================================
    # Hero Image
    # =====================================================

    if data.get("custom_banner"):
        data["hero_placeholder"] = "../generated/banner.jpg"

    else:
        banner = download_image(data.get("image_keywords", []))

        if banner:
            data["hero_placeholder"] = "../generated/banner.jpg"
        else:
            data["hero_placeholder"] = "../assets/placeholder.png"

    # =====================================================
    # CSS
    # =====================================================

    data["css_file"] = "../assets/css/style.css"

    return template.render(**data)


def save_html(html, filename="newsletter.html"):
    """
    Save rendered newsletter.
    """

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / filename

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[INFO] Newsletter saved to: {output_file}")

    return output_file