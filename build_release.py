import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path

def main():
    root_dir = Path(__file__).resolve().parent
    output_dir = root_dir / "Downfy_Portatil"
    dist_dir = root_dir / "dist" / "Downfy"

    print("=" * 65)
    print("   [+] INICIANDO COMPILACAO DO DOWNFY PORTATIL")
    print("=" * 65)

    # Encerrar instâncias anteriores do Downfy para não travar os arquivos
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Process -Name 'Downfy' -ErrorAction SilentlyContinue | Stop-Process -Force"], capture_output=True)
    except Exception:
        pass

    # 1. Executar PyInstaller
    spec_path = root_dir / "Downfy.spec"
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", str(spec_path)]
    print("[1/5] Compilando executavel com PyInstaller...")
    res = subprocess.run(cmd, cwd=str(root_dir))
    if res.returncode != 0:
        print("[!] Erro ao compilar com PyInstaller!")
        sys.exit(res.returncode)

    # 2. Criar ou limpar a pasta Downfy_Portatil
    print(f"[2/5] Preparando pasta de distribuicao: {output_dir.name}...")
    if output_dir.exists():
        try:
            shutil.rmtree(output_dir)
        except Exception as e:
            print(f"Aviso ao limpar pasta: {e}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 3. Copiar arquivos compilados do dist/Downfy
    print("[3/5] Copiando binarios compilados...")
    if dist_dir.exists():
        for item in dist_dir.iterdir():
            dest = output_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
        # Garantir pasta frontend também na raiz de Downfy_Portatil
        frontend_src = root_dir / "frontend"
        if frontend_src.exists():
            shutil.copytree(frontend_src, output_dir / "frontend", dirs_exist_ok=True)
    else:
        print(f"[!] Diretorio {dist_dir} nao encontrado!")
        sys.exit(1)

    # 4. Incluir FFmpeg e Deno diretamente na pasta
    print("[4/5] Anexando FFmpeg e Deno para os DJs (zero configuracao)...")
    spotdl_dir = Path(os.path.expanduser("~/.spotdl"))
    
    # FFmpeg
    ffmpeg_src = spotdl_dir / "ffmpeg.exe"
    if not ffmpeg_src.exists():
        found = shutil.which("ffmpeg")
        if found:
            ffmpeg_src = Path(found)
    
    if ffmpeg_src.exists():
        shutil.copy2(ffmpeg_src, output_dir / "ffmpeg.exe")
        print(f"   -> FFmpeg incluido com sucesso: {output_dir / 'ffmpeg.exe'}")
    else:
        print("   [!] ffmpeg.exe nao foi localizado em ~/.spotdl nem no PATH.")

    # Deno
    deno_src = spotdl_dir / "deno.exe"
    if not deno_src.exists():
        found = shutil.which("deno")
        if found:
            deno_src = Path(found)
    
    if deno_src.exists():
        shutil.copy2(deno_src, output_dir / "deno.exe")
        print(f"   -> Deno incluido com sucesso: {output_dir / 'deno.exe'}")
    else:
        print("   [!] deno.exe nao foi localizado.")

    # 5. Criar LEIA-ME e script de atalho
    readme_content = """=====================================================
            DOWNFY - GUIA RAPIDO PARA DJS
=====================================================

COMO USAR:
1. De dois cliques no arquivo "Downfy.exe".
2. O aplicativo iniciara e abrira seu navegador automaticamente
   no endereco: http://127.0.0.1:8000
3. Cole o link do Spotify, YouTube ou SoundCloud e baixe suas faixas!

VANTAGENS DESTA VERSAO:
- Totalmente portatil: NAO precisa instalar Python nem configurar variaveis.
- Ja inclui o conversor FFmpeg (audio em 320kbps, WAV, FLAC, MP3 com tags ID3).
- Nao precisa de privilegios de administrador.
- Seus downloads vao direto para a pasta 'Musicas' do seu Windows.

DICA:
Para criar um atalho na Area de Trabalho com um clique,
de dois cliques no arquivo "Criar Atalho na Area de Trabalho.bat".

Para fechar o Downfy, basta fechar a janela do terminal.
=====================================================
"""
    (output_dir / "LEIA-ME.txt").write_text(readme_content, encoding="utf-8")

    shortcut_bat = """@echo off
set SCRIPT="%TEMP%\\CreateShortcut.vbs"
set TARGET="%~dp0Downfy.exe"
set SHORTCUT="%USERPROFILE%\\Desktop\\Downfy.lnk"
echo Set oWS = WScript.CreateObject("WScript.Shell") > %SCRIPT%
echo sLinkFile = %SHORTCUT% >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = %TARGET% >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink.Description = "Downfy - Downloader de Musicas" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%
cscript /nologo %SCRIPT%
del %SCRIPT%
echo.
echo ====================================================
echo   Atalho do Downfy criado com sucesso no seu Desktop!
echo ====================================================
echo.
pause
"""
    (output_dir / "Criar Atalho na Area de Trabalho.bat").write_text(shortcut_bat, encoding="utf-8")

    # 6. Gerar arquivo ZIP para fácil envio
    zip_dest = root_dir / "Downfy_Portatil.zip"
    print(f"[5/5] Compactando em {zip_dest.name} para envio a amigos...")
    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in output_dir.rglob("*"):
            rel_path = file.relative_to(output_dir)
            zipf.write(file, arcname=str(Path("Downfy_Portatil") / rel_path))

    print()
    print("=" * 65)
    print("   [+] COMPILACAO CONCLUIDA COM SUCESSO!")
    print("=" * 65)
    print(f"Pasta pronta: {output_dir}")
    print(f"Arquivo ZIP pronto para envio: {zip_dest}")
    print("=" * 65)

if __name__ == "__main__":
    main()
