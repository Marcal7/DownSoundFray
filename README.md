# 🎧 Downfy (DownSoundFray)

Aplicativo moderno e rápido para download e gerenciamento de faixas musicais do **Spotify**, **YouTube** e **SoundCloud** com conversão automática de áudio em alta qualidade.

---

### 🚀 Para Usuários (Download Rápido & Sem Instalação)

Não precisa instalar Python, bibliotecas nem configurar nada no Windows:

[![Baixar Versão Portátil](https://img.shields.io/badge/⬇️%20Baixar%20Downfy%20Portátil%20(Windows)-00C853?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/Marcal7/DownSoundFray/releases/latest)

#### Como Usar:
1. Acesse o botão acima ou a aba de [Releases](https://github.com/Marcal7/DownSoundFray/releases/latest) e baixe o arquivo `Downfy_Portatil.zip`.
2. Extraia o arquivo `.zip` no seu computador.
3. Dê dois cliques em **`Downfy.exe`** (ou use o atalho para a Área de Trabalho).
4. O aplicativo abrirá automaticamente no seu navegador em `http://127.0.0.1:8000`.

---

## ✨ Recursos

- **Spotify**: Download de músicas individuais, álbuns e playlists completas via `spotdl`.
- **YouTube & SoundCloud**: Extração rápida de áudio com suporte a múltiplas qualidades via `yt-dlp`.
- **Motor Integrado**: Já acompanha FFmpeg e decodificador Deno (zero configuração de variáveis de ambiente).
- **Interface Intuitiva**: Acompanhamento de progresso em tempo real, status detalhado e seletor nativo de pasta de destino.
- **Conversão Automática**: Tags ID3 completas, capa em alta resolução e suporte a MP3 (320kbps), FLAC, WAV, etc.

---

## 🛠️ Para Desenvolvedores (Executar via Código Fonte)

Caso queira modificar ou rodar o projeto diretamente em Python:

### Pré-requisitos
- Python 3.9+
- [FFmpeg](https://ffmpeg.org/download.html) (adicionado ao PATH do sistema ou instalado via `spotdl --download-ffmpeg`)

### Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/Marcal7/DownSoundFray.git
   cd DownSoundFray
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Inicie o servidor:
   ```bash
   iniciar.bat
   ```
   *Ou execute manualmente via terminal:*
   ```bash
   python main.py
   ```

4. Abra `http://127.0.0.1:8000` no navegador.

### Gerar Novo Executável Portátil

Para gerar uma nova versão compilada autônoma:
```bash
python build_release.py
```
O script compilará os binários e gerará o pacote `Downfy_Portatil.zip` pronto para distribuição.

---

## 📄 Licença
Distribuído sob a licença MIT. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.
