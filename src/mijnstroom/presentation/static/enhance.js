/* Mijnstroom — ES3-compatible progressive enhancements.
 *
 * SPA architecture:
 *  1. Intercept link clicks, fetch full HTML via XMLHttpRequest.
 *  2. Extract content from <div id="mij-spa-content"> in fetched page.
 *  3. Replace current #mij-spa-content with extracted content.
 *  4. Player and shell persist across navigation.
 *
 * ES3 constraints:
 *  - No const/let (use var)
 *  - No arrow functions (use function() {})
 *  - No template literals (use string concatenation)
 *  - No for..of (use for(var i=0; i<len; i++))
 *  - No array methods like forEach/map (use loops)
 *  - No Array.from / NodeList iteration (convert to array manually)
 */

// ===== Polyfills & helpers =====
function $(sel, root) {
    root = root || document;
    return root.querySelector ? root.querySelector(sel) : null;
}

function $$(sel, root) {
    root = root || document;
    var nodes = root.querySelectorAll ? root.querySelectorAll(sel) : [];
    var arr = [];
    for (var i = 0; i < nodes.length; i++) {
        arr.push(nodes[i]);
    }
    return arr;
}

function bind(el, event, handler) {
    if (el.addEventListener) {
        el.addEventListener(event, handler, false);
    } else if (el.attachEvent) {
        el.attachEvent('on' + event, handler);
    }
}

function unbind(el, event, handler) {
    if (el.removeEventListener) {
        el.removeEventListener(event, handler, false);
    } else if (el.detachEvent) {
        el.detachEvent('on' + event, handler);
    }
}

// ===== SPA Navigation =====
var spaEnabled = false;
var currentUrl = window.location.pathname + window.location.search;

function initSpaNav() {
    var contentEl = $('#mij-spa-content');
    if (!contentEl) return;

    spaEnabled = true;

    // Intercept link clicks
    bind(document.body, 'click', function(ev) {
        ev = ev || window.event;
        var target = ev.target || ev.srcElement;
        var a = target;

        // Walk up to find <a> tag
        while (a && a.tagName !== 'A') {
            a = a.parentNode;
        }

        if (!a || a.tagName !== 'A') return;
        if (a.target === '_blank') return;
        if (a.getAttribute('download')) return;
        if (a.getAttribute('data-no-spa')) return;
        if (a.className && a.className.indexOf('mij-play') >= 0) return;

        var href = a.getAttribute('href') || '';
        if (!href || href.indexOf('#') === 0 || href.indexOf('javascript:') === 0) return;

        // External links
        if (a.hostname && a.hostname !== window.location.hostname) return;

        // Prevent default
        if (ev.preventDefault) {
            ev.preventDefault();
        } else {
            ev.returnValue = false;
        }

        navigateTo(href);
    });

    // Intercept form submissions (GET only)
    bind(document.body, 'submit', function(ev) {
        ev = ev || window.event;
        var form = ev.target || ev.srcElement;
        if (form.tagName !== 'FORM') return;
        if (form.method && form.method.toLowerCase() !== 'get') return;
        if (form.getAttribute('data-no-spa')) return;

        if (ev.preventDefault) {
            ev.preventDefault();
        } else {
            ev.returnValue = false;
        }

        var action = form.getAttribute('action') || window.location.pathname;
        var params = serializeForm(form);
        navigateTo(action + '?' + params);
    });

    // Browser back/forward
    if (window.history && window.history.pushState) {
        bind(window, 'popstate', function() {
            fetchPage(window.location.pathname + window.location.search, true);
        });
    }
}

function serializeForm(form) {
    var params = [];
    var elements = form.elements;
    for (var i = 0; i < elements.length; i++) {
        var el = elements[i];
        if (!el.name) continue;
        if (el.type === 'checkbox' && !el.checked) continue;
        if (el.type === 'radio' && !el.checked) continue;
        params.push(encodeURIComponent(el.name) + '=' + encodeURIComponent(el.value || ''));
    }
    return params.join('&');
}

function navigateTo(url) {
    if (url === currentUrl) return;
    if (window.history && window.history.pushState) {
        window.history.pushState(null, '', url);
    }
    currentUrl = url;
    fetchPage(url, false);
}

function fetchPage(url, isPopstate) {
    var contentEl = $('#mij-spa-content');
    var fabEl = $('#mij-spa-fab');
    var scriptsEl = $('#mij-spa-scripts');
    var topbarEl = $('#mij-spa-topbar');
    if (!contentEl) {
        window.location.href = url;
        return;
    }

    showPreloader();

    var xhr = window.XMLHttpRequest ? new XMLHttpRequest() : new ActiveXObject('Microsoft.XMLHTTP');
    xhr.open('GET', url, true);
    xhr.setRequestHeader('X-Mijnstroom-SPA', '1');

    xhr.onreadystatechange = function() {
        if (xhr.readyState !== 4) return;

        hidePreloader();

        if (xhr.status >= 200 && xhr.status < 400) {
            var html = xhr.responseText;
            var parts = extractSpaParts(html);
            console.log(topbarEl);
            console.log(parts);
            if (parts) {
                contentEl.innerHTML = parts.content;
                if (fabEl) {
                    fabEl.innerHTML = parts.fab;
                    executeScripts(fabEl);
                }
                if (scriptsEl) {
                    scriptsEl.innerHTML = parts.scripts;
                    executeScripts(scriptsEl);
                }
                if (topbarEl) {
                    topbarEl.innerHTML = parts.topbar;
                    executeScripts(topbarEl);
                }
                updateSidebarActive();
                var title = extractTitle(html);
                if (title) document.title = title;
                reinitPage();
            } else {
                window.location.href = url;
            }
        } else {
            window.location.href = url;
        }
    };

    xhr.onerror = function() {
        hidePreloader();
        window.location.href = url;
    };

    xhr.send();
}

function executeScripts(container) {
    var scripts = container.getElementsByTagName('script');
    for (var i = 0; i < scripts.length; i++) {
        var script = scripts[i];
        if (script.type === 'application/json') continue; // Skip JSON data scripts
        
        var code = script.text || script.textContent || script.innerHTML || '';
        if (code) {
            try {
                // Use Function constructor for ES3 compatibility (safer than eval)
                var fn = new Function(code);
                fn();
            } catch (e) {
                // Silent fail - don't break page if script has error
            }
        }
    }
}

function extractSpaParts(html) {
    var content = extractBetween(html, '<div class="mij-content" id="mij-spa-content">', '</div>');
    var fab = extractBetween(html, '<div id="mij-spa-fab">', '</div>');
    var scripts = extractBetween(html, '<div id="mij-spa-scripts">', '</div>');
    var topbar = extractBetween(html, '<div class="mij-topbar" id="mij-spa-topbar">', '</div>');
    if (!content) return null;
    return {
        content: content || '',
        fab: fab || '',
        scripts: scripts || '',
        topbar: topbar || '',
    };
}

function extractBetween(html, startTag, endTag) {
    var start = html.indexOf(startTag);
    if (start < 0) return null;
    start += startTag.length;
    
    // Find matching closing tag with depth counting
    var depth = 1;
    var pos = start;
    while (depth > 0 && pos < html.length) {
        var nextOpen = html.indexOf('<div', pos);
        var nextClose = html.indexOf(endTag, pos);
        if (nextClose < 0) break;
        if (nextOpen >= 0 && nextOpen < nextClose) {
            depth++;
            pos = nextOpen + 4;
        } else {
            depth--;
            if (depth === 0) {
                return html.substring(start, nextClose);
            }
            pos = nextClose + endTag.length;
        }
    }
    return null;
}

function extractTitle(html) {
    var match = html.match(/<title[^>]*>(.*?)<\/title>/i);
    return match ? match[1] : null;
}

function updateSidebarActive() {
    var path = window.location.pathname;
    var links = $$('.mij-sidebar-link');
    for (var i = 0; i < links.length; i++) {
        var link = links[i];
        var href = link.getAttribute('href') || '';
        if (href !== '/' && path.indexOf(href) === 0) {
            link.className = link.className.replace(/ ?is-active/g, '') + ' is-active';
        } else {
            link.className = link.className.replace(/ ?is-active/g, '');
        }
    }
}

function reinitPage() {
    // Re-bind play links
    if (window.mijPlayer) {
        window.mijPlayer.rebindPlayLinks();
        window.mijPlayer.loadPageQueue();
    }
    // Re-init YouTube pieces
    initYtPieces();
    // Re-init confirms
    initConfirms();
}

// ===== Preloader =====
function showPreloader() {
    var el = $('#mij-preloader');
    if (el) el.className = 'mij-preloader is-visible';
}

function hidePreloader() {
    var el = $('#mij-preloader');
    if (el) el.className = 'mij-preloader';
}

// ===== Sidebar (mobile) =====
function initSidebar() {
    var btn = $('#mij-menu-btn');
    var sidebar = $('#mij-sidebar');
    var overlay = $('#mij-overlay');
    if (!btn || !sidebar || !overlay) return;

    var isOpen = false;

    function close() {
        sidebar.className = sidebar.className.replace(/ ?is-open/g, '');
        overlay.className = overlay.className.replace(/ ?is-visible/g, '');
        isOpen = false;
    }

    bind(btn, 'click', function() {
        if (isOpen) {
            close();
        } else {
            sidebar.className += ' is-open';
            overlay.className += ' is-visible';
            isOpen = true;
        }
    });

    bind(overlay, 'click', close);

    // Close sidebar when a link is clicked
    bind(sidebar, 'click', function(ev) {
        ev = ev || window.event;
        var target = ev.target || ev.srcElement;
        var a = target;
        while (a && a.tagName !== 'A') {
            a = a.parentNode;
        }
        if (a && a.tagName === 'A') {
            close();
        }
    });
}

// ===== Audio player =====
function fmtTime(sec) {
    if (!isFinite(sec) || sec < 0) return '0:00';
    var m = Math.floor(sec / 60);
    var s = Math.floor(sec % 60);
    return m + ':' + (s < 10 ? '0' + s : s);
}

var REPEAT_ICONS = ['\u{1F501}', '\u{1F501}', '\u{1F502}'];
var REPEAT_TITLES = ['Repeat: off', 'Repeat: all', 'Repeat: one'];

function Player() {
    var self = this;
    this.el = $('#mij-player');
    if (!this.el) return;

    this.audio = new Audio();
    this.audio.preload = 'metadata';
    this.audio.volume = 1;

    this.queue = [];
    this.queueIndex = -1;
    this.repeatMode = 0;
    this.pageQueue = null;

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

    bind(this.btnPlay, 'click', function() { self.toggle(); });
    bind(this.btnPrev, 'click', function() { self.prev(); });
    bind(this.btnNext, 'click', function() { self.next(); });
    bind(this.btnRepeat, 'click', function() { self.cycleRepeat(); });
    bind(this.btnQueue, 'click', function() { window.location.href = '/queue'; });

    bind(this.audio, 'timeupdate', function() { self.updateProgress(); });
    bind(this.audio, 'loadedmetadata', function() { self.updateProgress(); });
    bind(this.audio, 'play', function() { self.btnPlay.innerHTML = '\u2759\u2759'; });
    bind(this.audio, 'pause', function() { self.btnPlay.innerHTML = '\u25B6'; });
    bind(this.audio, 'ended', function() { self.onEnded(); });

    bind(this.progressEl, 'click', function(ev) { self.seekTo(ev); });
    bind(this.volumeSlider, 'input', function() {
        self.audio.volume = parseFloat(self.volumeSlider.value);
        self.updateVolumeIcon();
    });
    bind(this.volumeBtn, 'click', function() {
        self.audio.muted = !self.audio.muted;
        self.updateVolumeIcon();
    });

    this.loadPageQueue();
    this.rebindPlayLinks();

    window.mijPlayer = this;
}

Player.prototype.rebindPlayLinks = function() {
    var self = this;
    bind(document.body, 'click', function(ev) {
        ev = ev || window.event;
        var target = ev.target || ev.srcElement;
        var link = target;
        while (link && link.tagName !== 'A') {
            link = link.parentNode;
        }
        if (!link || link.className.indexOf('mij-play') < 0) return;

        if (ev.preventDefault) {
            ev.preventDefault();
        } else {
            ev.returnValue = false;
        }

        var track = {
            url: link.getAttribute('data-stream-url') || link.href,
            title: link.getAttribute('data-title') || 'Unknown',
            artist: link.getAttribute('data-artist') || '',
            cover: link.getAttribute('data-cover') || ''
        };

        var qidx = link.getAttribute('data-queue-index');
        if (qidx !== null && self.pageQueue) {
            self.loadQueue(self.pageQueue, parseInt(qidx, 10));
        } else {
            self.load(track);
        }
    });
};

Player.prototype.loadPageQueue = function() {
    var el = $('#mij-queue-data');
    if (!el) return;
    try {
        this.pageQueue = JSON.parse(el.textContent || el.innerText);
    } catch (e) {
        this.pageQueue = null;
    }
};

Player.prototype.loadQueue = function(tracks, startIndex) {
    if (!this.el || !tracks.length) return;
    this.queue = tracks.slice();
    this.queueIndex = Math.max(0, Math.min(startIndex, this.queue.length - 1));
    this._loadCurrent();
};

Player.prototype.load = function(track) {
    if (!this.el) return;
    var existing = -1;
    for (var i = 0; i < this.queue.length; i++) {
        if (this.queue[i].url === track.url) {
            existing = i;
            break;
        }
    }
    if (existing >= 0) {
        this.queueIndex = existing;
    } else {
        this.queue.push(track);
        this.queueIndex = this.queue.length - 1;
    }
    this._loadCurrent();
};

Player.prototype._loadCurrent = function() {
    var track = this.queue[this.queueIndex];
    if (!track) return;
    this.audio.src = track.url;
    this.titleEl.innerHTML = track.title;
    this.artistEl.innerHTML = track.artist;
    if (track.cover) {
        this.coverEl.innerHTML = '<img src="' + track.cover + '" alt="">';
    } else {
        this.coverEl.innerHTML = '';
    }
    this.el.className = this.el.className.replace(/ ?is-active/g, '') + ' is-active';
    this.audio.play();
};

Player.prototype.toggle = function() {
    if (!this.audio.src) return;
    if (this.audio.paused) {
        this.audio.play();
    } else {
        this.audio.pause();
    }
};

Player.prototype.prev = function() {
    if (this.queue.length === 0) return;
    if (this.audio.currentTime > 3) {
        this.audio.currentTime = 0;
        return;
    }
    this.queueIndex = (this.queueIndex - 1 + this.queue.length) % this.queue.length;
    this._loadCurrent();
};

Player.prototype.next = function() {
    if (this.queue.length === 0) return;
    this.queueIndex = (this.queueIndex + 1) % this.queue.length;
    this._loadCurrent();
};

Player.prototype.onEnded = function() {
    if (this.repeatMode === 2) {
        this.audio.currentTime = 0;
        this.audio.play();
    } else if (this.repeatMode === 1) {
        this.next();
    } else if (this.queueIndex < this.queue.length - 1) {
        this.next();
    }
};

Player.prototype.cycleRepeat = function() {
    this.repeatMode = (this.repeatMode + 1) % 3;
    this.btnRepeat.innerHTML = REPEAT_ICONS[this.repeatMode];
    this.btnRepeat.title = REPEAT_TITLES[this.repeatMode];
    if (this.repeatMode > 0) {
        this.btnRepeat.className = this.btnRepeat.className.replace(/ ?is-active/g, '') + ' is-active';
    } else {
        this.btnRepeat.className = this.btnRepeat.className.replace(/ ?is-active/g, '');
    }
};

Player.prototype.seekTo = function(ev) {
    ev = ev || window.event;
    var rect = this.progressEl.getBoundingClientRect ? this.progressEl.getBoundingClientRect() : this.progressEl.offsetWidth;
    var clientX = ev.clientX || 0;
    var ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    if (this.audio.duration) this.audio.currentTime = ratio * this.audio.duration;
};

Player.prototype.updateProgress = function() {
    var cur = this.audio.currentTime || 0;
    var tot = this.audio.duration || 0;
    if (tot > 0) this.fillEl.style.width = ((cur / tot) * 100) + '%';
};

Player.prototype.updateVolumeIcon = function() {
    var muted = this.audio.muted || this.audio.volume === 0;
    var low = !muted && this.audio.volume < 0.5;
    this.volumeBtn.innerHTML = muted ? '\u{1F507}' : (low ? '\u{1F509}' : '\u{1F50A}');
};

// ===== YouTube dynamic pieces =====
function initYtPieces() {
    var tbody = $('#yt-pieces-tbody');
    var addBtn = $('#yt-add-piece');
    var countInput = $('#yt-piece-count');
    if (!tbody || !addBtn || !countInput) return;

    function reindex() {
        var rows = $$('.yt-piece-row', tbody);
        for (var i = 0; i < rows.length; i++) {
            var inputs = rows[i].getElementsByTagName('input');
            for (var j = 0; j < inputs.length; j++) {
                var name = inputs[j].getAttribute('name');
                if (name) {
                    inputs[j].setAttribute('name', name.replace(/_\d+$/, '_' + i));
                }
            }
        }
        countInput.value = rows.length;
    }

    function addRow() {
        var first = $('.yt-piece-row', tbody);
        if (!first) return;
        var tpl = first.cloneNode(true);
        var inputs = tpl.getElementsByTagName('input');
        for (var i = 0; i < inputs.length; i++) {
            if (inputs[i].type === 'checkbox') {
                inputs[i].checked = true;
            } else {
                inputs[i].value = '';
            }
        }
        tbody.appendChild(tpl);
        reindex();
    }

    function removeRow(btn) {
        var row = btn.parentNode;
        while (row && row.className.indexOf('yt-piece-row') < 0) {
            row = row.parentNode;
        }
        if (row) {
            row.parentNode.removeChild(row);
            reindex();
        }
    }

    bind(addBtn, 'click', addRow);
    bind(tbody, 'click', function(ev) {
        ev = ev || window.event;
        var target = ev.target || ev.srcElement;
        var btn = target;
        while (btn && btn.className.indexOf('yt-piece-remove') < 0) {
            btn = btn.parentNode;
        }
        if (btn && btn.className.indexOf('yt-piece-remove') >= 0) {
            removeRow(btn);
        }
    });
}

// ===== Confirm interception =====
function initConfirms() {
    var links = $$('a[data-confirm]');
    for (var i = 0; i < links.length; i++) {
        (function(link) {
            bind(link, 'click', function(ev) {
                ev = ev || window.event;
                var msg = link.getAttribute('data-confirm');
                if (!confirm(msg)) {
                    if (ev.preventDefault) {
                        ev.preventDefault();
                    } else {
                        ev.returnValue = false;
                    }
                }
            });
        })(links[i]);
    }
}

// ===== Dialogs (ES3 simple modal) =====
function openDialog(title, bodyHtml, actionsHtml) {
    var header = $('#mij-dialog-header');
    var body = $('#mij-dialog-body');
    var actions = $('#mij-dialog-actions');
    var backdrop = $('#mij-dialog-backdrop');
    var dialog = $('#mij-dialog');

    if (!header || !body || !actions || !backdrop || !dialog) return;

    header.innerHTML = title;
    body.innerHTML = bodyHtml;
    actions.innerHTML = actionsHtml;

    backdrop.className = 'mij-dialog-backdrop is-open';
    dialog.className = 'mij-dialog is-open';
}

function closeDialog() {
    var backdrop = $('#mij-dialog-backdrop');
    var dialog = $('#mij-dialog');
    if (backdrop) backdrop.className = 'mij-dialog-backdrop';
    if (dialog) dialog.className = 'mij-dialog';
}

window.openDialog = openDialog;
window.closeDialog = closeDialog;

// ===== Boot =====
function onReady(fn) {
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        setTimeout(fn, 1);
    } else if (document.addEventListener) {
        document.addEventListener('DOMContentLoaded', fn);
    } else if (document.attachEvent) {
        document.attachEvent('onreadystatechange', function() {
            if (document.readyState === 'complete') fn();
        });
    }
}

onReady(function() {
    initSpaNav();
    initSidebar();
    new Player();
    initYtPieces();
    initConfirms();
});
