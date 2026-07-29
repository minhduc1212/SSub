import requests
from src.utils import download_file

BASE_URL = "https://api.subsource.net/v1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

def search_movies(query):
    url = f"{BASE_URL}/movie/search"
    payload = {
        "query": query,
        "includeSeasons": True,
        "limit": 15
    }
    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("results", [])
    except Exception as e:
        print(f"SubSource movie search error: {e}")
    return []

def get_movie_subtitles(movie_slug):
    url = f"{BASE_URL}/subtitles/{movie_slug}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return data.get("subtitles", [])
    except Exception as e:
        print(f"SubSource subtitles fetch error: {e}")
    return []

LANG_MAP = {
    "en": "english",
    "vi": "vietnamese",
    "ar": "arabic",
    "es": "spanish",
    "fr": "french",
    "de": "german",
    "it": "italian",
    "ru": "russian",
    "zh": "chinese",
    "ja": "japanese",
    "ko": "korean",
}

def search(query, languages="vi,en"):
    print(f"Searching SubSource for '{query}'...")
    movies = search_movies(query)
    if not movies:
        return []
        
    # Sort movies by score descending to bring exact/best match to the top
    movies = sorted(movies, key=lambda x: x.get("score", 0), reverse=True)
    
    lang_list = [l.strip().lower() for l in languages.split(",") if l.strip()]
    target_langs = []
    for l in lang_list:
        if l in LANG_MAP:
            target_langs.append(LANG_MAP[l])
        else:
            target_langs.append(l)
            
    formatted = []
    
    # We query the subtitles for the top 2 movies to keep it fast but comprehensive
    for movie in movies[:2]:
        movie_link = movie.get("link", "")
        movie_slug = movie_link.replace("/subtitles/", "").strip("/")
        if not movie_slug:
            continue
            
        movie_title = movie.get("title", "")
        movie_year = movie.get("releaseYear", "")
        movie_label = f"{movie_title} ({movie_year})"
        
        subtitles = get_movie_subtitles(movie_slug)
        for sub in subtitles:
            sub_lang = sub.get("language", "unknown").lower()
            # Filter by language
            if target_langs and sub_lang not in target_langs:
                continue
                
            release_info = sub.get("release_info", "N/A")
            rating = sub.get("rating", "unrated")
            sub_link = sub.get("link")
            
            formatted.append({
                "provider": "SubSource",
                "language": sub_lang,
                "release_info": f"{movie_label} - {release_info} (Rating: {rating})",
                "link": sub_link,
                "id": sub_link
            })
            
    return formatted

def download(item, config=None):
    sub_link = item["link"]
    
    # Get download token
    url = f"{BASE_URL}/subtitle/{sub_link}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print("Failed to fetch SubSource subtitle details.")
            return False
            
        data = response.json()
        sub = data.get("subtitle", {})
        download_token = sub.get("download_token")
        if not download_token:
            print("Failed to acquire SubSource download token.")
            return False
            
        # Download subtitle file
        dl_url = f"{BASE_URL}/subtitle/download/{download_token}"
        dl_headers = HEADERS.copy()
        dl_headers["Referer"] = f"https://subsource.net/subtitle/{sub_link}"
        
        output_dir = config.get("output_dir", ".") if config else "."
        return download_file(dl_url, headers=dl_headers, output_dir=output_dir)
    except Exception as e:
        print(f"SubSource download error: {e}")
        return False
