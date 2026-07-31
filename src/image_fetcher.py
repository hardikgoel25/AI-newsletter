import requests
from pathlib import Path

from src.config import UNSPLASH_ACCESS_KEY

BASE_DIR = Path(__file__).resolve().parent.parent
GENERATED_DIR = BASE_DIR / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

BANNER_PATH = GENERATED_DIR / "banner.jpg"

UNSPLASH_URL = "https://api.unsplash.com/photos/random"

HEADERS = {
    "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"
}


def _download(query: str):
    """Attempt to download a single image for a query."""

    response = requests.get(
        UNSPLASH_URL,
        headers=HEADERS,
        params={
            "query": query,
            "orientation": "landscape",
        },
        timeout=15,
    )

    print(f"[Unsplash] Query: {query}")
    print(f"[Unsplash] Status: {response.status_code}")

    if response.status_code == 404:
        print("[Unsplash] No photos found.")
        return None

    response.raise_for_status()

    image_url = response.json()["urls"]["regular"]

    image = requests.get(image_url, timeout=20)
    image.raise_for_status()

    with open(BANNER_PATH, "wb") as f:
        f.write(image.content)

    print(f"[Unsplash] Saved banner -> {BANNER_PATH}")

    return str(BANNER_PATH)


def download_image(keywords):
    if isinstance(keywords, str):
        keywords = [keywords]

    keywords = [k.strip() for k in keywords if k.strip()]

    search_queries = []

    # 1. Original approach (highest relevance)
    if keywords:
        search_queries.append(" ".join(keywords))

    # 2. Slightly simplified
    if len(keywords) >= 5:
        search_queries.append(" ".join(keywords[:5]))

    # 3. Top 3 keywords
    if len(keywords) >= 3:
        search_queries.append(" ".join(keywords[:3]))

    # 4. Top 2 keywords
    if len(keywords) >= 2:
        search_queries.append(" ".join(keywords[:2]))

    # 5. Individual keywords
    search_queries.extend(keywords)

    # 6. Generic fallbacks
    search_queries.extend([
        "business technology",
        "corporate office",
        "innovation",
    ])

    tried = set()

    for query in search_queries:

        query = query.strip()

        if not query or query.lower() in tried:
            continue

        tried.add(query.lower())

        try:
            result = _download(query)

            if result:
                print(f"[Unsplash] Success using: {query}")
                return result

        except Exception as e:
            print(f"[Unsplash] {query}: {e}")

    print("[Unsplash] Failed to download any image.")
    return None