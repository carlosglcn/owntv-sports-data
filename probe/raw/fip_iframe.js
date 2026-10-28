/**
 * padelfip — caricamento e refresh robusto dei widget in iframe
 * (Live Score, Order Of Play, Results).
 *
 * PROBLEMA RISOLTO
 * Il vecchio pattern `iframe.src = iframe.src` su setInterval ricarica l'iframe
 * in modo distruttivo: durante il reload l'iframe e' bianco e, se il reload
 * fallisce o stalla (rete mobile, Low Power Mode iOS, throttling dei timer in
 * background, ripristino da BFCache), resta bianco — i widget "spariscono",
 * soprattutto su iPhone e dopo il primo caricamento.
 *
 * SOLUZIONE
 * - Refresh "double-buffered": si carica un iframe nascosto con la stessa src e
 *   lo si scambia SOLO quando emette `load`. Il widget visibile non diventa mai
 *   bianco; se il caricamento fallisce, si tiene il vecchio iframe.
 * - Watchdog: se il caricamento non arriva entro il timeout, si ritenta.
 * - Refresh sull'attivazione: click sul tab, ritorno in foreground
 *   (visibilitychange) e ripristino da BFCache (pageshow).
 * - Il refresh periodico gira SOLO per il widget effettivamente visibile.
 *
 * USO (dagli script inline dei template):
 *   (window.padelfipWidgetQueue = window.padelfipWidgetQueue || []).push({
 *     containerId: 'oop-status',
 *     fetchUrl: '/.../get-oop-data.php?...', // oppure: src: 'https://...'
 *     title: 'Order Of Play',
 *     className: 'iframe-oop',
 *     intervalMs: 50000,
 *     errorText: 'Unable to load data.'      // opzionale
 *   });
 *   if (window.padelfipDrainWidgetQueue) window.padelfipDrainWidgetQueue();
 */
(function (w, d) {
    'use strict';

    var registry = (w.padelfipWidgets = w.padelfipWidgets || {});
    var LOAD_TIMEOUT_MS = 15000;
    var lifecycleBound = false;

    // Costruisce l'iframe applicando solo la classe: la dimensione e' governata
    // dal CSS (iframe.iframe-oop / .iframe-score / .iframe-livescore), quindi qui
    // NON impostiamo width/height inline per non sovrascriverlo.
    function buildIframe(cfg, src) {
        var f = d.createElement('iframe');
        f.src = src;
        f.title = cfg.title || '';
        f.className = cfg.className || 'iframe-oop';
        f.loading = 'lazy';
        return f;
    }

    function eachWidget(fn) {
        Object.keys(registry).forEach(function (key) {
            var wg = registry[key];
            if (wg && !wg.destroyed) fn(wg);
        });
    }

    // Lifecycle globale (una sola volta): foreground e BFCache.
    function bindGlobalLifecycle() {
        if (lifecycleBound) return;
        lifecycleBound = true;

        d.addEventListener('visibilitychange', function () {
            if (d.hidden) {
                eachWidget(function (wg) { wg.stopTimer(); });
            } else {
                eachWidget(function (wg) { wg.refresh(); wg.startTimer(); });
            }
        });

        // iOS Safari ripristina la pagina dalla BFCache con i timer morti e il
        // contenuto stantio: forziamo un refresh.
        w.addEventListener('pageshow', function (e) {
            if (e.persisted) {
                eachWidget(function (wg) { wg.refresh(); wg.startTimer(); });
            }
        });
    }

    function Widget(cfg) {
        this.cfg = cfg;
        this.id = cfg.containerId;
        this.container = d.getElementById(cfg.containerId);
        this.intervalMs = cfg.intervalMs || 50000;
        this.src = cfg.src || null;
        this.iframe = null;
        this.timer = null;
        this.refreshing = false;
        this.destroyed = false;
    }

    // Il container e' realmente visibile (nessun antenato in display:none).
    Widget.prototype.isVisible = function () {
        return !!(this.container && this.container.offsetParent !== null);
    };

    Widget.prototype.start = function () {
        if (!this.container) return;
        var self = this;

        if (this.cfg.fetchUrl && !this.src) {
            fetch(this.cfg.fetchUrl, { cache: 'no-store' })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (!data || !data.success) {
                        throw new Error(data && data.error ? data.error : 'load error');
                    }
                    if (self.destroyed) return;
                    self.src = data.oopUrl;
                    self.mount();
                })
                .catch(function (err) {
                    if (self.container) {
                        self.container.textContent =
                            self.cfg.errorText || (err && err.message) || 'Error';
                    }
                });
        } else if (this.src) {
            this.mount();
        }
    };

    Widget.prototype.mount = function () {
        if (this.destroyed || !this.container) return;
        this.iframe = buildIframe(this.cfg, this.src);
        this.container.innerHTML = '';
        this.container.appendChild(this.iframe);
        this.armWatchdog(this.iframe);
        this.startTimer();
        bindGlobalLifecycle();
    };

    // Se il primo `load` non arriva entro il timeout, prova un refresh.
    Widget.prototype.armWatchdog = function (frame) {
        var self = this;
        var done = false;
        var wd = setTimeout(function () {
            if (done) return;
            done = true;
            self.refresh();
        }, LOAD_TIMEOUT_MS);
        frame.addEventListener('load', function () {
            done = true;
            clearTimeout(wd);
        }, { once: true });
    };

    Widget.prototype.startTimer = function () {
        if (this.timer || this.destroyed) return;
        var self = this;
        this.timer = setInterval(function () {
            if (!d.hidden && self.isVisible()) self.refresh();
        }, this.intervalMs);
    };

    Widget.prototype.stopTimer = function () {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    };

    // Refresh non distruttivo: carica un buffer nascosto e scambia al `load`.
    Widget.prototype.refresh = function () {
        if (this.refreshing || this.destroyed || !this.container || !this.src) return;
        if (d.hidden || !this.isVisible()) return;

        this.refreshing = true;
        var self = this;
        var buf = buildIframe(this.cfg, this.src);

        // Nascosto ma ancora caricato (visibility:hidden, non display:none) e
        // fuori dal flusso per non disturbare il layout durante il caricamento.
        this.container.style.position = 'relative';
        buf.style.position = 'absolute';
        buf.style.top = '0';
        buf.style.left = '0';
        buf.style.width = '100%';
        buf.style.height = '100%';
        buf.style.visibility = 'hidden';
        buf.setAttribute('aria-hidden', 'true');

        var settled = false;
        var settle = function (ok) {
            if (settled) return;
            settled = true;
            clearTimeout(wd);
            self.refreshing = false;
            if (!self.container) return;

            if (ok) {
                // Promuovi il buffer: rimuovi gli stili inline cosi' torna
                // governato dal CSS (height 750px, width 100%).
                buf.style.position = '';
                buf.style.top = '';
                buf.style.left = '';
                buf.style.width = '';
                buf.style.height = '';
                buf.style.visibility = '';
                buf.removeAttribute('aria-hidden');
                if (self.iframe && self.iframe.parentNode) {
                    self.iframe.parentNode.removeChild(self.iframe);
                }
                self.iframe = buf;
            } else {
                // Fallito: butta il buffer, tieni il vecchio iframe visibile.
                if (buf.parentNode) buf.parentNode.removeChild(buf);
            }
        };

        buf.addEventListener('load', function () { settle(true); }, { once: true });
        buf.addEventListener('error', function () { settle(false); }, { once: true });
        var wd = setTimeout(function () { settle(false); }, LOAD_TIMEOUT_MS);

        this.container.appendChild(buf);
    };

    Widget.prototype.destroy = function () {
        this.destroyed = true;
        this.stopTimer();
    };

    function mountWidget(cfg) {
        if (!cfg || !cfg.containerId) return;
        // Re-injection safe: se esiste gia' un widget per quel container (es. il
        // tab livescore ricaricato via AJAX), fermiamo il precedente.
        var prev = registry[cfg.containerId];
        if (prev && prev.destroy) prev.destroy();

        var widget = new Widget(cfg);
        registry[cfg.containerId] = widget;
        widget.start();
    }

    w.padelfipMountWidget = mountWidget;

    // Coda: gli script inline (anche server-rendered o serviti da cache) accodano
    // le config; l'helper le consuma quando e' pronto, a prescindere dall'ordine
    // di caricamento degli script.
    w.padelfipDrainWidgetQueue = function () {
        var q = w.padelfipWidgetQueue;
        if (!q || !q.length) return;
        while (q.length) mountWidget(q.shift());
    };

    // Refresh dei widget contenuti in un nodo: usato al click sul tab per
    // recuperare un iframe eventualmente svuotato da iOS.
    w.padelfipRefreshWidgetsIn = function (root) {
        if (!root) return;
        eachWidget(function (wg) {
            if (wg.container && root.contains(wg.container)) {
                wg.refresh();
                wg.startTimer();
            }
        });
    };

    // Consuma quanto eventualmente gia' accodato prima del caricamento helper.
    w.padelfipDrainWidgetQueue();
})(window, document);
