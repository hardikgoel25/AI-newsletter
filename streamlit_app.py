
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
from src.embed_assets import embed_images
from themes.avl import AVL_THEME

BASE_DIR = Path(__file__).resolve().parent
GENERATED_DIR = BASE_DIR / "generated"
GENERATED_DIR.mkdir(exist_ok=True)

client = LLMClient(
    provider="groq",
    model="llama-3.3-70b-versatile"
)

st.set_page_config(page_title="AI Newsletter Generator", page_icon="📰", layout="wide")
st.title("📰 AI Newsletter Generator")
st.caption("Generate beautiful AI-powered corporate newsletters.")

st.sidebar.title("⚙️ Settings")

brand = st.sidebar.selectbox(
    "Brand",
    [
        "Generic",
        "AVL"
    ]
)

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

theme = st.sidebar.selectbox("🎨 Theme", ["Dark","Light"], index=0)

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

publication_date = st.sidebar.text_input(
    "Publication Date",
    value="August 2026"
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

if brand == "AVL":
    defaults = AVL_THEME
else:
    defaults = {}

company_name_default = defaults.get("company_name", "")
website_default = defaults.get("website", "")
contact_email_default = defaults.get("contact_email", "")
phone_default = defaults.get("phone", "")
address_default = defaults.get("address", "")
tagline_default = defaults.get("tagline", "")

linkedin_default = defaults.get("linkedin", "")
twitter_default = defaults.get("twitter", "")
instagram_default = defaults.get("instagram", "")
facebook_default = defaults.get("facebook", "")
youtube_default = defaults.get("youtube", "")
github_default = defaults.get("github", "")

st.subheader("🏢 Company Information (Optional)")
c1,c2 = st.columns(2)
with c1:
    company_name = st.text_input("Company Name", value=company_name_default)
    website = st.text_input("Website", value=website_default)
    contact_email = st.text_input("Email", value=contact_email_default)
    phone = st.text_input("Phone", value=phone_default)
    address = st.text_area("Address", height=100, value=address_default)
    tagline = st.text_input("Company Tagline", value=tagline_default)
with c2:

    linkedin = st.text_input("LinkedIn", value=linkedin_default)
    twitter = st.text_input("Twitter / X", value=twitter_default)

    instagram = st.text_input("Instagram", value=instagram_default)
    facebook = st.text_input("Facebook", value=facebook_default)
    youtube = st.text_input("YouTube", value=youtube_default)
    github = st.text_input("GitHub", value=github_default)


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

Publication Date: {publication_date}

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
        data["brand"] = brand.lower()
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
        footer["website"] = website or footer.get("website","")
        footer["contact_email"] = contact_email or footer.get("contact_email","")
        footer["phone"] = phone or footer.get("phone","")
        footer["address"] = address or footer.get("address","")
        footer["linkedin"] = linkedin or footer.get("linkedin","")
        footer["twitter"] = twitter or footer.get("twitter","")
        footer["tagline"] = tagline or footer.get("tagline","")
        footer["instagram"] = instagram or footer.get("instagram", "")
        footer["facebook"] = facebook or footer.get("facebook", "") 
        footer["youtube"] = youtube or footer.get("youtube", "")
        footer["github"] = github or footer.get("github", "")
        if company_name:
            data["company_name"] = company_name

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

        with st.expander("📦 Generated JSON"):
            st.json(data)

        is_cloud = os.getenv("STREAMLIT_SERVER_HEADLESS") == "true"

        if is_cloud:
            st.subheader("📄 Newsletter Preview")
            components.html(html_content, height=1000, scrolling=True)
        else:
            try:
                os.startfile(output_file)
            except (AttributeError,OSError):
                webbrowser.open(output_file.resolve().as_uri())
            with st.expander("📄 Preview inside Streamlit"):
                components.html(html_content, height=1000, scrolling=True)

        st.download_button(
            "📥 Download HTML",
            data=html_content,
            file_name=f"newsletter_{theme.lower()}.html",
            mime="text/html",
            use_container_width=True,
        )

        st.download_button(
            "📥 Download JSON",
            data=json.dumps(data, indent=2),
            file_name="newsletter.json",
            mime="application/json",
            use_container_width=True,
        )

    except Exception as e:
        status.update(label="❌ Generation Failed", state="error")
        st.exception(e)
