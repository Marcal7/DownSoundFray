const API_BASE = window.location.origin;

document.addEventListener('DOMContentLoaded', () => {
    // Elementos DOM
    const urlInput = document.getElementById('urlInput');
    const downloadBtn = document.getElementById('downloadBtn');
    const formatSelect = document.getElementById('formatSelect');
    const qualitySelect = document.getElementById('qualitySelect');
    
    const selectFolderBtn = document.getElementById('selectFolderBtn');
    const editFolderBtn = document.getElementById('editFolderBtn');
    const openFolderBtn = document.getElementById('openFolderBtn');
    const openFolderHeaderBtn = document.getElementById('openFolderHeaderBtn');
    const currentFolderSpan = document.getElementById('currentFolder');
    
    const ffmpegStatus = document.getElementById('ffmpegStatus');
    const ytdlpStatus = document.getElementById('ytdlpStatus');
    const installFfmpegBtn = document.getElementById('installFfmpegBtn');
    const updateYtdlpBtn = document.getElementById('updateYtdlpBtn');
    
    const downloadsList = document.getElementById('downloadsList');
    const emptyState = document.getElementById('emptyState');
    const downloadCount = document.getElementById('downloadCount');
    const clearFinishedBtn = document.getElementById('clearFinishedBtn');
    
    // Modal Elementos
    const folderModal = document.getElementById('folderModal');
    const manualFolderPath = document.getElementById('manualFolderPath');
    const cancelFolderModalBtn = document.getElementById('cancelFolderModalBtn');
    const saveFolderModalBtn = document.getElementById('saveFolderModalBtn');
    
    const toastContainer = document.getElementById('toastContainer');

    let activeDownloads = {};

    // Sistema de Notificações Toast
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const iconClass = type === 'success' ? 'fa-circle-check' :
                          type === 'error' ? 'fa-circle-exclamation' :
                          type === 'warning' ? 'fa-triangle-exclamation' : 'fa-circle-info';
                          
        toast.innerHTML = `<i class="fa-solid ${iconClass}"></i> <span>${message}</span>`;
        toastContainer.appendChild(toast);

        setTimeout(() => toast.classList.add('show'), 10);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // Carregar Estado e Saúde do Sistema
    async function fetchSystemHealth() {
        try {
            const res = await fetch(`${API_BASE}/api/health`);
            const data = await res.json();

            // Atualizar status do FFmpeg
            if (data.ffmpeg.installed) {
                ffmpegStatus.className = 'status-pill success';
                ffmpegStatus.innerHTML = '<i class="fa-solid fa-check"></i> FFmpeg Pronto';
                installFfmpegBtn.style.display = 'none';
            } else {
                ffmpegStatus.className = 'status-pill danger';
                ffmpegStatus.innerHTML = '<i class="fa-solid fa-xmark"></i> FFmpeg Ausente';
                installFfmpegBtn.style.display = 'inline-flex';
            }

            // Atualizar status do yt-dlp
            ytdlpStatus.innerHTML = `<i class="fa-solid fa-code-branch"></i> yt-dlp v${data.ytdlp_version}`;

            // Pasta de Download
            currentFolderSpan.textContent = data.download_folder;
            currentFolderSpan.title = data.download_folder;

            if (!data.folder_writable) {
                showToast('A pasta selecionada não tem permissão de escrita ou é inválida.', 'warning');
            }
        } catch (err) {
            console.error('Erro ao carregar diagnóstico do servidor:', err);
            ffmpegStatus.className = 'status-pill danger';
            ffmpegStatus.innerHTML = '<i class="fa-solid fa-plug-circle-xmark"></i> Servidor Desconectado';
            currentFolderSpan.textContent = 'Erro ao conectar ao servidor local';
        }
    }

    fetchSystemHealth();

    // Seleção de Pasta via Diálogo Nativo
    selectFolderBtn.addEventListener('click', async () => {
        selectFolderBtn.disabled = true;
        const originalText = selectFolderBtn.innerHTML;
        selectFolderBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Abrindo...';

        try {
            const res = await fetch(`${API_BASE}/api/select-folder`, { method: 'POST' });
            const data = await res.json();

            if (data.status === 'success') {
                currentFolderSpan.textContent = data.folder;
                currentFolderSpan.title = data.folder;
                showToast('Pasta de destino atualizada!', 'success');
            } else if (data.status === 'error') {
                showToast(data.message, 'error');
            }
        } catch (err) {
            console.error('Erro ao selecionar pasta:', err);
            showToast('Erro ao abrir seletor de pasta.', 'error');
        } finally {
            selectFolderBtn.disabled = false;
            selectFolderBtn.innerHTML = originalText;
        }
    });

    // Edição Manual de Pasta (Modal)
    editFolderBtn.addEventListener('click', () => {
        manualFolderPath.value = currentFolderSpan.textContent !== 'Selecionando pasta padrão...' ? currentFolderSpan.textContent : '';
        folderModal.classList.add('active');
    });

    cancelFolderModalBtn.addEventListener('click', () => {
        folderModal.classList.remove('active');
    });

    saveFolderModalBtn.addEventListener('click', async () => {
        const newPath = manualFolderPath.value.trim();
        if (!newPath) return;

        try {
            const res = await fetch(`${API_BASE}/api/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ download_folder: newPath })
            });
            const data = await res.json();

            if (res.ok) {
                currentFolderSpan.textContent = data.download_folder;
                currentFolderSpan.title = data.download_folder;
                folderModal.classList.remove('active');
                showToast('Pasta alterada com sucesso!', 'success');
            } else {
                showToast(data.detail || 'Erro ao alterar pasta.', 'error');
            }
        } catch (err) {
            showToast('Erro de comunicação ao salvar pasta.', 'error');
        }
    });

    // Abrir Pasta no Explorer
    const handleOpenFolder = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/open-folder`, { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success') {
                showToast('Pasta aberta no Explorer!', 'info');
            } else {
                showToast(data.message, 'error');
            }
        } catch (err) {
            showToast('Erro ao tentar abrir a pasta.', 'error');
        }
    };

    openFolderBtn.addEventListener('click', handleOpenFolder);
    openFolderHeaderBtn.addEventListener('click', handleOpenFolder);

    // Atualizar yt-dlp
    updateYtdlpBtn.addEventListener('click', async () => {
        updateYtdlpBtn.disabled = true;
        updateYtdlpBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Atualizando...';
        showToast('Iniciando atualização do yt-dlp...', 'info');

        try {
            const res = await fetch(`${API_BASE}/api/update-ytdlp`, { method: 'POST' });
            const data = await res.json();

            if (data.status === 'success') {
                showToast('yt-dlp atualizado com sucesso!', 'success');
                fetchSystemHealth();
            } else {
                showToast('Falha ao atualizar yt-dlp: ' + data.message, 'error');
            }
        } catch (err) {
            showToast('Erro ao atualizar yt-dlp.', 'error');
        } finally {
            updateYtdlpBtn.disabled = false;
            updateYtdlpBtn.innerHTML = '<i class="fa-solid fa-rotate"></i> Atualizar yt-dlp';
        }
    });

    // Instalar FFmpeg
    installFfmpegBtn.addEventListener('click', async () => {
        installFfmpegBtn.disabled = true;
        installFfmpegBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Baixando FFmpeg...';
        showToast('Baixando FFmpeg (isso pode levar alguns segundos)...', 'info');

        try {
            const res = await fetch(`${API_BASE}/api/install-ffmpeg`, { method: 'POST' });
            const data = await res.json();

            if (data.status === 'success') {
                showToast('FFmpeg instalado com sucesso!', 'success');
                fetchSystemHealth();
            } else {
                showToast('Erro na instalação: ' + data.message, 'error');
            }
        } catch (err) {
            showToast('Erro ao comunicar com o servidor.', 'error');
        } finally {
            installFfmpegBtn.disabled = false;
            installFfmpegBtn.innerHTML = '<i class="fa-solid fa-download"></i> Instalar FFmpeg';
        }
    });

    // Iniciar Download
    downloadBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) {
            showToast('Por favor, cole uma URL válida antes de baixar.', 'warning');
            return;
        }

        const format = formatSelect.value;
        const quality = qualitySelect.value;

        downloadBtn.style.transform = 'scale(0.95)';
        setTimeout(() => downloadBtn.style.transform = '', 150);

        try {
            const res = await fetch(`${API_BASE}/api/download`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, format, quality })
            });

            const data = await res.json();

            if (res.ok && data.status === 'success') {
                urlInput.value = '';
                addDownloadItem(data.download_id, url, data.platform, format, quality);
                showToast('Download adicionado à fila!', 'success');
            } else {
                showToast(data.detail || data.message || 'Erro ao iniciar download.', 'error');
            }
        } catch (err) {
            console.error('Erro ao solicitar download:', err);
            showToast('Falha na requisição. Verifique se o servidor está rodando.', 'error');
        }
    });

    // Limpar Concluídos
    clearFinishedBtn.addEventListener('click', async () => {
        try {
            const res = await fetch(`${API_BASE}/api/clear-finished`, { method: 'POST' });
            const data = await res.json();
            
            const finishedElements = document.querySelectorAll('.status-completed, .status-error, .status-cancelled');
            finishedElements.forEach(el => el.remove());
            
            if (data.cleared > 0) {
                showToast(`${data.cleared} download(s) resolvidos removidos da lista.`, 'info');
            }
            updateBadge();
        } catch (err) {
            showToast('Erro ao limpar downloads.', 'error');
        }
    });

    // EventSource SSE para Progresso dos Downloads
    const eventSource = new EventSource(`${API_BASE}/api/progress`);
    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            updateDownloadProgress(data.id, data);
        } catch (e) {
            console.error('Erro ao ler SSE:', e);
        }
    };

    function addDownloadItem(id, url, platform, format, quality) {
        if (emptyState) emptyState.style.display = 'none';

        const iconClass = platform === 'spotify' ? 'fa-spotify platform-spotify' :
            platform === 'soundcloud' ? 'fa-soundcloud platform-soundcloud' : 'fa-youtube platform-youtube';

        const formatLabel = format.toUpperCase();

        const itemHTML = `
            <div class="download-item" id="dl-${id}">
                <div class="item-header">
                    <div class="item-info">
                        <div class="platform-icon ${platform}">
                            <i class="fa-brands ${iconClass}"></i>
                        </div>
                        <div class="item-details">
                            <div class="item-title-row">
                                <span class="item-title" id="title-${id}">Iniciando...</span>
                                <span class="format-tag">${formatLabel} • ${quality}</span>
                            </div>
                            <span class="item-status-text" id="status-${id}">Aguardando na fila...</span>
                        </div>
                    </div>
                    <div class="item-actions" id="actions-${id}">
                        <button class="action-btn cancel-btn" title="Cancelar download" onclick="cancelDownload('${id}')">
                            <i class="fa-solid fa-xmark"></i>
                        </button>
                    </div>
                </div>
                <div class="progress-container">
                    <div class="progress-bar" id="bar-${id}"></div>
                </div>
            </div>
        `;

        downloadsList.insertAdjacentHTML('afterbegin', itemHTML);
        activeDownloads[id] = { url, platform, format, quality, status: 'starting' };
        updateBadge();
    }

    function updateDownloadProgress(id, data) {
        let item = document.getElementById(`dl-${id}`);
        
        // Se o item não existir na DOM mas existir nos dados ativos do servidor, adicione-o
        if (!item && data.status !== 'finished') {
            addDownloadItem(id, data.url, data.platform, data.format || 'mp3', data.quality || '320k');
            item = document.getElementById(`dl-${id}`);
        }

        if (!item) return;

        const titleSpan = document.getElementById(`title-${id}`);
        const statusSpan = document.getElementById(`status-${id}`);
        const progressBar = document.getElementById(`bar-${id}`);
        const actionsDiv = document.getElementById(`actions-${id}`);

        if (data.title) {
            titleSpan.textContent = data.title;
        }

        if (data.status === 'downloading') {
            statusSpan.textContent = data.status_text || `Baixando... ${data.percent}%`;
            progressBar.style.width = `${Math.min(100, Math.max(0, data.percent))}%`;
            item.className = 'download-item status-downloading';
        } else if (data.status === 'finished') {
            statusSpan.textContent = data.status_text || 'Concluído com sucesso!';
            progressBar.style.width = '100%';
            item.className = 'download-item status-completed';
            
            actionsDiv.innerHTML = `
                <button class="action-btn success-btn" title="Abrir pasta de downloads" onclick="handleOpenFolderGlobal()">
                    <i class="fa-solid fa-folder-open"></i>
                </button>
            `;
        } else if (data.status === 'error') {
            statusSpan.textContent = data.error || data.status_text || 'Falha no download';
            progressBar.style.width = '100%';
            item.className = 'download-item status-error';

            actionsDiv.innerHTML = `
                <button class="action-btn retry-btn" title="Tentar Novamente" onclick="retryDownload('${id}')">
                    <i class="fa-solid fa-rotate-right"></i> Tentar Novamente
                </button>
            `;
        } else if (data.status === 'cancelled') {
            statusSpan.textContent = 'Download cancelado.';
            progressBar.style.width = '0%';
            item.className = 'download-item status-cancelled';

            actionsDiv.innerHTML = `
                <button class="action-btn retry-btn" title="Reiniciar Download" onclick="retryDownload('${id}')">
                    <i class="fa-solid fa-rotate-right"></i> Reiniciar
                </button>
            `;
        }

        updateBadge();
    }

    function updateBadge() {
        const totalItems = document.querySelectorAll('.download-item').length;
        const finishedItems = document.querySelectorAll('.status-completed').length;
        const errorItems = document.querySelectorAll('.status-error, .status-cancelled').length;

        const activeCount = totalItems - finishedItems - errorItems;
        downloadCount.textContent = activeCount;

        if (totalItems === 0 && emptyState) {
            emptyState.style.display = 'flex';
        } else if (emptyState) {
            emptyState.style.display = 'none';
        }
    }

    // Funções globais para onclick em elementos HTML dinâmicos
    window.cancelDownload = async (id) => {
        try {
            const res = await fetch(`${API_BASE}/api/cancel/${id}`, { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success') {
                showToast('Download cancelado.', 'info');
            }
        } catch (e) {
            showToast('Erro ao cancelar download.', 'error');
        }
    };

    window.retryDownload = async (id) => {
        try {
            const res = await fetch(`${API_BASE}/api/retry/${id}`, { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success') {
                showToast('Reiniciando download...', 'info');
            } else {
                showToast(data.message || 'Erro ao reiniciar.', 'error');
            }
        } catch (e) {
            showToast('Erro ao reiniciar download.', 'error');
        }
    };

    window.handleOpenFolderGlobal = handleOpenFolder;
});

