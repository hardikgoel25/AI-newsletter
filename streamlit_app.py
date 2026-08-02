
# streamlit_app.py
from pathlib import Path
import os
import webbrowser
import json

import streamlit as st
import streamlit.components.v1 as components

from src.llm import LLMClient
from src.prompts import NEWSLETTER_JSON_PROMPT
from src.parser import parse_llm_response
from src.renderer import render_newsletter, save_html
from src.image_fetcher import download_image
from src.embed_assets import embed_images

BASE_DIR = Path(__file__).resolve().parent
GENERATED_DIR = BASE_DIR / "generated"
GENERATED_DIR.mkdir(exist_ok=True)

client = LLMClient(
    provider="groq",
    model="llama-3.3-70b-versatile"
)

if "newsletter_data" not in st.session_state:
    st.session_state.newsletter_data = None

if "html_content" not in st.session_state:
    st.session_state.html_content = None

if "output_file" not in st.session_state:
    st.session_state.output_file = None
if "current_theme" not in st.session_state:
    st.session_state.current_theme = "dark"

st.set_page_config(page_title="AI Newsletter Generator", page_icon="📰", layout="wide")
st.title("📰 AI Newsletter Generator")
st.caption("Generate beautiful AI-powered corporate newsletters.")

st.sidebar.title("⚙️ Settings")

use_custom_logo = st.sidebar.checkbox("Upload Custom Logo")
logo_path = None
if use_custom_logo:
    logo = st.sidebar.file_uploader("Choose Logo", type=["svg","png","jpg","jpeg","webp"])
    if logo:
        for ext in [".svg",".png",".jpg",".jpeg",".webp"]:
            f = GENERATED_DIR / f"logo{ext}"
            if f.exists():
                f.unlink()
        logo_path = GENERATED_DIR / f"logo{Path(logo.name).suffix.lower()}"
        logo_path.write_bytes(logo.getbuffer())

use_custom_banner = st.sidebar.checkbox("Upload Custom Hero Image")
hero_path = None
if use_custom_banner:
    banner = st.sidebar.file_uploader("Choose Hero Image", type=["png","jpg","jpeg"])
    if banner:
        hero_path = GENERATED_DIR / "banner.jpg"
        hero_path.write_bytes(banner.getbuffer())
        
st.sidebar.divider()
st.sidebar.subheader("🖼 Hero Image")

##banner_prompt = st.sidebar.text_input(
##    "Banner Prompt (Optional)",
##    placeholder="Modern AI office with blue lighting"
##)

manual_image_keywords = st.sidebar.text_input(
    "Image Keywords (Optional)",
    placeholder="technology, ai, office"
)

theme = st.sidebar.selectbox(
    "🎨 Theme",
    ["Dark", "Light"],
    index=0 if st.session_state.current_theme == "dark" else 1,
)

st.sidebar.divider()
st.sidebar.subheader("📰 Newsletter Settings")

newsletter_type = st.sidebar.selectbox(
    "Newsletter Type",
    [
        "Corporate",
        "Weekly Update",
        "Monthly Update",
        "Product Launch",
        "Investor Update",
        "Internal Newsletter",
        "HR Newsletter",
        "Marketing",
        "Custom"
    ]
)

tone = st.sidebar.selectbox(
    "Tone",
    [
        "Professional",
        "Executive",
        "Friendly",
        "Technical",
        "Marketing",
        "Minimal",
        "Inspirational"
    ]
)

reading_time = st.sidebar.selectbox(
    "Estimated Reading Time",
    [
        "Auto",
        "3 min",
        "5 min",
        "7 min",
        "10 min"
    ]
)

highlight_count = st.sidebar.slider(
    "Highlights",
    2,
    8,
    4
)

section_count = st.sidebar.slider(
    "Sections",
    3,
    6,
    4
)

st.subheader("🏢 Company Information (Optional)")
c1,c2 = st.columns(2)
with c1:
    company_name = st.text_input("Company Name")
    website = st.text_input("Website")
    contact_email = st.text_input("Email")
    phone = st.text_input("Phone")
    address = st.text_area("Address", height=100)
    tagline = st.text_input("Company Tagline")
with c2:

    linkedin = st.text_input("LinkedIn")
    twitter = st.text_input("Twitter / X")

    instagram = st.text_input("Instagram")
    facebook = st.text_input("Facebook")
    youtube = st.text_input("YouTube")
    github = st.text_input("GitHub")


st.subheader("✍ Content Overrides")

hero_title_override = st.text_input(
    "Hero Title (Optional)",
    placeholder="Leave empty to let AI generate"
)

summary_override = st.text_area(
    "Executive Summary (Optional)",
    height=120,
    placeholder="Leave empty to let AI generate"
)

company_updates = st.text_area(
    "Paste Company Updates",
    height=350,
    placeholder="""• TechNova launched AI Assistant 2.0
    • Crossed 100,000 active users
    • Partnered with Microsoft Azure
    • Opened Bangalore Office
    • Hiring ML Engineers"""
)

if st.button("🚀 Generate Newsletter", use_container_width=True):

    if not company_updates.strip():
        st.warning("Please enter company updates.")
        st.stop()

    status = st.status("Generating Newsletter...", expanded=True)

    try:
        status.write("🧠 Preparing Prompt...")

        company_info = f"""
            Company Name: {company_name}

            Website: {website}

            Email: {contact_email}

            Phone: {phone}

            Address: {address}

            LinkedIn: {linkedin}

            Twitter: {twitter}

            Instagram: {instagram}

            Facebook: {facebook}

            YouTube: {youtube}

            GitHub: {github}

            Tagline: {tagline}

            Newsletter Type: {newsletter_type}

            Tone: {tone}

            Estimated Reading Time: {reading_time}

            Generate exactly {highlight_count} highlights.

            Generate exactly {section_count} sections.

            Company Updates:
            {company_updates}
            """

        prompt = NEWSLETTER_JSON_PROMPT.format(content=company_info)

        status.write("🤖 Generating Newsletter...")
        raw_response = client.generate(prompt)

        status.write("📄 Validating JSON...")
        data = parse_llm_response(raw_response)
        # Theme
        data["theme"] = theme.lower()
        if reading_time != "Auto":
            data["estimated_read_time"] = reading_time

        # Override hero title
        if hero_title_override.strip():
            data["hero_title"] = hero_title_override.strip()

        # Override summary
        if summary_override.strip():
            data["summary"] = summary_override.strip()
            
        ##if banner_prompt.strip():
        ##    data["banner_prompt"] = banner_prompt.strip()

        if manual_image_keywords.strip():
            manual_keywords = [
                k.strip()
                for k in manual_image_keywords.split(",")
                if k.strip()
            ]           
            data["manual_image_keywords"] = manual_keywords

        footer = data.setdefault("footer", {})

        footer_fields = {
            "website": website,
            "contact_email": contact_email,
            "phone": phone,
            "address": address,
            "linkedin": linkedin,
            "twitter": twitter,
            "instagram": instagram,
            "facebook": facebook,
            "youtube": youtube,
            "github": github,
            "tagline": tagline,
        }

        for key, value in footer_fields.items():
            if value.strip():
                footer[key] = value.strip()
                
        if company_name.strip():
            data["company_name"] = company_name.strip()

        if logo_path:
            data["custom_logo"] = True
        if hero_path:
            data["custom_banner"] = True

        status.write("🎨 Rendering HTML...")
        html = render_newsletter(data)
        html = embed_images(html, BASE_DIR)

        status.write("💾 Saving Newsletter...")
        output_file = save_html(html, filename=f"newsletter_{theme.lower()}.html")

        status.update(label="✅ Newsletter Generated Successfully!", state="complete")

        html_content = output_file.read_text(encoding="utf-8")
        st.session_state.newsletter_data = data
        st.session_state.html_content = html_content
        st.session_state.output_file = output_file
        st.session_state.current_theme = theme.lower()

        st.success(
            f"""
            🎉 Newsletter generated successfully!

            Theme: {theme}
            Type: {newsletter_type}
            Tone: {tone}

            Sections: {len(data.get("sections", []))}
            Highlights: {len(data.get("highlights", []))}
            """
        )
        st.divider()
        with st.expander("📦 Generated JSON"):
            st.json(data)
        if st.button("🔄 Regenerate Hero Image", use_container_width=True):

            keywords = (
                st.session_state.newsletter_data.get("manual_image_keywords")
                or st.session_state.newsletter_data.get("image_keywords", [])
            )

            company = st.session_state.newsletter_data.get(
                "company_name",
                "",
            )

            with st.spinner("Generating a new hero image..."):
                download_image(
                    company_name=company,
                    keywords=keywords,
                    filename="banner.jpg",
                )

            html = render_newsletter(
                st.session_state.newsletter_data
            )

            html = embed_images(html, BASE_DIR)

            output_file = save_html(
                html,
                filename=f"newsletter_{st.session_state.current_theme}.html",
            )

            st.session_state.output_file = output_file
            st.session_state.html_content = output_file.read_text(
                encoding="utf-8"
            )

            st.toast("✅ Hero image regenerated!")

            st.rerun()

        is_cloud = os.getenv("STREAMLIT_SERVER_HEADLESS") == "true"

        if is_cloud:
            st.subheader("📄 Newsletter Preview")
            components.html(st.session_state.html_content, height=1000, scrolling=True)
        else:
            try:
                os.startfile(st.session_state.output_file)
            except (AttributeError,OSError):
                webbrowser.open(st.session_state.output_file.resolve().as_uri())
            with st.expander("📄 Preview inside Streamlit"):
                components.html(st.session_state.html_content, height=1000, scrolling=True)

        st.download_button(
            "📥 Download HTML",
            data=st.session_state.html_content,
            file_name=f"newsletter_{theme.lower()}.html",
            mime="text/html",
            use_container_width=True,
        )

        st.download_button(
            "📥 Download JSON",
            data=json.dumps(st.session_state.newsletter_data, indent=2),
            file_name="newsletter.json",
            mime="application/json",
            use_container_width=True,
        )
    except Exception as e:
        status.update(label="❌ Generation Failed", state="error")
        st.exception(e)
