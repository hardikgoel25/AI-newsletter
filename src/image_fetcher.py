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


def _download(query: str, output_path: Path):
    """Attempt to download a single image for a query."""

    response = requests.get(
        UNSPLASH_URL,
        headers=HEADERS,
        params={
            "query": query,
            "orientation": "landscape",
        },
        timeout=(5,20),
    )

    print(f"[Unsplash] Query: {query}")
    print(f"[Unsplash] Status: {response.status_code}")

    if response.status_code == 404:
        print("[Unsplash] No photos found.")
        return None

    response.raise_for_status()

    image_data = response.json()

    image_url = (
        image_data.get("urls", {})
        .get("regular")
    )

    if not image_url:
        return None

    image = requests.get(image_url, timeout=20)
    image.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(image.content)

    print(f"[Unsplash] Saved banner -> {output_path}")

    return str(output_path)


def download_image(
    company_name="",
    keywords=None,
    custom_query=None,
    filename="banner.jpg",
):
    """
    Download a banner image.

    Priority:
    1. Custom query
    2. Company + keywords
    3. Keywords
    4. Generic fallbacks
    """

    if keywords is None:
        keywords = []

    if isinstance(keywords, str):
        keywords = [keywords]

    keywords = [k.strip() for k in keywords if k.strip()]

    output_path = GENERATED_DIR / filename

    search_queries = []

    # Highest priority
    if custom_query:
        search_queries.append(custom_query.strip())

    # Company-aware searches
    if company_name and len(keywords) >= 2:
        search_queries.append(
            f"{company_name} {keywords[0]} {keywords[1]}"
        )

    if company_name and keywords:
        search_queries.append(
            f"{company_name} {keywords[0]}"
        )

    if company_name:
        search_queries.extend([
            company_name,
            f"{company_name} headquarters",
            f"{company_name} office",
        ])

    # Original search
    if keywords:
        search_queries.append(" ".join(keywords))

    if len(keywords) >= 5:
        search_queries.append(" ".join(keywords[:5]))

    if len(keywords) >= 3:
        search_queries.append(" ".join(keywords[:3]))

    if len(keywords) >= 2:
        search_queries.append(" ".join(keywords[:2]))

    search_queries.extend(keywords)

    # Generic fallbacks
    search_queries.extend([
        "business technology",
        "corporate office",
        "innovation",
    ])

    tried = set()

    for query in search_queries:

        query = " ".join(query.split())

        if not query:
            continue

        key = query.lower()

        if key in tried:
            continue

        tried.add(key)

        try:
            result = _download(query, output_path)

            if result:
                print(f"[Unsplash] Success using: {query}")
                return result

        except Exception as e:
            print(f"[Unsplash] {query}: {e}")

    print("[Unsplash] Failed to download any image.")
    return None