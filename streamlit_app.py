from pathlib import Path
import os
import webbrowser

import streamlit as st

from src.llm import LLMClient
from src.prompts import NEWSLETTER_JSON_PROMPT
from src.parser import parse_llm_response
from src.renderer import render_newsletter, save_html
from src.embed_assets import embed_images

# -------------------------------------------------------
# Paths
# -------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
GENERATED_DIR = BASE_DIR / "generated"
GENERATED_DIR.mkdir(exist_ok=True)

# -------------------------------------------------------
# LLM
# -------------------------------------------------------

client = LLMClient(
    provider="groq",
    model="llama-3.3-70b-versatile"
)

# -------------------------------------------------------
# Streamlit Config
# -------------------------------------------------------

st.set_page_config(
    page_title="AI Newsletter Generator",
    page_icon="📰",
    layout="wide"
)

st.title("📰 AI Newsletter Generator")
st.caption("Generate beautiful AI-powered corporate newsletters.")

# -------------------------------------------------------
# Sidebar
# -------------------------------------------------------

st.sidebar.title("⚙️ Settings")

# ---------------- Logo ----------------

use_custom_logo = st.sidebar.checkbox("Upload Custom Logo")

logo_path = None

if use_custom_logo:
    logo = st.sidebar.file_uploader(
        "Choose Logo",
        type=["svg", "png", "jpg", "jpeg", "webp"]
    )

    if logo:
        # Delete any previous uploaded logo
        for ext in [".svg", ".png", ".jpg", ".jpeg", ".webp"]:
            old_file = GENERATED_DIR / f"logo{ext}"
            if old_file.exists():
                old_file.unlink()

        # Preserve the uploaded extension
        extension = Path(logo.name).suffix.lower()

        logo_path = GENERATED_DIR / f"logo{extension}"

        with open(logo_path, "wb") as f:
            f.write(logo.getbuffer())

# ---------------- Hero Image ----------------

use_custom_banner = st.sidebar.checkbox(
    "Upload Custom Hero Image"
)

hero_path = None

if use_custom_banner:
    banner = st.sidebar.file_uploader(
        "Choose Hero Image",
        type=["png", "jpg", "jpeg"]
    )

    if banner:
        hero_path = GENERATED_DIR / "banner.jpg"

        with open(hero_path, "wb") as f:
            f.write(banner.read())

# -------------------------------------------------------
# Company Updates
# -------------------------------------------------------

company_updates = st.text_area(
    "Paste Company Updates",
    height=350,
    placeholder="""
• TechNova launched AI Assistant 2.0
• Crossed 100,000 active users
• Partnered with Microsoft Azure
• Opened Bangalore Office
• Hiring ML Engineers
"""
)

# -------------------------------------------------------
# Generate
# -------------------------------------------------------

if st.button("🚀 Generate Newsletter", use_container_width=True):

    if not company_updates.strip():
        st.warning("Please enter company updates.")
        st.stop()

    status = st.status(
        "Generating Newsletter...",
        expanded=True
    )

    try:

        # ---------------- Prompt ----------------

        status.write("🧠 Preparing Prompt...")

        prompt = NEWSLETTER_JSON_PROMPT.format(
            content=company_updates
        )

        # ---------------- LLM ----------------

        status.write("🤖 Calling LLM...")

        raw_response = client.generate(prompt)

        # ---------------- Parse ----------------

        status.write("📄 Parsing Response...")

        data = parse_llm_response(raw_response)

        # ---------------- Assets ----------------

        if logo_path:
            data["custom_logo"] = True

        if hero_path:
            data["custom_banner"] = True

        # ---------------- Render ----------------

        status.write("🎨 Rendering Newsletter...")

        # Render HTML
        html = render_newsletter(data)

        # Embed all local images as Base64
        html = embed_images(
        html,
        BASE_DIR
        )

# Save standalone HTML
        output_file = save_html(html)
        status.update(
            label="✅ Newsletter Generated Successfully!",
            state="complete"
        )

        # ---------------- Open Browser ----------------

        html_content = output_file.read_text(
            encoding="utf-8"
        )

        st.success("🎉 Newsletter generated successfully!")

        try:
            # Windows
            os.startfile(output_file)
        except AttributeError:
            # Linux / macOS
            webbrowser.open(output_file.resolve().as_uri())

        st.info("The newsletter has been opened in your default browser.")

        # ---------------- Download ----------------

        st.download_button(
            "📥 Download HTML",
            data=html_content,
            file_name="newsletter.html",
            mime="text/html",
            use_container_width=True
        )

    except Exception as e:

        status.update(
            label="❌ Generation Failed",
            state="error"
        )

        st.exception(e)