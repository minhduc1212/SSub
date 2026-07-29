import requests
from src.utils import download_file

API_KEY = "d3Sba6j6VYnty3ir5T8GXYoAuiLSBf0S"
USER_AGENT = "VLSub OpenSubtitles.com v1.2.9"

def login(username, password):
    if not username or not password:
        return None
        
    url = "https://api.opensubtitles.com/api/v1/login"
    headers = {
        "Api-Key": API_KEY,
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json"
    }
    data = {
        "username": username,
        "password": password
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            return response.json().get("token")
    except Exception as e:
        print(f"OpenSubtitles login error: {e}")
    return None

def search(query, languages="vi,en"):
    url = "https://api.opensubtitles.com/api/v1/subtitles"
    headers = {
        "Api-Key": API_KEY,
        "User-Agent": USER_AGENT
    }
    params = {
        "query": query,
        "languages": languages
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code != 200:
            return []
            
        results = response.json().get("data", [])
        formatted = []
        for item in results:
            attrs = item.get("attributes", {})
            files = attrs.get("files", [])
            if not files:
                continue
                
            file_id = files[0].get("file_id")
            file_name = files[0].get("file_name") or "subtitle.srt"
            language = attrs.get("language", "unknown")
            downloads = attrs.get("download_count", 0)
            
            formatted.append({
                "provider": "OpenSubtitles",
                "language": language,
                "release_info": file_name,
                "downloads": downloads,
                "rating": attrs.get("ratings", 0.0),
                "id": file_id,
                "file_name": file_name
            })
        return formatted
    except Exception as e:
        print(f"OpenSubtitles search error: {e}")
        return []

def download(item, config):
    token = login(config.get("username"), config.get("password"))
    if not token:
        print("Error: Could not login to OpenSubtitles.com. Check credentials in config.json.")
        return False
        
    file_id = item["id"]
    file_name = item.get("file_name", "subtitle.srt")
    
    url = "https://api.opensubtitles.com/api/v1/download"
    headers = {
        "Api-Key": API_KEY,
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    data = {
        "file_id": file_id
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            dl_info = response.json()
            dl_link = dl_info.get("link")
            if dl_link:
                # Use the generic downloader to download and extract
                output_dir = config.get("output_dir", ".") if config else "."
                return download_file(dl_link, headers={"User-Agent": USER_AGENT}, output_dir=output_dir)
            else:
                print("OpenSubtitles API response did not contain a download link.")
        else:
            print(f"OpenSubtitles download link request failed: HTTP {response.status_code} - {response.text}")
    except Exception as e:
        print(f"OpenSubtitles download error: {e}")
    return False
