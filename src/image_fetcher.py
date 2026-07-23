import requests
from pathlib import Path

from src.config import UNSPLASH_ACCESS_KEY

BASE_DIR = Path(__file__).resolve().parent.parent
GENERATED_DIR = BASE_DIR / "generated"
GENERATED_DIR.mkdir(exist_ok=True)

BANNER_PATH = GENERATED_DIR / "banner.jpg"


def download_image(keywords):
    """
    Download a banner image using Unsplash.
    Returns the local image path if successful, otherwise None.
    """

    if isinstance(keywords, list):
        query = " ".join(keywords)
    else:
        query = keywords

    url = "https://api.unsplash.com/photos/random"

    headers = {
        "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"
    }

    params = {
        "query": query,
        "orientation": "landscape"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        image_url = response.json()["urls"]["regular"]

        image = requests.get(image_url).content

        with open(BANNER_PATH, "wb") as f:
            f.write(image)

        return str(BANNER_PATH)

    except Exception as e:
        print("Image download failed:", e)
        return None