import os
import xmlrpc.client
import base64
import gzip
import io
from src.utils import clean_filename

URL = "https://api.opensubtitles.org/xml-rpc"
USER_AGENT = "VLSub v0.10.0"

LANG_MAP_3 = {
    "en": "eng",
    "vi": "vie",
    "ar": "ara",
    "es": "spa",
    "fr": "fre",
    "de": "ger",
    "it": "ita",
    "ru": "rus",
    "zh": "chi",
    "ja": "jpn",
    "ko": "kor",
}

def get_3_letter_langs(languages_str):
    lang_list = [l.strip().lower() for l in languages_str.split(",") if l.strip()]
    langs_3 = []
    for l in lang_list:
        if l in LANG_MAP_3:
            langs_3.append(LANG_MAP_3[l])
        else:
            langs_3.append(l) # fallback
    return ",".join(langs_3)

def search(query, languages="vi,en"):
    print(f"Searching OpenSubtitles.org for '{query}'...")
    try:
        server = xmlrpc.client.ServerProxy(URL)
        login_info = server.LogIn('', '', 'en', USER_AGENT)
        token = login_info.get('token')
        
        if not token:
            print("[OpenSubtitlesOrg] Login failed to yield a session token.")
            return []
            
        sublang = get_3_letter_langs(languages)
        params = [{'query': query, 'sublanguageid': sublang}]
        
        results = server.SearchSubtitles(token, params)
        data = results.get('data', [])
        
        formatted = []
        for sub in data:
            sub_id = sub.get('IDSubtitleFile')
            file_name = sub.get('SubFileName') or "subtitle.srt"
            lang = sub.get('ISO639') or "unknown"
            downloads = sub.get('SubDownloadsCnt', 0)
            rating = sub.get('SubRating', 0.0)
            movie_name = sub.get('MovieName', "")
            
            # Combine movie title and sub file name for descriptive release info
            release_info = f"{movie_name} - {file_name}"
            
            formatted.append({
                "provider": "OpenSubtitlesOrg",
                "language": lang,
                "release_info": release_info,
                "id": sub_id,
                "file_name": file_name,
                "downloads": downloads,
                "rating": rating
            })
            
        server.LogOut(token)
        return formatted
    except Exception as e:
        print(f"[OpenSubtitlesOrg] XML-RPC search error: {e}")
        return []

def download(item, config=None):
    sub_id = item["id"]
    file_name = item.get("file_name", "subtitle.srt")
    
    try:
        server = xmlrpc.client.ServerProxy(URL)
        login_info = server.LogIn('', '', 'en', USER_AGENT)
        token = login_info.get('token')
        
        if not token:
            print("[OpenSubtitlesOrg] Login failed during download request.")
            return False
            
        print(f"Downloading subtitle {sub_id} from OpenSubtitles.org...")
        dl_response = server.DownloadSubtitles(token, [sub_id])
        data_list = dl_response.get("data", [])
        
        success = False
        if data_list:
            sub_data = data_list[0]
            b64_content = sub_data.get("data")
            if b64_content:
                # Decode base64
                compressed_bytes = base64.b64decode(b64_content)
                # Decompress gzip
                with gzip.GzipFile(fileobj=io.BytesIO(compressed_bytes)) as f:
                    srt_content = f.read()
                    
                # Clean name and save directly
                filename = clean_filename(file_name)
                output_dir = config.get("output_dir", ".") if config else "."
                out_path = os.path.join(output_dir, filename)
                with open(out_path, "wb") as f_out:
                    f_out.write(srt_content)
                print(f"Saved subtitle to '{out_path}' successfully!")
                success = True
            else:
                print("[OpenSubtitlesOrg] Download response data was empty.")
        else:
            print("[OpenSubtitlesOrg] Subtitle download ID not found on server.")
            
        server.LogOut(token)
        return success
    except Exception as e:
        print(f"[OpenSubtitlesOrg] Download error: {e}")
        return False
