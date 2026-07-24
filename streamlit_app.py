
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

theme = st.sidebar.selectbox("🎨 Theme", ["Dark","Light"], index=0)

st.subheader("🏢 Company Information (Optional)")
c1,c2 = st.columns(2)
with c1:
    company_name = st.text_input("Company Name")
    website = st.text_input("Website")
    contact_email = st.text_input("Email")
    phone = st.text_input("Phone")
with c2:
    address = st.text_area("Address", height=100)
    linkedin = st.text_input("LinkedIn")
    twitter = st.text_input("Twitter / X")
    tagline = st.text_input("Company Tagline")

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

        company_info = f"""Company Name: {company_name}
Website: {website}
Email: {contact_email}
Phone: {phone}
Address: {address}
LinkedIn: {linkedin}
Twitter: {twitter}
Tagline: {tagline}

Company Updates:
{company_updates}
"""

        prompt = NEWSLETTER_JSON_PROMPT.format(content=company_info)

        status.write("🤖 Generating Newsletter...")
        raw_response = client.generate(prompt)

        status.write("📄 Validating JSON...")
        data = parse_llm_response(raw_response)
        data["theme"] = theme.lower()

        footer = data.setdefault("footer", {})
        footer["website"] = website or footer.get("website","")
        footer["contact_email"] = contact_email or footer.get("contact_email","")
        footer["phone"] = phone or footer.get("phone","")
        footer["address"] = address or footer.get("address","")
        footer["linkedin"] = linkedin or footer.get("linkedin","")
        footer["twitter"] = twitter or footer.get("twitter","")
        footer["tagline"] = tagline or footer.get("tagline","")
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

        st.success(f"🎉 Newsletter generated successfully! ({len(data.get('sections',[]))} sections, {len(data.get('highlights',[]))} highlights)")

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
