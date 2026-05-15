/* Mijnstroom — modern progressive enhancements.
 *
 * This script is loaded as <script type="module">; legacy browsers
 * (Nokia, IE) will silently ignore it. Modern browsers get:
 *   1. Sidebar toggle on mobile.
 *   2. Material ripple effect on buttons / cards.
 *   3. Bottom audio player with full GPM 2014 controls.
 *   4. Dynamic piece management on YouTube prepare page.
 *   5. Smooth page-fade transitions on intra-app navigation.
 *   6. Confirm-dialog interception for delete links.
 */

// ---------- helpers ----------
const $  = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

// ---------- sidebar (mobile) ----------
function initSidebar() {
    const btn = $('#mij-menu-btn');
    const sidebar = $('#mij-sidebar');
    const overlay = $('#mij-overlay');
    if (!btn || !sidebar || !overlay) return;

    const open = () => {
        sidebar.classList.add('is-open');
        overlay.classList.add('is-visible');
    };
    const close = () => {
        sidebar.classList.remove('is-open');
        overlay.classList.remove('is-visible');
    };

    btn.addEventListener('click', () => {
        sidebar.classList.contains('is-open') ? close() : open();
    });
    overlay.addEventListener('click', close);
}

// ---------- ripples ----------
function attachRipple(el, ev) {
    const rect = el.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const ripple = document.createElement('span');
    ripple.className = 'mij-ripple';
    ripple.style.width = ripple.style.height = size + 'px';
    const x = (ev.clientX || (rect.left + rect.width / 2)) - rect.left - size / 2;
    const y = (ev.clientY || (rect.top + rect.height / 2)) - rect.top - size / 2;
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    const computed = getComputedStyle(el).position;
    if (computed === 'static') el.style.position = 'relative';
    el.appendChild(ripple);
    setTimeout(() => ripple.remove(), 500);
}

function initRipples() {
    const selectors = '.mij-btn, .mij-fab, .mij-card-play, .mij-sidebar-link';
    document.body.addEventListener('click', (ev) => {
        const target = ev.target.closest(selectors);
        if (target) attachRipple(target, ev);
    });
}

// ---------- YouTube dynamic pieces ----------
function initYtPieces() {
    const tbody = $('#yt-pieces-tbody');
    const addBtn = $('#yt-add-piece');
    const countInput = $('#yt-piece-count');
    if (!tbody || !addBtn || !countInput) return;

    let pieceCount = tbody.querySelectorAll('.yt-piece-row').length;

    function reindex() {
        const rows = tbody.querySelectorAll('.yt-piece-row');
        rows.forEach((row, i) => {
            row.querySelectorAll('input, select').forEach((input) => {
                const name = input.getAttribute('name');
                if (name) {
                    // Replace the trailing index.
                    input.setAttribute('name', name.replace(/_\d+$/, `_${i}`));
                }
            });
        });
        countInput.value = rows.length;
    }

    function addRow() {
        const first = tbody.querySelector('.yt-piece-row');
        const tpl = first ? first.cloneNode(true) : document.createElement('tr');
        tpl.className = 'yt-piece-row';
        // Clear values.
        tpl.querySelectorAll('input').forEach((input) => {
            if (input.type === 'checkbox') {
                input.checked = true;
            } else {
                input.value = '';
            }
        });
        tbody.appendChild(tpl);
        pieceCount++;
        reindex();
    }

    function removeRow(btn) {
        const row = btn.closest('.yt-piece-row');
        if (row) {
            row.remove();
            reindex();
        }
    }

    addBtn.addEventListener('click', addRow);
    tbody.addEventListener('click', (ev) => {
        const btn = ev.target.closest('.yt-piece-remove');
        if (btn) removeRow(btn);
    });
}

// ---------- audio player ----------
function fmtTime(sec) {
    if (!isFinite(sec) || sec < 0) return '0:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return m + ':' + (s < 10 ? '0' + s : s);
}

// Repeat modes: 0 = off, 1 = all, 2 = one
const REPEAT_ICONS = ['\u{1F501}', '\u{1F501}', '\u{1F502}'];
const REPEAT_TITLES = ['Repeat: off', 'Repeat: all', 'Repeat: one'];

class Player {
    constructor() {
        this.el = $('#mij-player');
        if (!this.el) return;

        this.audio = new Audio();
        this.audio.preload = 'metadata';
        this.audio.volume = 1;

        // Queue of tracks for prev/next navigation.
        this.queue = [];
        this.queueIndex = -1;
        this.repeatMode = 0; // 0=off, 1=all, 2=one

        // Page-level queue context (e.g. playlist).
        this.pageQueue = null;

        // DOM elements.
        this.titleEl = $('#mij-player-title', this.el);
        this.artistEl = $('#mij-player-artist', this.el);
        this.coverEl = $('#mij-player-cover', this.el);
        this.fillEl = $('#mij-player-progress-fill', this.el);
        this.progressEl = $('#mij-player-progress', this.el);
        this.btnPlay = $('#mij-player-play', this.el);
        this.btnPrev = $('#mij-player-prev', this.el);
        this.btnNext = $('#mij-player-next', this.el);
        this.btnRepeat = $('#mij-player-repeat', this.el);
        this.btnQueue = $('#mij-player-queue', this.el);
        this.volumeBtn = $('#mij-player-volume-btn', this.el);
        this.volumeSlider = $('#mij-player-volume-slider', this.el);

        // Event wiring.
        this.btnPlay.addEventListener('click', () => this.toggle());
        this.btnPrev.addEventListener('click', () => this.prev());
        this.btnNext.addEventListener('click', () => this.next());
        this.btnRepeat.addEventListener('click', () => this.cycleRepeat());
        this.btnQueue.addEventListener('click', () => { window.location.href = '/queue'; });

        this.audio.addEventListener('timeupdate', () => this.updateProgress());
        this.audio.addEventListener('loadedmetadata', () => this.updateProgress());
        this.audio.addEventListener('play', () => { this.btnPlay.innerHTML = '\u2759\u2759'; });
        this.audio.addEventListener('pause', () => { this.btnPlay.innerHTML = '\u25B6'; });
        this.audio.addEventListener('ended', () => this.onEnded());

        // Progress bar: click + drag.
        this.progressEl.addEventListener('click', (ev) => this.seekTo(ev));
        this.progressEl.addEventListener('mousedown', (ev) => this.startDrag(ev));
        this.progressEl.addEventListener('touchstart', (ev) => this.startDrag(ev), { passive: false });

        // Volume.
        this.volumeSlider.addEventListener('input', () => {
            this.audio.volume = parseFloat(this.volumeSlider.value);
            this.updateVolumeIcon();
        });
        this.volumeBtn.addEventListener('click', () => {
            this.audio.muted = !this.audio.muted;
            this.updateVolumeIcon();
        });

        // Load page-level queue if present.
        this.loadPageQueue();

        // Wire up play links across the page.
        document.body.addEventListener('click', (ev) => {
            const link = ev.target.closest('.mij-play');
            if (!link) return;
            ev.preventDefault();
            const track = {
                url: link.getAttribute('data-stream-url') || link.href,
                title: link.getAttribute('data-title') || 'Unknown',
                artist: link.getAttribute('data-artist') || '',
                cover: link.getAttribute('data-cover') || '',
            };
            const qidx = link.getAttribute('data-queue-index');
            if (qidx !== null && this.pageQueue) {
                this.loadQueue(this.pageQueue, parseInt(qidx, 10));
            } else {
                this.load(track);
            }
        });

        // Play all button.
        const playAllBtn = $('#mij-play-all');
        if (playAllBtn && this.pageQueue) {
            playAllBtn.addEventListener('click', () => this.loadQueue(this.pageQueue, 0));
        }
    }

    loadPageQueue() {
        const el = $('#mij-queue-data');
        if (!el) return;
        try {
            this.pageQueue = JSON.parse(el.textContent);
        } catch {
            this.pageQueue = null;
        }
    }

    loadQueue(tracks, startIndex) {
        if (!this.el || !tracks.length) return;
        this.queue = tracks.slice();
        this.queueIndex = Math.max(0, Math.min(startIndex, this.queue.length - 1));
        this._loadCurrent();
    }

    load(track) {
        if (!this.el) return;
        // Add to queue if not already present.
        const existing = this.queue.findIndex((t) => t.url === track.url);
        if (existing >= 0) {
            this.queueIndex = existing;
        } else {
            this.queue.push(track);
            this.queueIndex = this.queue.length - 1;
        }
        this._loadCurrent();
    }

    _loadCurrent() {
        const track = this.queue[this.queueIndex];
        if (!track) return;
        this.audio.src = track.url;
        this.titleEl.textContent = track.title;
        this.artistEl.textContent = track.artist;
        if (track.cover) {
            this.coverEl.innerHTML = '';
            const img = document.createElement('img');
            img.src = track.cover;
            img.alt = '';
            this.coverEl.appendChild(img);
        } else {
            this.coverEl.innerHTML = '';
        }
        this.el.classList.add('is-active');
        this.audio.play().catch(() => {});
    }

    toggle() {
        if (!this.audio.src) return;
        if (this.audio.paused) this.audio.play(); else this.audio.pause();
    }

    prev() {
        if (this.queue.length === 0) return;
        if (this.audio.currentTime > 3) {
            this.audio.currentTime = 0;
            return;
        }
        this.queueIndex = (this.queueIndex - 1 + this.queue.length) % this.queue.length;
        this._loadCurrent();
    }

    next() {
        if (this.queue.length === 0) return;
        this.queueIndex = (this.queueIndex + 1) % this.queue.length;
        this._loadCurrent();
    }

    onEnded() {
        if (this.repeatMode === 2) {
            // Repeat one.
            this.audio.currentTime = 0;
            this.audio.play();
        } else if (this.repeatMode === 1) {
            // Repeat all.
            this.next();
        } else {
            // No repeat — go to next if available, otherwise stop.
            if (this.queueIndex < this.queue.length - 1) {
                this.next();
            }
        }
    }

    cycleRepeat() {
        this.repeatMode = (this.repeatMode + 1) % 3;
        this.btnRepeat.innerHTML = REPEAT_ICONS[this.repeatMode];
        this.btnRepeat.title = REPEAT_TITLES[this.repeatMode];
        this.btnRepeat.classList.toggle('is-active', this.repeatMode > 0);
    }

    seekTo(ev) {
        const rect = this.progressEl.getBoundingClientRect();
        const ratio = Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
        if (this.audio.duration) this.audio.currentTime = ratio * this.audio.duration;
    }

    startDrag(ev) {
        ev.preventDefault();
        this.progressEl.classList.add('is-dragging');
        this.seekTo(ev);

        const onMove = (e) => {
            const clientX = e.touches ? e.touches[0].clientX : e.clientX;
            const rect = this.progressEl.getBoundingClientRect();
            const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
            if (this.audio.duration) this.audio.currentTime = ratio * this.audio.duration;
        };
        const onEnd = () => {
            this.progressEl.classList.remove('is-dragging');
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onEnd);
            document.removeEventListener('touchmove', onMove);
            document.removeEventListener('touchend', onEnd);
        };

        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onEnd);
        document.addEventListener('touchmove', onMove, { passive: false });
        document.addEventListener('touchend', onEnd);
    }

    updateProgress() {
        const cur = this.audio.currentTime || 0;
        const tot = this.audio.duration || 0;
        if (tot > 0) this.fillEl.style.width = ((cur / tot) * 100) + '%';
    }

    updateVolumeIcon() {
        const muted = this.audio.muted || this.audio.volume === 0;
        const low = !muted && this.audio.volume < 0.5;
        this.volumeBtn.innerHTML = muted ? '\u{1F507}' : low ? '\u{1F509}' : '\u{1F50A}';
    }
}

// ---------- page fade transition ----------
function initPageFade() {
    document.body.classList.add('mij-page-fade');
    document.body.addEventListener('click', (ev) => {
        const a = ev.target.closest('a');
        if (!a) return;
        if (a.target === '_blank' || a.hasAttribute('download')) return;
        if (a.hasAttribute('data-no-fade')) return;
        if (a.classList.contains('mij-play')) return;
        const href = a.getAttribute('href') || '';
        if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;
        if (a.origin && a.origin !== location.origin) return;
        ev.preventDefault();
        document.body.classList.add('is-leaving');
        setTimeout(() => { window.location.href = href; }, 160);
    });
}

// ---------- delete confirmation ----------
function initConfirms() {
    $$('a[data-confirm]').forEach((a) => {
        a.addEventListener('click', (ev) => {
            if (!window.confirm(a.getAttribute('data-confirm'))) ev.preventDefault();
        });
    });
}

// ---------- boot ----------
document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    initRipples();
    new Player();
    initYtPieces();
    initPageFade();
    initConfirms();
});
