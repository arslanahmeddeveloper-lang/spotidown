document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('spotify-url');
    const fetchBtn = document.getElementById('fetch-btn');
    const downloadBtn = document.getElementById('download-btn');
    const saveBtn = document.getElementById('save-btn');
    const newDownloadBtn = document.getElementById('new-download-btn');

    const trackCard = document.getElementById('track-card');
    const progressSection = document.getElementById('progress-section');
    const downloadComplete = document.getElementById('download-complete');
    const bgBlur = document.getElementById('track-bg-blur');
    const toastContainer = document.getElementById('toast-container');

    let currentDownloadId = null;
    let currentTrackUrl = null;

    function showToast(message, type = 'error') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        let icon = '';
        if (type === 'error') {
            icon = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
        } else {
            icon = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>';
            toast.style.background = 'rgba(30, 215, 96, 0.15)';
            toast.style.borderColor = 'rgba(30, 215, 96, 0.3)';
            toast.style.color = '#1ed760';
            toast.style.boxShadow = '0 4px 15px rgba(30, 215, 96, 0.2)';
        }

        toast.innerHTML = `${icon}<span>${message}</span>`;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => {
                if (toast.parentElement) toast.remove();
            }, 400);
        }, 4000);
    }

    function setButtonLoading(btn, loading) {
        if (loading) {
            btn.classList.add('loading');
            btn.disabled = true;
        } else {
            btn.classList.remove('loading');
            btn.disabled = false;
        }
    }

    async function fetchTrack() {
        const url = urlInput.value.trim();

        if (!url) {
            showToast('Please paste a valid Spotify link');
            return;
        }

        setButtonLoading(fetchBtn, true);
        trackCard.classList.add('hidden');
        progressSection.classList.add('hidden');
        downloadComplete.classList.add('hidden');
        bgBlur.style.backgroundImage = 'none';

        try {
            const response = await fetch('/api/fetch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const data = await response.json();

            if (!response.ok) {
                showToast(data.error || 'Failed to fetch track information');
                return;
            }

            currentTrackUrl = url;
            displayTrack(data.track);

        } catch (error) {
            showToast('Network error. Check your connection.');
        } finally {
            setButtonLoading(fetchBtn, false);
        }
    }

    function displayTrack(track) {
        const artUrl = track.album_art || '';
        document.getElementById('album-art').src = artUrl;

        // update background blur
        if (artUrl) {
            bgBlur.style.backgroundImage = `url(${artUrl})`;
        }

        document.getElementById('track-name').textContent = track.name;
        document.getElementById('track-artist').textContent = track.artist;
        document.getElementById('track-album').querySelector('.tag-text').textContent = track.album;
        document.getElementById('track-duration').querySelector('.tag-text').textContent = track.duration;

        trackCard.classList.remove('hidden');

        // Handle scrolling text if it's too long
        const nameEl = document.getElementById('track-name');
        if (nameEl.scrollWidth > nameEl.clientWidth) {
            nameEl.style.animation = 'marquee 10s linear infinite';
            // Not a real CSS variable yet, but implies custom marquee if implemented
        } else {
            nameEl.style.animation = 'none';
        }
    }

    async function startDownload() {
        if (!currentTrackUrl) return;

        setButtonLoading(downloadBtn, true);
        progressSection.classList.remove('hidden');
        downloadComplete.classList.add('hidden');

        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: currentTrackUrl })
            });

            const data = await response.json();

            if (!response.ok) {
                showToast(data.error || 'Download failed to start');
                progressSection.classList.add('hidden');
                setButtonLoading(downloadBtn, false);
                return;
            }

            currentDownloadId = data.download_id;
            pollStatus();

        } catch (error) {
            showToast('Network error while starting download');
            progressSection.classList.add('hidden');
            setButtonLoading(downloadBtn, false);
        }
    }

    async function pollStatus() {
        if (!currentDownloadId) return;

        try {
            const response = await fetch(`/api/status/${currentDownloadId}`);
            const data = await response.json();

            updateProgress(data);

            if (data.status === 'complete') {
                onDownloadComplete();
            } else if (data.status === 'error') {
                showToast(data.error || 'An error occurred during download');
                progressSection.classList.add('hidden');
                setButtonLoading(downloadBtn, false);
            } else {
                setTimeout(pollStatus, 600); // Poll slightly slower to reduce UI jitter
            }

        } catch (error) {
            showToast('Connection lost during status check');
            progressSection.classList.add('hidden');
            setButtonLoading(downloadBtn, false);
        }
    }

    function updateProgress(data) {
        const statusEl = document.getElementById('progress-status');
        const percentEl = document.getElementById('progress-percent');
        const fillEl = document.getElementById('progress-fill');

        statusEl.textContent = data.message || 'Processing...';
        const pct = Math.min(Math.max(data.progress || 0, 0), 100);
        percentEl.textContent = `${pct}%`;
        fillEl.style.width = `${pct}%`;
    }

    function onDownloadComplete() {
        trackCard.classList.add('hidden');
        progressSection.classList.add('hidden');
        downloadComplete.classList.remove('hidden');
        setButtonLoading(downloadBtn, false);
        showToast('Download Ready!', 'success');
    }

    function saveFile() {
        if (!currentDownloadId) return;
        window.location.href = `/api/file/${currentDownloadId}`;
    }

    function resetForm() {
        urlInput.value = '';
        currentDownloadId = null;
        currentTrackUrl = null;

        trackCard.classList.add('hidden');
        progressSection.classList.add('hidden');
        downloadComplete.classList.add('hidden');
        bgBlur.style.backgroundImage = 'none';

        urlInput.parentElement.classList.remove('active');
        urlInput.focus();
    }

    // UI Interactions
    urlInput.addEventListener('focus', () => {
        urlInput.parentElement.classList.add('active');
    });

    urlInput.addEventListener('blur', () => {
        if (!urlInput.value.trim()) {
            urlInput.parentElement.classList.remove('active');
        }
    });

    fetchBtn.addEventListener('click', fetchTrack);
    downloadBtn.addEventListener('click', startDownload);
    saveBtn.addEventListener('click', saveFile);
    newDownloadBtn.addEventListener('click', resetForm);

    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            fetchTrack();
        }
    });
});

