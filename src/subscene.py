import os
import re
import json
import requests
from bs4 import BeautifulSoup
from src.utils import download_file
from src.config import load_config, save_config

BASE_URL = "https://sub-scene.com"

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

def get_subscene_languages(languages_str):
    lang_list = [l.strip().lower() for l in languages_str.split(",") if l.strip()]
    subscene_langs = []
    for l in lang_list:
        if l in LANG_MAP:
            subscene_langs.append(LANG_MAP[l])
        else:
            subscene_langs.append(l) # fallback
    return subscene_langs

def try_search_with_cookies(query, cf_clearance, user_agent):
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://sub-scene.com/"
    }
    cookies = {
        "cf_clearance": cf_clearance
    }
    url = f"{BASE_URL}/search"
    params = {"query": query}
    
    try:
        r = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=12)
        if r.status_code == 200 and "Just a moment..." not in r.text:
            return r.text
    except Exception as e:
        print(f"SubScene request error: {e}")
    return None

def get_cookies_via_playwright(query):
    # We do a lazy import of playwright so that if the user doesn't have it or can't run it,
    # the rest of the application still works.
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SubScene] playwright library is not installed. Run 'pip install playwright' and 'playwright install'.")
        return None, None

    try:
        with sync_playwright() as p:
            print("\n[SubScene] Opening headful browser to bypass Cloudflare Turnstile...")
            print("[SubScene] Please solve the challenge in the browser window if prompted.")
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            
            url = f"{BASE_URL}/search?query={query}"
            page.goto(url)
            
            # Poll for page title to change
            cf_clearance = None
            user_agent = page.evaluate("navigator.userAgent")
            
            for _ in range(25):
                page.wait_for_timeout(1000)
                try:
                    title = page.title()
                    if title and "Just a moment..." not in title and "Loading" not in title:
                        # Success
                        cookies = context.cookies()
                        for cookie in cookies:
                            if cookie["name"] == "cf_clearance":
                                cf_clearance = cookie["value"]
                                break
                        break
                except:
                    pass
            browser.close()
            return cf_clearance, user_agent
    except Exception as e:
        print(f"[SubScene] Playwright automatic bypass failed: {e}")
        return None, None

def search(query, languages="vi,en"):
    config = load_config()
    cf_clearance = config.get("subscene_cf_clearance", "")
    user_agent = config.get("subscene_user_agent", "")
    
    html = None
    if cf_clearance and user_agent:
        html = try_search_with_cookies(query, cf_clearance, user_agent)
        
    if not html:
        print("[SubScene] Cloudflare cookie missing or expired. Trying automatic bypass...")
        cf_clearance, user_agent = get_cookies_via_playwright(query)
        if cf_clearance and user_agent:
            config["subscene_cf_clearance"] = cf_clearance
            config["subscene_user_agent"] = user_agent
            save_config(config)
            html = try_search_with_cookies(query, cf_clearance, user_agent)
            
    if not html:
        print("[SubScene] Cloudflare bypass failed. You can manually solve it in your browser")
        print("           and put 'subscene_cf_clearance' and 'subscene_user_agent' in config.json.")
        print("           Skipping SubScene results.")
        return []
        
    # Parse movies from search results
    print(f"Parsing movie list from SubScene...")
    soup = BeautifulSoup(html, 'html.parser')
    movies = []
    
    # Check for links in search page starting with /subscene/
    links = soup.find_all('a')
    seen_ids = set()
    for l in links:
        href = l.get('href', '')
        # Match /subscene/{id} but NOT /subscene/{id}/{lang}
        match = re.match(r'^/subscene/(\d+)$', href)
        if match:
            movie_id = match.group(1)
            if movie_id not in seen_ids:
                seen_ids.add(movie_id)
                movies.append({
                    "id": movie_id,
                    "title": l.text.strip(),
                    "url": f"{BASE_URL}{href}"
                })
                
    if not movies:
        print("[SubScene] No movie pages found in search results.")
        return []
        
    target_langs = get_subscene_languages(languages)
    formatted = []
    
    # Fetch subtitles for the top 2 matching movies
    for movie in movies[:2]:
        movie_title = movie["title"]
        movie_url = movie["url"]
        
        print(f"Fetching subtitles for movie: '{movie_title}' from {movie_url}...")
        try:
            r = requests.get(movie_url, headers={"User-Agent": user_agent}, timeout=10)
            if r.status_code != 200:
                continue
                
            movie_soup = BeautifulSoup(r.text, 'html.parser')
            rows = movie_soup.find_all('tr')
            
            for row in rows:
                spans = row.find_all('span')
                if len(spans) >= 2:
                    sub_lang = spans[0].text.strip()
                    # Filter by language
                    if target_langs and sub_lang.lower() not in target_langs:
                        continue
                        
                    release_info = spans[1].text.strip()
                    # Find subtitle link
                    sub_link = None
                    for a in row.find_all('a'):
                        href = a.get('href', '')
                        if href.startswith('/subtitle/'):
                            sub_link = href
                            break
                            
                    if sub_link:
                        formatted.append({
                            "provider": "SubScene",
                            "language": sub_lang.lower(),
                            "release_info": f"{movie_title} - {release_info}",
                            "link": f"{BASE_URL}{sub_link}",
                            "id": f"{BASE_URL}{sub_link}"
                        })
        except Exception as e:
            print(f"[SubScene] Error fetching subtitles for movie {movie_title}: {e}")
            
    return formatted

def download(item, config=None):
    sub_url = item["link"]
    user_agent = config.get("subscene_user_agent", DEFAULT_HEADERS["User-Agent"]) if config else DEFAULT_HEADERS["User-Agent"]
    
    try:
        # Fetch the subtitle detail page to get the direct download link
        print(f"Fetching subtitle detail page {sub_url}...")
        r = requests.get(sub_url, headers={"User-Agent": user_agent}, timeout=10)
        if r.status_code != 200:
            print("Failed to load subtitle detail page.")
            return False
            
        soup = BeautifulSoup(r.text, 'html.parser')
        # Find the download button link which starts with /download/
        download_btn = None
        for a in soup.find_all('a'):
            href = a.get('href', '')
            if href.startswith('/download/'):
                download_btn = href
                break
                
        if not download_btn:
            print("Failed to find download button link on the page.")
            return False
            
        dl_url = f"{BASE_URL}{download_btn}"
        # Download and extract the subtitle ZIP file
        return download_file(dl_url, headers={"User-Agent": user_agent, "Referer": sub_url})
    except Exception as e:
        print(f"[SubScene] Download error: {e}")
        return False

# Fallback headers if not passed
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
