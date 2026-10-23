from pathlib import Path
import base64
import mimetypes

def to_data_uri(file_path: Path):
    mime = mimetypes.guess_type(file_path)[0]
    if mime is None:
        return None

    encoded = base64.b64encode(file_path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def embed_images(html: str, base_dir: Path):

    mapping = {
        "../assets/logo.png": base_dir / "assets/logo.png",
        "../assets/logo.svg": base_dir / "assets/logo.svg",
        "../generated/banner.jpg": base_dir / "generated/banner.jpg",
        "../generated/banner.png": base_dir / "generated/banner.png",
        "../generated/logo.png": base_dir / "generated/logo.png",
        "../generated/logo.svg": base_dir / "generated/logo.svg",
        "../generated/logo.jpg": base_dir / "generated/logo.jpg",
        "../generated/logo.jpeg": base_dir / "generated/logo.jpeg",
        "../generated/logo.webp": base_dir / "generated/logo.webp",
    }

    for src, file in mapping.items():
        if file.exists():
            uri = to_data_uri(file)
            if uri:
                html = html.replace(src, uri)

    return html