import requests
from src.utils import download_file

BASE_URL = "https://api.subdl.com/api/v1/subtitles"

def search(query, languages="vi,en", api_key=None):
    if not api_key:
        # Silently skip if not configured, or return empty list
        return []
        
    print(f"Searching SubDL for '{query}'...")
    params = {
        "api_key": api_key,
        "film_name": query,
        "languages": languages
    }
    
    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
        if response.status_code != 200:
            print(f"SubDL search failed: HTTP {response.status_code}")
            return []
            
        data = response.json()
        if not data.get("status"):
            error_msg = data.get("error", "Unknown error")
            print(f"SubDL API returned error: {error_msg}")
            return []
            
        subtitles = data.get("subtitles", [])
        formatted = []
        for sub in subtitles:
            lang = sub.get("lang", "unknown")
            release_name = sub.get("release_name") or sub.get("name") or "N/A"
            dl_link = sub.get("download_link")
            
            if not dl_link and sub.get("url"):
                dl_link = f"https://dl.subdl.com{sub.get('url')}"
                
            if dl_link:
                # Add API key to download link if paid/auth required, though usually direct links work
                formatted.append({
                    "provider": "SubDL",
                    "language": lang,
                    "release_info": release_name,
                    "link": dl_link,
                    "id": dl_link
                })
        return formatted
    except Exception as e:
        print(f"SubDL search error: {e}")
        return []

def download(item, config=None):
    dl_link = item["link"]
    
    # If the user has an API key, we append it to the download link as a query parameter
    # in case SubDL requires it to track quotas or permissions.
    api_key = config.get("subdl_api_key") if config else None
    if api_key and "api_key=" not in dl_link:
        connector = "&" if "?" in dl_link else "?"
        dl_link = f"{dl_link}{connector}api_key={api_key}"
        
    try:
        # Download and extract the subtitle using our common downloader
        return download_file(dl_link)
    except Exception as e:
        print(f"SubDL download error: {e}")
        return False
