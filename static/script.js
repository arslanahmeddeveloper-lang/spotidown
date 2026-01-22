document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('spotify-url');
    const fetchBtn = document.getElementById('fetch-btn');
    const downloadBtn = document.getElementById('download-btn');
    const saveBtn = document.getElementById('save-btn');
    const newDownloadBtn = document.getElementById('new-download-btn');
    
    const errorMessage = document.getElementById('error-message');
    const trackCard = document.getElementById('track-card');
    const progressSection = document.getElementById('progress-section');
    const downloadComplete = document.getElementById('download-complete');
    
    let currentDownloadId = null;
    let currentTrackUrl = null;
    
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
        trackCard.classList.add('hidden');
        progressSection.classList.add('hidden');
        downloadComplete.classList.add('hidden');
    }
    
    function hideError() {
        errorMessage.classList.add('hidden');
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
            showError('Please enter a Spotify track URL');
            return;
        }
        
        hideError();
        setButtonLoading(fetchBtn, true);
        trackCard.classList.add('hidden');
        progressSection.classList.add('hidden');
        downloadComplete.classList.add('hidden');
        
        try {
            const response = await fetch('/api/fetch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                showError(data.error || 'Failed to fetch track');
                return;
            }
            
            currentTrackUrl = url;
            displayTrack(data.track);
            
        } catch (error) {
            showError('Network error. Please try again.');
        } finally {
            setButtonLoading(fetchBtn, false);
        }
    }
    
    function displayTrack(track) {
        document.getElementById('album-art').src = track.album_art || '';
        document.getElementById('track-name').textContent = track.name;
        document.getElementById('track-artist').textContent = track.artist;
        document.getElementById('track-album').querySelector('span').textContent = track.album;
        document.getElementById('track-duration').querySelector('span').textContent = track.duration;
        
        trackCard.classList.remove('hidden');
    }
    
    async function startDownload() {
        if (!currentTrackUrl) return;
        
        hideError();
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
                showError(data.error || 'Failed to start download');
                progressSection.classList.add('hidden');
                setButtonLoading(downloadBtn, false);
                return;
            }
            
            currentDownloadId = data.download_id;
            pollStatus();
            
        } catch (error) {
            showError('Network error. Please try again.');
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
                showError(data.error || 'Download failed');
                progressSection.classList.add('hidden');
                setButtonLoading(downloadBtn, false);
            } else {
                setTimeout(pollStatus, 500);
            }
            
        } catch (error) {
            showError('Connection lost. Please try again.');
            progressSection.classList.add('hidden');
            setButtonLoading(downloadBtn, false);
        }
    }
    
    function updateProgress(data) {
        const statusEl = document.getElementById('progress-status');
        const percentEl = document.getElementById('progress-percent');
        const fillEl = document.getElementById('progress-fill');
        
        statusEl.textContent = data.message || 'Processing...';
        percentEl.textContent = `${data.progress || 0}%`;
        fillEl.style.width = `${data.progress || 0}%`;
    }
    
    function onDownloadComplete() {
        trackCard.classList.add('hidden');
        progressSection.classList.add('hidden');
        downloadComplete.classList.remove('hidden');
        setButtonLoading(downloadBtn, false);
    }
    
    function saveFile() {
        if (!currentDownloadId) return;
        window.location.href = `/api/file/${currentDownloadId}`;
    }
    
    function resetForm() {
        urlInput.value = '';
        currentDownloadId = null;
        currentTrackUrl = null;
        
        hideError();
        trackCard.classList.add('hidden');
        progressSection.classList.add('hidden');
        downloadComplete.classList.add('hidden');
        
        urlInput.focus();
    }
    
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
