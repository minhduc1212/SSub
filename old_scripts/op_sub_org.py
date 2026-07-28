import os
import json
import time
import requests

SESSION_FILE = "session.json"
url = "https://www.opensubtitles.org/vi/search/sublanguageid-vie/idmovie-2447180"

def get_cookies_via_browser(url):
    print("Launching browser to refresh cookies (Cloudflare bypass)...")
    from playwright.sync_api import sync_playwright
    user_data_dir = os.path.abspath(".playwright_data")
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,  # Run headful so the user/UI can bypass Cloudflare/captchas if needed
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ],
            no_viewport=True
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        
        print(f"Navigating to {url}...")
        page.goto(url)
        
        # Wait up to 60 seconds for Cloudflare to verify the browser
        start_time = time.time()
        success = False
        while time.time() - start_time < 60:
            title = page.title()
            safe_title = title.encode('ascii', 'backslashreplace').decode('ascii')
            print(f"Current page title: {safe_title}")
            
            # Check if it loaded the target page
            if "Just a moment" not in title and "Cloudflare" not in title and "Making sure you're not a bot" not in title and title != "":
                content = page.content().lower()
                if "opensubtitles" in content or "search" in content:
                    success = True
                    break
            time.sleep(2)
            
        if not success:
            print("Failed to automatically detect Cloudflare bypass. Waiting 10 seconds for manual resolution...")
            time.sleep(10)
            
        cookies = context.cookies()
        user_agent = page.evaluate("navigator.userAgent")
        
        context.close()
        
        cookies_dict = {c['name']: c['value'] for c in cookies}
        return cookies_dict, user_agent

def load_session():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_session(cookies, user_agent):
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump({"cookies": cookies, "user_agent": user_agent}, f, indent=2)
    except Exception as e:
        print(f"Error saving session file: {e}")

def get_with_session(url):
    session_data = load_session()
    
    if session_data:
        cookies = session_data.get("cookies", {})
        user_agent = session_data.get("user_agent", "")
    else:
        cookies, user_agent = get_cookies_via_browser(url)
        save_session(cookies, user_agent)
        
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "vi",
        "priority": "u=0, i",
        "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": user_agent
    }
    
    print("Attempting request with current session cookies...")
    response = requests.get(url, headers=headers, cookies=cookies)
    
    # If the response indicates authorization/forbidden/cloudflare issues, refresh cookies and retry once
    if response.status_code in (401, 403, 503) or "Just a moment" in response.text:
        print(f"Request failed with status {response.status_code}. Session may have expired. Refreshing...")
        cookies, user_agent = get_cookies_via_browser(url)
        save_session(cookies, user_agent)
        headers["user-agent"] = user_agent
        response = requests.get(url, headers=headers, cookies=cookies)
        
    return response

# Execute request
response = get_with_session(url)
print("Final Response Status Code:", response.status_code)