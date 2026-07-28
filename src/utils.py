import os
import requests
import zipfile
import io
import re

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
}

def clean_filename(filename):
    # Remove invalid characters for windows filesystems
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def get_filename_from_headers(headers, default="subtitle.zip"):
    content_disposition = headers.get("Content-Disposition", "")
    if not content_disposition:
        return default
        
    # Match filename="..."
    matches = re.findall(r'filename=["\']?(.*?)["\']?$', content_disposition)
    if matches:
        return clean_filename(matches[0])
        
    # Fallback match without quotes
    parts = content_disposition.split("filename=")
    if len(parts) > 1:
        return clean_filename(parts[1].split(";")[0].strip())
        
    return default

def download_file(url, headers=None, cookies=None, output_dir="."):
    """
    Downloads a subtitle. If it's a ZIP archive, extracts it.
    Otherwise, saves it directly as a subtitle file.
    """
    req_headers = DEFAULT_HEADERS.copy()
    if headers:
        req_headers.update(headers)
        
    try:
        print(f"Downloading from {url}...")
        response = requests.get(url, headers=req_headers, cookies=cookies, timeout=30)
        if response.status_code != 200:
            print(f"Download failed: HTTP {response.status_code}")
            return False
            
        content = response.content
        if not content:
            print("Download failed: empty response content.")
            return False
            
        # Detect ZIP archive signature (PK\x03\x04)
        is_zip = content.startswith(b"PK\x03\x04")
        
        filename = get_filename_from_headers(response.headers, default="subtitle.zip" if is_zip else "subtitle.srt")
        
        if is_zip:
            print(f"Saved ZIP archive as temporary buffer, extracting...")
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    for zip_info in z.infolist():
                        name = zip_info.filename
                        # Decode name if encoded in cp437
                        try:
                            decoded_name = name.encode('cp437').decode('utf-8')
                        except:
                            decoded_name = name
                            
                        decoded_name = clean_filename(decoded_name)
                        out_path = os.path.join(output_dir, decoded_name)
                        print(f"  Extracting: {decoded_name}")
                        
                        # Write the file manually to support decoded_name and nested dirs safely
                        if zip_info.is_dir():
                            os.makedirs(out_path, exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(out_path), exist_ok=True)
                            with open(out_path, "wb") as f_out:
                                f_out.write(z.read(zip_info.filename))
                print("Extraction completed successfully!")
                return True
            except Exception as extract_err:
                print(f"Failed to extract ZIP archive: {extract_err}")
                # Save the raw zip anyway
                out_path = os.path.join(output_dir, filename)
                with open(out_path, "wb") as f:
                    f.write(content)
                print(f"Saved raw ZIP to '{out_path}'")
                return True
        else:
            # Raw subtitle file (SRT, ASS, VTT, etc.)
            out_path = os.path.join(output_dir, filename)
            with open(out_path, "wb") as f:
                f.write(content)
            print(f"Saved subtitle to '{out_path}' successfully!")
            return True
            
    except Exception as e:
        print(f"Download/Extraction error: {e}")
        return False
