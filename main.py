import os
import sys
import json
import shutil
import asyncio
import subprocess
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from typing import Optional
import yt_dlp

# Adicionar ~/.spotdl ao PATH para garantir que o ffmpeg baixado pelo spotdl seja encontrado
spotdl_dir = os.path.expanduser("~/.spotdl")
if os.path.exists(spotdl_dir) and spotdl_dir not in os.environ["PATH"]:
    os.environ["PATH"] = spotdl_dir + os.pathsep + os.environ["PATH"]

app = FastAPI(title="Downfy API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração e estado global
config = {
    "download_folder": os.path.expanduser("~/Music"),
    "default_format": "mp3",
    "default_quality": "320k"
}

active_downloads = {}
active_processes = {}  # dl_id -> subprocess / task handle
download_queue = asyncio.Queue()
CONCURRENT_WORKERS = 3

class DownloadRequest(BaseModel):
    url: str
    format: Optional[str] = "mp3"
    quality: Optional[str] = "320k"

class ConfigUpdateRequest(BaseModel):
    download_folder: Optional[str] = None
    default_format: Optional[str] = None
    default_quality: Optional[str] = None

def check_ffmpeg():
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return {"installed": True, "path": ffmpeg_path}
    
    # Checar caminho alternativo do spotdl
    alt_path = os.path.expanduser("~/.spotdl/ffmpeg.exe")
    if os.path.exists(alt_path):
        return {"installed": True, "path": alt_path}
        
    return {"installed": False, "path": None}

def select_folder_dialog_native():
    """Tenta abrir a janela nativa de seleção de pasta usando Tkinter ou PowerShell."""
    current_folder = config["download_folder"]
    if not os.path.exists(current_folder):
        current_folder = os.path.expanduser("~")

    # 1. Tentativa via Tkinter (Rápido e nativo)
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        root.focus_force()
        folder = filedialog.askdirectory(
            initialdir=current_folder,
            title="Selecione a pasta para os downloads do Downfy"
        )
        root.destroy()
        if folder:
            return os.path.normpath(folder)
    except Exception as e:
        print("[Folder Picker] Tkinter falhou, tentando PowerShell:", e)

    # 2. Fallback via PowerShell
    ps_script = f"""
[System.Reflection.Assembly]::LoadWithPartialName("System.windows.forms") | Out-Null
$f = New-Object System.Windows.Forms.FolderBrowserDialog
$f.Description = "Selecione a pasta de download do Downfy"
$f.SelectedPath = "{current_folder}"
$f.ShowNewFolderButton = $true
$top = New-Object System.Windows.Forms.Form
$top.TopMost = $true
if ($f.ShowDialog($top) -eq "OK") {{ Write-Output $f.SelectedPath }}
$top.Dispose()
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        folder = result.stdout.strip()
        if folder and os.path.exists(folder):
            return os.path.normpath(folder)
    except Exception as e:
        print("[Folder Picker] PowerShell falhou:", e)

    return ""

@app.get("/api/config")
def get_config():
    return config

@app.post("/api/config")
def update_config(req: ConfigUpdateRequest):
    if req.download_folder is not None:
        folder = req.download_folder.strip()
        if folder:
            try:
                os.makedirs(folder, exist_ok=True)
                config["download_folder"] = os.path.normpath(folder)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Caminho de pasta inválido: {str(e)}")
    
    if req.default_format is not None:
        config["default_format"] = req.default_format
    if req.default_quality is not None:
        config["default_quality"] = req.default_quality

    return config

@app.get("/api/health")
def health_check():
    ffmpeg_info = check_ffmpeg()
    folder_ok = os.path.exists(config["download_folder"]) and os.access(config["download_folder"], os.W_OK)
    
    return {
        "status": "online",
        "ffmpeg": ffmpeg_info,
        "ytdlp_version": yt_dlp.version.__version__,
        "download_folder": config["download_folder"],
        "folder_writable": folder_ok,
        "active_downloads": len(active_downloads)
    }

@app.post("/api/select-folder")
async def select_folder():
    folder = await asyncio.to_thread(select_folder_dialog_native)
    if folder:
        try:
            os.makedirs(folder, exist_ok=True)
            config["download_folder"] = folder
            return {"status": "success", "folder": config["download_folder"]}
        except Exception as e:
            return {"status": "error", "message": f"Não foi possível salvar na pasta: {str(e)}", "folder": config["download_folder"]}
    return {"status": "cancelled", "folder": config["download_folder"]}

@app.post("/api/open-folder")
def open_folder():
    folder = config["download_folder"]
    if not os.path.exists(folder):
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as e:
            return {"status": "error", "message": f"Pasta não encontrada: {str(e)}"}

    try:
        if os.name == 'nt':
            os.startfile(folder)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', folder])
        else:
            subprocess.Popen(['xdg-open', folder])
        return {"status": "success", "message": "Pasta aberta com sucesso"}
    except Exception as e:
        return {"status": "error", "message": f"Erro ao abrir pasta: {str(e)}"}

@app.post("/api/update-ytdlp")
async def update_ytdlp():
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode('utf-8', errors='ignore')
        if proc.returncode == 0:
            return {"status": "success", "message": "yt-dlp atualizado com sucesso!", "output": output}
        else:
            return {"status": "error", "message": "Falha ao atualizar yt-dlp.", "output": output}
    except Exception as e:
        return {"status": "error", "message": f"Erro: {str(e)}"}

@app.post("/api/install-ffmpeg")
async def install_ffmpeg():
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "spotdl", "--download-ffmpeg",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode('utf-8', errors='ignore')
        
        # Recarregar PATH
        if os.path.exists(spotdl_dir) and spotdl_dir not in os.environ["PATH"]:
            os.environ["PATH"] = spotdl_dir + os.pathsep + os.environ["PATH"]
            
        ffmpeg_info = check_ffmpeg()
        if ffmpeg_info["installed"]:
            return {"status": "success", "message": "FFmpeg instalado e configurado!", "output": output}
        else:
            return {"status": "error", "message": "FFmpeg não foi detectado após a instalação.", "output": output}
    except Exception as e:
        return {"status": "error", "message": f"Erro ao instalar FFmpeg: {str(e)}"}

async def download_worker(worker_id: int):
    while True:
        task = await download_queue.get()
        dl_id = task["id"]
        url = task["url"]
        platform = task["platform"]
        fmt = task.get("format", config["default_format"])
        quality = task.get("quality", config["default_quality"])
        
        # Verificar cancelamento antes de iniciar
        if active_downloads.get(dl_id, {}).get("status") == "cancelled":
            download_queue.task_done()
            continue

        try:
            if platform == "spotify":
                await download_spotify(url, dl_id, fmt, quality)
            else:
                await download_ytdlp(url, dl_id, fmt, quality)
        except asyncio.CancelledError:
            active_downloads[dl_id]["status"] = "cancelled"
            active_downloads[dl_id]["status_text"] = "Download cancelado pelo usuário."
        except Exception as e:
            active_downloads[dl_id]["status"] = "error"
            active_downloads[dl_id]["error"] = str(e)
            active_downloads[dl_id]["status_text"] = f"Erro: {str(e)}"
        finally:
            active_processes.pop(dl_id, None)
            download_queue.task_done()

@app.on_event("startup")
async def startup_event():
    # Garantir que a pasta de download existe
    try:
        os.makedirs(config["download_folder"], exist_ok=True)
    except Exception:
        pass
        
    # Iniciar trabalhadores concorrentes
    for i in range(CONCURRENT_WORKERS):
        asyncio.create_task(download_worker(i))

@app.post("/api/download")
async def start_download(req: DownloadRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Por favor, insira uma URL válida.")

    # Garantir pasta criada
    folder = config["download_folder"]
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro na pasta de destino: {str(e)}. Altere a pasta antes de baixar.")

    dl_id = str(len(active_downloads) + 1)
    
    if "spotify.com" in url:
        platform = "spotify"
    elif "soundcloud.com" in url:
        platform = "soundcloud"
    else:
        platform = "youtube"

    fmt = req.format or config["default_format"]
    quality = req.quality or config["default_quality"]

    item = {
        "id": dl_id,
        "url": url,
        "platform": platform,
        "format": fmt,
        "quality": quality,
        "status": "starting",
        "percent": 0,
        "title": "Iniciando download...",
        "status_text": "Aguardando na fila...",
        "total_songs": 1,
        "current_song": 0
    }
    
    active_downloads[dl_id] = item
    await download_queue.put(item)
    return {"status": "success", "download_id": dl_id, "platform": platform}

@app.post("/api/cancel/{dl_id}")
async def cancel_download(dl_id: str):
    if dl_id in active_downloads:
        active_downloads[dl_id]["status"] = "cancelled"
        active_downloads[dl_id]["status_text"] = "Download cancelado."
        
        proc_or_task = active_processes.get(dl_id)
        if proc_or_task:
            if isinstance(proc_or_task, asyncio.subprocess.Process):
                try:
                    proc_or_task.terminate()
                except Exception:
                    pass
            elif isinstance(proc_or_task, asyncio.Task):
                proc_or_task.cancel()
        return {"status": "success", "message": "Download cancelado."}
    return {"status": "error", "message": "Download não encontrado."}

@app.post("/api/retry/{dl_id}")
async def retry_download(dl_id: str):
    if dl_id in active_downloads:
        item = active_downloads[dl_id]
        item["status"] = "starting"
        item["percent"] = 0
        item["status_text"] = "Reiniciando download..."
        item["error"] = None
        
        await download_queue.put(item)
        return {"status": "success", "message": "Download reiniciado."}
    return {"status": "error", "message": "Download não encontrado."}

@app.post("/api/clear-finished")
def clear_finished():
    to_remove = [dl_id for dl_id, data in active_downloads.items() if data["status"] in ["finished", "error", "cancelled"]]
    for dl_id in to_remove:
        active_downloads.pop(dl_id, None)
        active_processes.pop(dl_id, None)
    return {"status": "success", "cleared": len(to_remove)}

async def progress_generator():
    while True:
        for dl_id, data in list(active_downloads.items()):
            yield {"event": "message", "data": json.dumps(data)}
        await asyncio.sleep(0.4)

@app.get("/api/progress")
async def sse_progress(request: Request):
    return EventSourceResponse(progress_generator())

async def download_spotify(url, dl_id, fmt, quality):
    active_downloads[dl_id]["status"] = "downloading"
    active_downloads[dl_id]["title"] = "Buscando metadados no Spotify..."
    active_downloads[dl_id]["percent"] = 5
    active_downloads[dl_id]["status_text"] = "Preparando ambiente SpotDL..."

    # Verificar FFmpeg
    ffmpeg_info = check_ffmpeg()
    if not ffmpeg_info["installed"]:
        active_downloads[dl_id]["status"] = "error"
        active_downloads[dl_id]["error"] = "FFmpeg não encontrado! Clique em 'Instalar FFmpeg' no menu superior para corrigir."
        active_downloads[dl_id]["status_text"] = "Erro: FFmpeg ausente."
        return

    # Ajustar taxa de bits para spotdl
    bitrate = quality if quality.endswith("k") else f"{quality}k"
    
    output_pattern = os.path.join(config["download_folder"], "{artist} - {title}.{ext}")

    cmd = [
        sys.executable, "-m", "spotdl", url,
        "--output", output_pattern,
        "--bitrate", bitrate,
        "--format", fmt,
        "--threads", "4",
        "--max-retries", "3"
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    
    active_processes[dl_id] = process

    import re
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        decoded = line.decode('utf-8', errors='ignore').strip()
        print(f"[spotdl:{dl_id}]", decoded)

        # Checar se foi cancelado
        if active_downloads.get(dl_id, {}).get("status") == "cancelled":
            try:
                process.terminate()
            except Exception:
                pass
            return

        m = re.search(r'Found\s+(\d+)\s+songs', decoded, re.IGNORECASE)
        if m:
            total = int(m.group(1))
            active_downloads[dl_id]["total_songs"] = total
            active_downloads[dl_id]["title"] = f"Playlist Spotify ({total} músicas)"

        if "Downloaded" in decoded or "Converting" in decoded:
            active_downloads[dl_id]["current_song"] += 1
            curr = active_downloads[dl_id]["current_song"]
            tot = active_downloads[dl_id]["total_songs"]
            
            # Tentar extrair nome da música
            song_match = re.search(r'"([^"]+)"', decoded)
            if song_match:
                active_downloads[dl_id]["title"] = song_match.group(1)

            if tot > 1:
                pct = min(99, int((curr / tot) * 100))
                active_downloads[dl_id]["percent"] = pct
                active_downloads[dl_id]["status_text"] = f"Baixando música {curr} de {tot} ({pct}%)"
            else:
                active_downloads[dl_id]["percent"] = 85
                active_downloads[dl_id]["status_text"] = "Convertendo e aplicando tags ID3..."

        elif "FFmpegError" in decoded or "FFmpeg is not installed" in decoded:
            active_downloads[dl_id]["status"] = "error"
            active_downloads[dl_id]["error"] = "FFmpeg ausente ou erro de conversão. Clique em 'Instalar FFmpeg'."
            return

    await process.wait()

    if active_downloads.get(dl_id, {}).get("status") == "cancelled":
        return

    if process.returncode == 0:
        active_downloads[dl_id]["status"] = "finished"
        active_downloads[dl_id]["percent"] = 100
        active_downloads[dl_id]["status_text"] = "Download e conversão concluídos!"
    else:
        active_downloads[dl_id]["status"] = "error"
        active_downloads[dl_id]["error"] = "Erro ao baixar via SpotDL. Verifique a URL ou sua conexão."
        active_downloads[dl_id]["status_text"] = "Falha no download via Spotify."

def ytdlp_hook(dl_id):
    def hook(d):
        if active_downloads.get(dl_id, {}).get("status") == "cancelled":
            raise Exception("Download cancelado pelo usuário.")

        tot = d.get('info_dict', {}).get('playlist_count') or 1
        curr = d.get('info_dict', {}).get('playlist_index') or 1
        
        active_downloads[dl_id]["total_songs"] = tot
        active_downloads[dl_id]["current_song"] = curr

        if d['status'] == 'finished':
            if tot == 1 or curr == tot:
                active_downloads[dl_id]["percent"] = 98
                active_downloads[dl_id]["status_text"] = "Processando áudio com FFmpeg..."
            else:
                pct = int((curr / tot) * 100)
                active_downloads[dl_id]["percent"] = pct
                active_downloads[dl_id]["status_text"] = f"Música {curr} de {tot} concluída ({pct}%)"

            if 'filename' in d and tot == 1:
                filename = os.path.basename(d['filename'])
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
                    active_downloads[dl_id]["status_text"] = f"Música {curr} de {tot} - {song_p:.1f}%"
                else:
                    active_downloads[dl_id]["percent"] = song_p
                    speed = d.get('_speed_str', '')
                    eta = d.get('_eta_str', '')
                    status_info = f"Baixando... {song_p:.1f}%"
                    if speed:
                        status_info += f" ({speed.strip()})"
                    if eta:
                        status_info += f" - Restante: {eta.strip()}"
                    active_downloads[dl_id]["status_text"] = status_info
            except Exception:
                pass

            if 'filename' in d and tot == 1:
                filename = os.path.basename(d['filename'])
                active_downloads[dl_id]["title"] = filename
    return hook

async def download_ytdlp(url, dl_id, fmt, quality):
    active_downloads[dl_id]["status"] = "downloading"
    active_downloads[dl_id]["status_text"] = "Analisando URL..."

    # Verificar FFmpeg
    ffmpeg_info = check_ffmpeg()
    ffmpeg_exe = ffmpeg_info["path"]

    clean_quality = quality.replace("k", "")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(config["download_folder"], '%(title)s.%(ext)s'),
        'ffmpeg_location': ffmpeg_exe if ffmpeg_exe else None,
        'concurrent_fragment_downloads': 8,
        'buffersize': 1024 * 1024,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'retries': 5,
        'fragment_retries': 5,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': fmt,
            'preferredquality': clean_quality,
        }],
        'progress_hooks': [ytdlp_hook(dl_id)],
        'quiet': True,
        'no_warnings': True
    }

    def run_ydl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    try:
        loop = asyncio.get_running_loop()
        task = loop.run_in_executor(None, run_ydl)
        active_processes[dl_id] = task
        await task
        
        if active_downloads.get(dl_id, {}).get("status") != "cancelled":
            active_downloads[dl_id]["status"] = "finished"
            active_downloads[dl_id]["percent"] = 100
            active_downloads[dl_id]["status_text"] = "Download e conversão concluídos com sucesso!"
    except Exception as e:
        err_msg = str(e)
        print("yt-dlp error:", err_msg)
        
        if active_downloads.get(dl_id, {}).get("status") == "cancelled":
            return
            
        active_downloads[dl_id]["status"] = "error"
        
        # Mapeamento de diagnósticos e soluções claras
        if "ffprobe or ffmpeg not found" in err_msg.lower() or "ffmpeg is not installed" in err_msg.lower():
            active_downloads[dl_id]["error"] = "FFmpeg não foi encontrado! Clique no botão 'Instalar FFmpeg' no topo da tela para solucionar."
        elif "http error 404" in err_msg.lower() or "video unavailable" in err_msg.lower():
            active_downloads[dl_id]["error"] = "Música ou vídeo não encontrado (404). Verifique se o link está correto ou não foi removido."
        elif "sign in to confirm your age" in err_msg.lower() or "bot" in err_msg.lower():
            active_downloads[dl_id]["error"] = "Este vídeo exige confirmação de idade ou verificação pelo YouTube."
        elif "unable to extract" in err_msg.lower() or "unsupported url" in err_msg.lower():
            active_downloads[dl_id]["error"] = "URL não suportada ou formato alterado. Tente atualizar o yt-dlp no menu superior."
        else:
            active_downloads[dl_id]["error"] = f"Falha no download: {err_msg}"
            
        active_downloads[dl_id]["status_text"] = "Erro no processo de download."

# Serve os arquivos estáticos do frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

