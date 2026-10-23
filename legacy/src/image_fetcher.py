import requests
from pathlib import Path

from src.config import UNSPLASH_ACCESS_KEY

BASE_DIR = Path(__file__).resolve().parent.parent
GENERATED_DIR = BASE_DIR / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

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
    "content_filter": "high",
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
    3. Company only
    4. Keywords
    5. Generic fallbacks
    """

    if keywords is None:
        keywords = []

    if isinstance(keywords, str):
        keywords = [keywords]

    keywords = [k.strip() for k in keywords if k.strip()]

    output_path = GENERATED_DIR / filename

    search_queries = []

    # -------------------------------------------------
    # Build search queries (most specific → broadest)
    # -------------------------------------------------

    company_name = company_name.strip()

    # 1. User override always wins
    if custom_query:
        search_queries.append(custom_query.strip())

    # 2. Company-specific searches
    if company_name:

        search_queries.extend([
    f"{company_name} engineering",
    f"{company_name} technology",
    f"{company_name} innovation",
    f"{company_name} headquarters",
    f"{company_name} campus",
    f"{company_name} office",
])

        if len(keywords) >= 2:
            search_queries.append(
                f"{company_name} {keywords[0]} {keywords[1]}"
            )

        if keywords:
            search_queries.append(
                f"{company_name} {keywords[0]}"
            )

        search_queries.append(company_name)

    # 3. Keyword combinations
    if keywords:
        search_queries.append(" ".join(keywords))

    if len(keywords) >= 3:
        search_queries.append(" ".join(keywords[:3]))

    if len(keywords) >= 2:
        search_queries.append(" ".join(keywords[:2]))

    # 4. Individual keywords
    search_queries.extend(keywords)

    # 5. AVL-specific fallbacks
    if company_name.lower() == "avl":
        search_queries.extend([
            "AVL headquarters Austria",
            "AVL engineering center",
            "automotive testing laboratory",
            "electric vehicle testing",
            "vehicle engineering",
            "automotive research",
            "engineering laboratory",
        ])

    # 6. Generic fallbacks
    search_queries.extend([
        "modern engineering office",
        "automotive engineering",
        "research laboratory",
        "engineering workplace",
        "corporate innovation",
    ])

    tried = set()

    for query in search_queries:

        query = query.strip()

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