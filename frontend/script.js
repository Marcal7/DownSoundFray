const API_BASE = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('urlInput');
    const downloadBtn = document.getElementById('downloadBtn');
    const selectFolderBtn = document.getElementById('selectFolderBtn');
    const currentFolderSpan = document.getElementById('currentFolder');
    const downloadsList = document.getElementById('downloadsList');
    const emptyState = document.getElementById('emptyState');
    const downloadCount = document.getElementById('downloadCount');

    let activeDownloads = {};

    // Load initial config
    fetch(`${API_BASE}/api/config`)
        .then(res => res.json())
        .then(data => {
            currentFolderSpan.textContent = data.download_folder;
        })
        .catch(err => {
            console.error('Failed to load config', err);
            currentFolderSpan.textContent = 'Erro ao conectar ao servidor local';
        });

    // Select Folder
    selectFolderBtn.addEventListener('click', async () => {
        try {
            const res = await fetch(`${API_BASE}/api/select-folder`, { method: 'POST' });
            const data = await res.json();
            if (data.folder) {
                currentFolderSpan.textContent = data.folder;
            }
        } catch (err) {
            console.error('Error selecting folder', err);
        }
    });

    // Start Download
    downloadBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) return;

        // Add a subtle click animation to the button
        downloadBtn.style.transform = 'scale(0.95)';
        setTimeout(() => downloadBtn.style.transform = '', 150);

        try {
            const res = await fetch(`${API_BASE}/api/download`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            const data = await res.json();

            if (data.status === 'success') {
                urlInput.value = ''; // clear input
                addDownloadItem(data.download_id, url, data.platform);
            } else {
                alert('Erro: ' + data.message);
            }
        } catch (err) {
            console.error('Error starting download', err);
            alert('Erro ao iniciar o download. O servidor local está rodando?');
        }
    });

    // Handle SSE for Progress
    const eventSource = new EventSource(`${API_BASE}/api/progress`);
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateDownloadProgress(data.id, data);
    };

    function addDownloadItem(id, url, platform) {
        if (Object.keys(activeDownloads).length === 0) {
            emptyState.style.display = 'none';
        }

        const iconClass = platform === 'spotify' ? 'fa-spotify platform-spotify' :
            platform === 'soundcloud' ? 'fa-soundcloud platform-soundcloud' : 'fa-music';

        const itemHTML = `
            <div class="download-item" id="dl-${id}">
                <div class="item-header">
                    <div class="item-info">
                        <div class="platform-icon ${platform === 'spotify' ? 'platform-spotify' : 'platform-soundcloud'}">
                            <i class="fa-brands ${iconClass}"></i>
                        </div>
                        <div class="item-details">
                            <span class="item-title" id="title-${id}">Iniciando...</span>
                            <span class="item-status-text" id="status-${id}">Preparando ambiente...</span>
                        </div>
                    </div>
                </div>
                <div class="progress-container">
                    <div class="progress-bar" id="bar-${id}"></div>
                </div>
            </div>
        `;

        downloadsList.insertAdjacentHTML('afterbegin', itemHTML);
        activeDownloads[id] = { url, platform, status: 'starting' };
        updateBadge();
    }

    function updateDownloadProgress(id, data) {
        const item = document.getElementById(`dl-${id}`);
        if (!item) return;

        const titleSpan = document.getElementById(`title-${id}`);
        const statusSpan = document.getElementById(`status-${id}`);
        const progressBar = document.getElementById(`bar-${id}`);

        if (data.title) {
            titleSpan.textContent = data.title;
        }

        if (data.status === 'downloading') {
            const txt = data.status_text ? `${data.status_text} - ${data.percent}%` : `Baixando... ${data.percent}%`;
            statusSpan.textContent = txt;
            progressBar.style.width = `${data.percent}%`;
        } else if (data.status === 'finished') {
            statusSpan.textContent = 'Concluído com sucesso!';
            progressBar.style.width = '100%';
            item.classList.add('status-completed');
            item.classList.remove('status-error');
            delete activeDownloads[id];
        } else if (data.status === 'error') {
            statusSpan.textContent = 'Erro: ' + (data.error || 'Falha no download');
            progressBar.style.width = '100%';
            item.classList.add('status-error');
            item.classList.remove('status-completed');
            delete activeDownloads[id];
        }

        updateBadge();
    }

    function updateBadge() {
        // Count only active elements visually from DOM to ensure accuracy
        const totalItems = document.querySelectorAll('.download-item').length;
        const finishedItems = document.querySelectorAll('.status-completed').length;
        const errorItems = document.querySelectorAll('.status-error').length;

        const activeCount = totalItems - finishedItems - errorItems;
        downloadCount.textContent = activeCount;
    }
});
