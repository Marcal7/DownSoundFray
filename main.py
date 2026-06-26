import os
import sys
import json
import asyncio
import subprocess
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração e estado global
config = {
    "download_folder": os.path.expanduser("~/Music")
}
active_downloads = {}
download_queue = asyncio.Queue()

class DownloadRequest(BaseModel):
    url: str

def select_folder_dialog():
    ps_script = f"""
Add-Type -AssemblyName System.windows.forms
$f = New-Object System.Windows.Forms.FolderBrowserDialog
$f.Description = "Selecione a pasta de download"
$f.SelectedPath = "{config['download_folder']}"
if ($f.ShowDialog() -eq "OK") {{ Write-Output $f.SelectedPath }}
"""
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, creationflags=0x08000000)
        return result.stdout.strip()
    except Exception as e:
        print("Erro ao abrir dialogo:", e)
        return ""

@app.get("/api/config")
def get_config():
    return config

@app.post("/api/select-folder")
def select_folder():
    folder = select_folder_dialog()
    if folder:
        config["download_folder"] = folder
    return {"folder": config["download_folder"]}

async def download_worker():
    while True:
        task = await download_queue.get()
        url = task["url"]
        dl_id = task["id"]
        platform = task["platform"]
        
        try:
            if platform == "spotify":
                await download_spotify(url, dl_id)
            else:
                await download_ytdlp(url, dl_id)
        except Exception as e:
            active_downloads[dl_id]["status"] = "error"
            active_downloads[dl_id]["error"] = str(e)
            
        download_queue.task_done()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(download_worker())

@app.post("/api/download")
async def start_download(req: DownloadRequest):
    url = req.url
    dl_id = str(len(active_downloads) + 1)
    
    if "spotify.com" in url:
        platform = "spotify"
    elif "soundcloud.com" in url:
        platform = "soundcloud"
    else:
        platform = "other"

    active_downloads[dl_id] = {
        "id": dl_id,
        "url": url,
        "platform": platform,
        "status": "starting",
        "percent": 0,
        "title": "Iniciando download..."
    }
    
    await download_queue.put(active_downloads[dl_id])
    return {"status": "success", "download_id": dl_id, "platform": platform}

async def progress_generator():
    while True:
        # Yield current state of all downloads
        for dl_id, data in list(active_downloads.items()):
            yield {"event": "message", "data": json.dumps(data)}
        await asyncio.sleep(0.5)

@app.get("/api/progress")
async def sse_progress(request: Request):
    return EventSourceResponse(progress_generator())

async def download_spotify(url, dl_id):
    active_downloads[dl_id]["status"] = "downloading"
    active_downloads[dl_id]["title"] = "Iniciando Spotify..."
    active_downloads[dl_id]["percent"] = 5
    active_downloads[dl_id]["total_songs"] = 1
    active_downloads[dl_id]["current_song"] = 0
    active_downloads[dl_id]["status_text"] = "Preparando..."
    
    cmd = [
        sys.executable, "-m", "spotdl", url,
        "--output", os.path.join(config["download_folder"], "{artist} - {title}.{ext}"),
        "--bitrate", "320k",
        "--format", "mp3"
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    
    import re
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        decoded = line.decode('utf-8', errors='ignore').strip()
        print("[spotdl]", decoded)
        
        m = re.search(r'Found\s+(\d+)\s+songs', decoded)
        if m:
            active_downloads[dl_id]["total_songs"] = int(m.group(1))
            active_downloads[dl_id]["title"] = f"Playlist Spotify ({m.group(1)} músicas)"
            
        if "Downloaded" in decoded:
            active_downloads[dl_id]["current_song"] += 1
            curr = active_downloads[dl_id]["current_song"]
            tot = active_downloads[dl_id]["total_songs"]
            if tot > 1:
                active_downloads[dl_id]["percent"] = int((curr / tot) * 100)
                active_downloads[dl_id]["status_text"] = f"Baixando ({curr} de {tot})"
            else:
                active_downloads[dl_id]["percent"] = 90
        elif "Found" in decoded and not m:
            active_downloads[dl_id]["percent"] = 10
            
    await process.wait()
    
    if process.returncode == 0:
        active_downloads[dl_id]["status"] = "finished"
        active_downloads[dl_id]["percent"] = 100
        active_downloads[dl_id]["title"] = "Download concluído!"
    else:
        active_downloads[dl_id]["status"] = "error"
        active_downloads[dl_id]["error"] = "Erro ao baixar via spotdl."

def ytdlp_hook(dl_id):
    def hook(d):
        tot = d.get('info_dict', {}).get('playlist_count') or 1
        curr = d.get('info_dict', {}).get('playlist_index') or 1
        
        active_downloads[dl_id]["total_songs"] = tot
        active_downloads[dl_id]["current_song"] = curr
        
        if tot > 1:
            active_downloads[dl_id]["status_text"] = f"Baixando ({curr} de {tot})"
            active_downloads[dl_id]["title"] = f"Playlist ({tot} músicas)"

        if d['status'] == 'finished':
            if tot == 1 or curr == tot:
                active_downloads[dl_id]["percent"] = 100
            else:
                active_downloads[dl_id]["percent"] = int((curr / tot) * 100)
                
            if 'filename' in d:
                filename = os.path.basename(d['filename'])
                if tot == 1:
                    active_downloads[dl_id]["title"] = filename
        elif d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%', '').strip()
            import re
            p = re.sub(r'\x1b[^m]*m', '', p)
            try:
                song_p = float(p)
                if tot > 1:
                    overall = ((curr - 1) * 100 + song_p) / tot
                    active_downloads[dl_id]["percent"] = float(f"{overall:.1f}")
                else:
                    active_downloads[dl_id]["percent"] = song_p
            except:
                pass
            
            if 'filename' in d and tot == 1:
                filename = os.path.basename(d['filename'])
                active_downloads[dl_id]["title"] = filename
    return hook

async def download_ytdlp(url, dl_id):
    active_downloads[dl_id]["status"] = "downloading"
    
    ffmpeg_path = os.path.expanduser("~/.spotdl/ffmpeg.exe")
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(config["download_folder"], '%(title)s.%(ext)s'),
        'ffmpeg_location': ffmpeg_path if os.path.exists(ffmpeg_path) else None,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
        'progress_hooks': [ytdlp_hook(dl_id)],
        'quiet': True,
        'no_warnings': True
    }
    
    def run_ydl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
    try:
        await asyncio.to_thread(run_ydl)
        active_downloads[dl_id]["status"] = "finished"
        active_downloads[dl_id]["percent"] = 100
    except Exception as e:
        print("yt-dlp error:", e)
        active_downloads[dl_id]["status"] = "error"
        active_downloads[dl_id]["error"] = "Falha no yt-dlp: " + str(e)

# Serve a pasta do frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
