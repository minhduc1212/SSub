import os
import sys
import asyncio
import tempfile
import shutil
import zipfile
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

# Ensure root directory is in sys.path to allow imports from src
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.config import load_config, save_config
from src import opensubtitles, subsource, subdl, addic7ed, opensubtitles_org

app = FastAPI(title="SSub API", description="Multi-site subtitle downloader API")

# Add CORS middleware to support calls from local frontends or CLI clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def async_search_provider(provider_name, search_fn, query, languages, *args):
    try:
        # Run synchronous search function in Starlette's threadpool to prevent blocking the async loop
        results = await run_in_threadpool(search_fn, query, languages, *args)
        return results
    except Exception as e:
        print(f"[{provider_name}] Search failed: {e}")
        return []

@app.get("/api/search")
async def search(query: str, languages: str = "vi,en"):
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    config = load_config()
    
    # Run concurrent searches across all subtitle providers
    tasks = [
        async_search_provider("OpenSubtitles.com", opensubtitles.search, query, languages),
        async_search_provider("SubSource", subsource.search, query, languages),
        async_search_provider("SubDL", subdl.search, query, languages, config.get("subdl_api_key")),
        async_search_provider("Addic7ed", addic7ed.search, query, languages),
        async_search_provider("OpenSubtitles.org", opensubtitles_org.search, query, languages),
    ]
    
    all_results = await asyncio.gather(*tasks)
    
    # Flatten list of lists
    flat_results = []
    for res in all_results:
        if res:
            flat_results.extend(res)
            
    # Sort results by language and then by provider
    flat_results.sort(key=lambda x: (x.get("language", ""), x.get("provider", "").lower()))
    
    return flat_results

def cleanup_temp_dir(temp_dir: str):
    try:
        shutil.rmtree(temp_dir)
        print(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        print(f"Error cleaning up temporary directory {temp_dir}: {e}")

@app.post("/api/download")
async def download(item: dict, background_tasks: BackgroundTasks):
    provider = item.get("provider")
    if not provider:
        raise HTTPException(status_code=400, detail="Provider must be specified.")
        
    config = load_config().copy()
    
    # Create a unique temporary directory to hold the downloaded files
    temp_dir = tempfile.mkdtemp(prefix="ssub_dl_")
    config["output_dir"] = temp_dir
    
    # Map of providers to their download functions
    providers_map = {
        "OpenSubtitles": opensubtitles.download,
        "SubSource": subsource.download,
        "SubDL": subdl.download,
        "Addic7ed": addic7ed.download,
        "OpenSubtitlesOrg": opensubtitles_org.download
    }
    
    download_fn = providers_map.get(provider)
    if not download_fn:
        cleanup_temp_dir(temp_dir)
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
        
    print(f"Starting download from {provider} to {temp_dir}...")
    
    # Run the synchronous download in the threadpool
    try:
        success = await run_in_threadpool(download_fn, item, config)
    except Exception as e:
        cleanup_temp_dir(temp_dir)
        raise HTTPException(status_code=500, detail=f"Download execution crashed: {str(e)}")
        
    if not success:
        cleanup_temp_dir(temp_dir)
        raise HTTPException(status_code=500, detail="Subtitles download failed at the provider level.")
        
    # Scan the temporary directory to find the downloaded files
    downloaded_files = []
    for root, _, filenames in os.walk(temp_dir):
        for f in filenames:
            file_path = os.path.join(root, f)
            # Exclude directory/metadata leftovers
            if not f.startswith("._") and f != ".DS_Store":
                downloaded_files.append(file_path)
                
    if not downloaded_files:
        cleanup_temp_dir(temp_dir)
        raise HTTPException(status_code=500, detail="Download succeeded but no files were found on disk.")
        
    # Schedule the cleanup of the temp directory after the response has been sent
    background_tasks.add_task(cleanup_temp_dir, temp_dir)
    
    # Filter for typical subtitle formats to prioritize
    subtitle_files = [f for f in downloaded_files if f.lower().endswith(('.srt', '.ass', '.vtt', '.sub'))]
    
    # If there is exactly one subtitle file, serve it directly
    if len(subtitle_files) == 1:
        target_file = subtitle_files[0]
        filename = os.path.basename(target_file)
        return FileResponse(
            target_file, 
            filename=filename, 
            media_type="application/octet-stream",
            headers={"Access-Control-Expose-Headers": "Content-Disposition"}
        )
        
    # If there are multiple subtitle files, zip them together
    if len(subtitle_files) > 1:
        zip_path = os.path.join(temp_dir, "subtitles.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for f in subtitle_files:
                zipf.write(f, os.path.relpath(f, temp_dir))
        return FileResponse(
            zip_path, 
            filename="subtitles.zip", 
            media_type="application/zip",
            headers={"Access-Control-Expose-Headers": "Content-Disposition"}
        )
        
    # Fallback to serving the first file found (even if not recognized as standard subtitle extension)
    target_file = downloaded_files[0]
    filename = os.path.basename(target_file)
    return FileResponse(
        target_file, 
        filename=filename, 
        media_type="application/octet-stream",
        headers={"Access-Control-Expose-Headers": "Content-Disposition"}
    )

@app.get("/api/config")
async def get_config():
    return load_config()

@app.post("/api/config")
async def update_config(new_config: dict):
    current_config = load_config()
    
    for key, value in new_config.items():
        current_config[key] = value
        
    if save_config(current_config):
        return {"status": "success", "message": "Configuration saved successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to save configuration.")

@app.get("/")
async def root():
    return {
        "status": "active",
        "message": "SSub API is running. Frontend has been removed from this server.",
        "endpoints": {
            "search": "GET /api/search?query=<query>&languages=<languages>",
            "download": "POST /api/download (with subtitle item JSON body)",
            "get_config": "GET /api/config",
            "update_config": "POST /api/config"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
