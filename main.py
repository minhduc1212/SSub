import os
import sys
import concurrent.futures
from src.config import load_config
from src import opensubtitles, subsource, subdl, subscene, addic7ed, opensubtitles_org

def search_provider(provider_name, search_fn, query, languages, *args):
    try:
        results = search_fn(query, languages, *args)
        return results
    except Exception as e:
        print(f"\n[{provider_name}] Search failed: {e}")
        return []

def main():
    print("==================================================")
    print("        MULTI-SITE SUBTITLE DOWNLOADER            ")
    print("==================================================")
    
    # Load configuration
    config = load_config()
    
    query = input("Enter movie or TV show name to search: ").strip()
    if not query:
        print("Search query cannot be empty.")
        return
        
    languages = input("Enter languages (comma-separated, default: vi,en): ").strip() or "vi,en"
    
    print("\nInitializing search across all subtitle sources...")
    
    results = []
    
    # We will use ThreadPoolExecutor to search all sites concurrently for speed
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(
                search_provider, "OpenSubtitles.com", opensubtitles.search, query, languages
            ): "OpenSubtitles.com",
            executor.submit(
                search_provider, "SubSource", subsource.search, query, languages
            ): "SubSource",
            executor.submit(
                search_provider, "SubDL", subdl.search, query, languages, config.get("subdl_api_key")
            ): "SubDL",
            executor.submit(
                search_provider, "SubScene", subscene.search, query, languages
            ): "SubScene",
            executor.submit(
                search_provider, "Addic7ed", addic7ed.search, query, languages
            ): "Addic7ed",
            executor.submit(
                search_provider, "OpenSubtitles.org", opensubtitles_org.search, query, languages
            ): "OpenSubtitles.org",
        }
        
        for future in concurrent.futures.as_completed(futures):
            provider = futures[future]
            res = future.result()
            if res:
                results.extend(res)
                print(f"[{provider}] Found {len(res)} subtitle options.")
            else:
                # If SubDL returned 0 because API key is empty, don't show warning
                if provider == "SubDL" and not config.get("subdl_api_key"):
                    pass
                elif provider == "Addic7ed":
                    # Addic7ed only works for TV shows when season/episode notation is provided
                    pass
                else:
                    print(f"[{provider}] No subtitles found or provider skipped.")
                    
    if not results:
        print("\nNo subtitles found on any platform.")
        # If Addic7ed was skipped, print a reminder for TV shows
        if not re.search(r'[sS](\d+)\s*[eE](\d+)', query) and not re.search(r'(\d+)\s*x\s*(\d+)', query):
            print("\nReminder: To search on Addic7ed, please include season/episode in your query (e.g. 'Breaking Bad S01E01').")
        return
        
    # Sort results by language and then by provider
    results.sort(key=lambda x: (x.get("language", ""), x.get("provider", "")))
    
    print(f"\n==================================================")
    print(f" Found {len(results)} subtitle options:")
    print(f"==================================================")
    
    for idx, item in enumerate(results, 1):
        provider = item.get("provider", "Unknown").upper()
        lang = item.get("language", "unknown").upper()
        release = item.get("release_info", "N/A")
        print(f"{idx:3d}. [{provider}] [{lang}] {release}")
        
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
    provider = selected_item["provider"]
    
    print(f"\nDownloading selected subtitle via {provider}...")
    
    success = False
    if provider == "OpenSubtitles":
        success = opensubtitles.download(selected_item, config)
    elif provider == "SubSource":
        success = subsource.download(selected_item, config)
    elif provider == "SubDL":
        success = subdl.download(selected_item, config)
    elif provider == "SubScene":
        success = subscene.download(selected_item, config)
    elif provider == "Addic7ed":
        success = addic7ed.download(selected_item, config)
    elif provider == "OpenSubtitlesOrg":
        success = opensubtitles_org.download(selected_item, config)
        
    if success:
        print("\nSubtitle downloaded and processed successfully!")
    else:
        print("\nFailed to download subtitle.")

# Lazy load re module if not imported
import re

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
