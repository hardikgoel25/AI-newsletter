# 📰 AI Newsletter Generator

An AI-powered application that transforms raw company updates into beautifully designed, professional newsletters in seconds.

Built with **Python**, **Streamlit**, **Groq LLM**, and **Jinja2**, the application automatically generates structured newsletter content and renders it into modern, responsive HTML templates.

---

## ✨ Features

- 🤖 AI-generated newsletter content using Groq LLM
- 📝 Converts plain company updates into polished newsletters
- 🎨 Modern responsive HTML templates
- 🖼️ Custom logo upload (SVG, PNG, JPG, JPEG, WebP)
- 🌄 Custom hero/banner image upload
- 📄 Download newsletters as standalone HTML
- 📱 Mobile-friendly responsive design
- ⚡ Fast generation with Groq Llama 3.3 70B
- 🔧 Easy to customize templates

---

## 📸 Screenshots

> Add screenshots here after uploading them.

```
screenshots/
    home.png
    newsletter.png
```

---

## 🏗️ Tech Stack

- Python
- Streamlit
- Groq API
- Llama 3.3 70B Versatile
- Jinja2
- HTML5
- CSS3

---

## 📂 Project Structure

```text
AI-Newsletter-Generator/
│
├── assets/
│   ├── logo.svg
│   └── logo.png
│
├── generated/
│
├── src/
│   ├── llm.py
│   ├── parser.py
│   ├── prompts.py
│   ├── renderer.py
│   ├── embed_assets.py
│   └── image_fetcher.py
│
├── templates/
│   └── corporate.html
│
├── app.py
├── requirements.txt
└── README.md
```

---

## 🚀 Installation

Clone the repository

```bash
git clone https://github.com/yourusername/AI-Newsletter-Generator.git

cd AI-Newsletter-Generator
```

Create a virtual environment

```bash
python -m venv venv
```

Activate it

Windows

```bash
venv\Scripts\activate
```

Linux / macOS

```bash
source venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Variables

Create a `.env` file.

```env
GROQ_API_KEY=your_api_key_here
```

---

## ▶️ Run

```bash
streamlit run app.py
```

---

## 📝 Usage

1. Paste company updates.
2. Optionally upload:
   - Company logo
   - Hero image
3. Click **Generate Newsletter**.
4. Preview the newsletter.
5. Download the generated HTML.

---

## 📌 Current Features

- Corporate newsletter template
- AI-generated structured content
- Executive summary
- Highlight cards
- Responsive layout
- Standalone HTML export
- Embedded images
- Custom branding support

---

## 🚧 Upcoming Features

- Multiple newsletter templates
- PDF export
- Dark mode
- Theme customization
- Email template export
- Automatic stock image integration
- Newsletter history
- Multi-language support

---

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a new branch.

```bash
git checkout -b feature-name
```

3. Commit your changes.

```bash
git commit -m "Add feature"
```

4. Push to your branch.

```bash
git push origin feature-name
```

5. Open a Pull Request.

---

## 📄 License

This project is licensed under the MIT License.

---

## ⭐ Acknowledgements

- Groq
- Streamlit
- Jinja2
- Meta Llama
