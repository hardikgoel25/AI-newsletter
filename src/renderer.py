from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from src.image_fetcher import download_image
from themes.avl import AVL_THEME

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

    # -----------------------------
    # Theme
    # -----------------------------
    brand = data.get("brand", "generic").lower()
    theme = data.get("theme", "dark").lower()

    if brand == "avl":
        template_name = (
            "newsletter_avl_light.html"
            if theme == "light"
            else "newsletter_avl_dark.html"
        )
    else:
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

    # ---------------------------------
    # Apply AVL defaults
    # ---------------------------------

    if brand == "avl":

        # Company
        data.setdefault("company_name", AVL_THEME["company_name"])

        # Footer defaults
        footer = data["footer"]

        for key in [
        "website",
        "tagline",
        "linkedin",
        "youtube",
        "facebook",
        "instagram",
        "twitter",
        "github",
        "contact_email",
        "phone",
        "address",
        "subscription_note",
        "privacy",
        "terms",
        "unsubscribe",
        ]:
            footer.setdefault(key, AVL_THEME[key])

        # Colors
        data["primary_gradient"] = AVL_THEME["primary_gradient"]
        data["primary"] = AVL_THEME["primary"]
        data["secondary"] = AVL_THEME["secondary"]
        data["tertiary"] = AVL_THEME["tertiary"]
        data["accent"] = AVL_THEME["accent"]
    
    # -----------------------------
    # Logo
    # -----------------------------

    if brand == "avl":

        data["logo"] = AVL_THEME["logo"]

    else:

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
        # Prefer manual keywords if provided
        keywords = (
            data.get("manual_image_keywords")
            or data.get("image_keywords", [])
        )

        banner = download_image(
            company_name=data.get("company_name", ""),
            keywords=keywords,
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