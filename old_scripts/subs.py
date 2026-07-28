import os
import requests
import json
import zipfile
import io

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
        response = requests.post(url, headers=HEADERS, json=payload)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("results", [])
        else:
            print(f"Error searching movies: HTTP {response.status_code}")
    except Exception as e:
        print(f"Error searching movies: {e}")
    return []

def get_movie_subtitles(movie_slug):
    url = f"{BASE_URL}/subtitles/{movie_slug}"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            return data.get("subtitles", [])
        else:
            print(f"Error fetching subtitles: HTTP {response.status_code}")
    except Exception as e:
        print(f"Error fetching subtitles: {e}")
    return []

def get_download_token(subtitle_link):
    url = f"{BASE_URL}/subtitle/{subtitle_link}"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            sub = data.get("subtitle", {})
            return sub.get("download_token")
        else:
            print(f"Error fetching subtitle details: HTTP {response.status_code}")
    except Exception as e:
        print(f"Error fetching subtitle details: {e}")
    return None

def download_and_extract(download_token, subtitle_link):
    url = f"{BASE_URL}/subtitle/download/{download_token}"
    dl_headers = HEADERS.copy()
    dl_headers["Referer"] = f"https://subsource.net/subtitle/{subtitle_link}"
    
    try:
        response = requests.get(url, headers=dl_headers)
        if response.status_code == 200:
            # Detect filename from headers
            content_disposition = response.headers.get("Content-Disposition", "")
            filename = "subtitle.zip"
            if "filename=" in content_disposition:
                filename = content_disposition.split("filename=")[1].strip('"')
            
            # Save zip file
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"Saved ZIP archive as: {filename}")
            
            # Try to extract it
            try:
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    for zip_info in z.infolist():
                        name = zip_info.filename
                        print(f"Extracting: {name}")
                        z.extract(zip_info, path=".")
                print("Extraction completed successfully!")
            except Exception as extract_err:
                print(f"Failed to automatically extract ZIP archive: {extract_err}")
                
            return True
        else:
            print(f"Download failed: HTTP {response.status_code}")
            if response.text:
                print(f"Server response: {response.text[:200]}")
    except Exception as e:
        print(f"Download error: {e}")
    return False

def main():
    print("=== SubSource Subtitle Downloader ===")
    
    # 1. Search for movie / show
    query = input("Enter movie or TV show name to search: ").strip()
    if not query:
        print("Search query cannot be empty.")
        return
        
    results = search_movies(query)
    if not results:
        print("No movies or TV shows found.")
        return
        
    print("\nSearch Results:")
    for idx, item in enumerate(results, 1):
        title = item.get("title")
        year = item.get("releaseYear")
        mtype = item.get("type", "movie").capitalize()
        print(f"{idx}. {title} ({mtype}, {year})")
        
    selection = input("\nSelect a result number (or press Enter to exit): ").strip()
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
        
    movie = results[selected_idx]
    movie_link = movie.get("link", "")
    movie_slug = movie_link.replace("/subtitles/", "").strip("/")
    if not movie_slug:
        print("Error: Could not parse movie slug from link.")
        return
        
    # 2. Get available subtitles
    print(f"\nFetching available subtitles for '{movie.get('title')}'...")
    subtitles = get_movie_subtitles(movie_slug)
    if not subtitles:
        print("No subtitles found for this title.")
        return
        
    # Ask for language filters
    lang_filter_input = input("Enter language codes to filter by (comma-separated, e.g. vi,en. Press Enter to list all): ").strip().lower()
    
    filtered_subs = subtitles
    if lang_filter_input:
        langs = [l.strip() for l in lang_filter_input.split(",") if l.strip()]
        filtered_subs = [s for s in subtitles if s.get("language", "").lower() in langs]
        
    if not filtered_subs:
        print("No subtitles matched the selected languages. Showing all available subtitles instead.")
        filtered_subs = subtitles
        
    print("\nAvailable Subtitles:")
    for idx, sub in enumerate(filtered_subs, 1):
        language = sub.get("language", "unknown").capitalize()
        release_info = sub.get("release_info", "N/A")
        rating = sub.get("rating", "unrated")
        print(f"{idx}. [{language}] {release_info} (Rating: {rating})")
        
    sub_selection = input("\nSelect a subtitle number to download (or press Enter to exit): ").strip()
    if not sub_selection:
        return
        
    try:
        sub_idx = int(sub_selection) - 1
        if sub_idx < 0 or sub_idx >= len(filtered_subs):
            print("Invalid selection.")
            return
    except ValueError:
        print("Invalid input.")
        return
        
    selected_sub = filtered_subs[sub_idx]
    sub_link = selected_sub.get("link")
    if not sub_link:
        print("Error: Selected subtitle does not have a valid link.")
        return
        
    # 3. Get download token and download
    print("Fetching download token...")
    download_token = get_download_token(sub_link)
    if not download_token:
        print("Failed to acquire download token.")
        return
        
    print("Downloading subtitle...")
    download_and_extract(download_token, sub_link)

if __name__ == "__main__":
    main()