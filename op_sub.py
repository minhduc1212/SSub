import os
import json
import requests

API_KEY = "d3Sba6j6VYnty3ir5T8GXYoAuiLSBf0S"
USER_AGENT = "VLSub OpenSubtitles.com v1.2.9"
CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "username": "",
            "password": ""
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=2)
        print(f"Created configuration template '{CONFIG_FILE}'. Please enter your OpenSubtitles.com credentials if you want to download subtitles.")
        return default_config
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {"username": "", "password": ""}

def login(username, password):
    if not username or not password:
        print("No username/password provided. Downloads will fail (OpenSubtitles.com requires authentication for downloads).")
        return None
        
    print(f"Logging in to OpenSubtitles.com as '{username}'...")
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
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        res_json = response.json()
        token = res_json.get("token")
        if token:
            print("Login successful!")
            return token
        else:
            print("Login response did not contain an authentication token.")
    else:
        print(f"Login failed (HTTP {response.status_code}): {response.text}")
    return None

def search_subtitles(query, languages="vi,en", year=None, season=None, episode=None):
    print(f"Searching subtitles for '{query}' (languages: {languages})...")
    url = "https://api.opensubtitles.com/api/v1/subtitles"
    headers = {
        "Api-Key": API_KEY,
        "User-Agent": USER_AGENT
    }
    params = {
        "query": query,
        "languages": languages
    }
    if year:
        params["year"] = year
    if season:
        params["season_number"] = season
    if episode:
        params["episode_number"] = episode
        
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        print(f"Search failed (HTTP {response.status_code}): {response.text}")
        return []

def download_subtitle(file_id, output_filename, token):
    if not token:
        print("Error: An authentication token is required to download subtitles from OpenSubtitles.com REST API.")
        return False
        
    print(f"Requesting download link for FileID: {file_id}...")
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
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        dl_info = response.json()
        dl_link = dl_info.get("link")
        if dl_link:
            print(f"Downloading from link: {dl_link}...")
            dl_resp = requests.get(dl_link)
            if dl_resp.status_code == 200:
                with open(output_filename, "wb") as f:
                    f.write(dl_resp.content)
                print(f"Saved subtitle to '{output_filename}' successfully!")
                return True
            else:
                print(f"Failed to download subtitle content (HTTP {dl_resp.status_code})")
        else:
            print(f"API download response did not contain a link: {dl_info}")
    else:
        print(f"Download request failed (HTTP {response.status_code}): {response.text}")
    return False

def main():
    config = load_config()
    username = config.get("username", "")
    password = config.get("password", "")
    
    # 1. Search query
    query = input("Enter movie or TV show name to search: ").strip()
    if not query:
        print("Search query cannot be empty.")
        return
        
    languages = input("Enter languages (comma-separated, default: vi,en): ").strip() or "vi,en"
    
    results = search_subtitles(query, languages=languages)
    if not results:
        print("No subtitles found.")
        return
        
    print("\nAvailable Subtitles:")
    for idx, item in enumerate(results, 1):
        attrs = item.get("attributes", {})
        files = attrs.get("files", [])
        file_name = files[0].get("file_name") if files else "N/A"
        language = attrs.get("language")
        downloads = attrs.get("download_count", 0)
        print(f"{idx}. [{language}] {file_name} ({downloads} downloads)")
        
    selection = input("\nEnter the number of the subtitle to download (or press Enter to exit): ").strip()
    if not selection:
        return
        
    try:
        selected_idx = int(selection) - 1
        if selected_idx < 0 or selected_idx >= len(results):
            print("Invalid selection.")
            return
    except ValueError:
        print("Invalid input.")
        return
        
    selected_item = results[selected_idx]
    attrs = selected_item.get("attributes", {})
    files = attrs.get("files", [])
    if not files:
        print("No download files available for this subtitle.")
        return
        
    file_id = files[0].get("file_id")
    file_name = files[0].get("file_name") or "subtitle.srt"
    
    # 2. Login to get token
    token = login(username, password)
    
    # 3. Download
    download_subtitle(file_id, file_name, token)

if __name__ == "__main__":
    main()