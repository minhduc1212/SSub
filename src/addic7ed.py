import re
import requests
from src.utils import download_file

BASE_URL = "https://api.gestdown.info"
HEADERS = {
    "accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

LANG_MAP_ADDIC7ED = {
    "en": "English",
    "vi": "Vietnamese",
    "ar": "Arabic",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
}

def parse_season_episode(query):
    # Match S01E01 or S1E1
    match = re.search(r'[sS](\d+)\s*[eE](\d+)', query)
    if match:
        season = int(match.group(1))
        episode = int(match.group(2))
        # Remove SxxExx from query to get show name
        clean_query = query.replace(match.group(0), "").strip()
        return clean_query, season, episode
        
    # Match 1x01 or 1x1
    match_alt = re.search(r'(\d+)\s*x\s*(\d+)', query)
    if match_alt:
        season = int(match_alt.group(1))
        episode = int(match_alt.group(2))
        clean_query = query.replace(match_alt.group(0), "").strip()
        return clean_query, season, episode
        
    return None

def search_shows(show_name):
    url = f"{BASE_URL}/shows/search/{show_name}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return response.json().get("shows", [])
    except Exception as e:
        print(f"Addic7ed show search error: {e}")
    return []

def search(query, languages="vi,en"):
    parse_result = parse_season_episode(query)
    if not parse_result:
        # Silently skip but log a notice
        # (This avoids cluttering if the query is a movie like "Inception")
        return []
        
    show_name, season, episode = parse_result
    print(f"Searching Addic7ed for show '{show_name}' S{season:02d}E{episode:02d}...")
    
    shows = search_shows(show_name)
    if not shows:
        print(f"[Addic7ed] Show '{show_name}' not found.")
        return []
        
    # Use the first/best show match
    show_id = shows[0]["id"]
    show_title = shows[0]["name"]
    
    lang_list = [l.strip().lower() for l in languages.split(",") if l.strip()]
    formatted = []
    
    for l in lang_list:
        lang_name = LANG_MAP_ADDIC7ED.get(l, l.capitalize())
        url = f"{BASE_URL}/subtitles/get/{show_id}/{season}/{episode}/{lang_name}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code == 200:
                subs_data = response.json()
                matching = subs_data.get("matchingSubtitles", [])
                for sub in matching:
                    version = sub.get("version", "N/A")
                    release = sub.get("release")
                    dl_uri = sub.get("downloadUri")
                    
                    if dl_uri:
                        release_info = f"{show_title} S{season:02d}E{episode:02d} - Version: {version}"
                        if release:
                            release_info += f" ({release})"
                            
                        formatted.append({
                            "provider": "Addic7ed",
                            "language": l,
                            "release_info": release_info,
                            "link": f"{BASE_URL}{dl_uri}",
                            "id": f"{BASE_URL}{dl_uri}"
                        })
        except Exception as e:
            print(f"[Addic7ed] Error fetching subtitles for {lang_name}: {e}")
            
    return formatted

def download(item, config=None):
    dl_url = item["link"]
    try:
        # Use our standard downloader
        return download_file(dl_url, headers=HEADERS)
    except Exception as e:
        print(f"Addic7ed download error: {e}")
        return False
