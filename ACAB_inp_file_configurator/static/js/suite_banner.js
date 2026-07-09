/**
 * suite_banner.js — Puntos de estado del banner de navegación de la suite ACAB.
 *
 * Fragmento común de la suite — mantener sincronizado en los 3 repos:
 *   ACAB_inp_file_configurator / ACAB_fort_file_analyzer / COLLAPS_inp_file_configurator
 *
 * Al cargar la página y cada 15 s hace fetch a /api/ping de las otras apps
 * (único endpoint con CORS habilitado) y pinta ● verde si responde, ○ gris si no.
 * Si está gris, el enlace muestra un tooltip indicando cómo arrancarla.
 */

'use strict';

(function () {
  const PING_INTERVAL_MS = 15000;
  const PING_TIMEOUT_MS = 1500;

  function offlineTooltip() {
    // i18n si la app lo soporta (t() global de app.js); fallback en español
    // para las apps sin i18n (analyzer, chains).
    if (typeof window.t === 'function') {
      const v = window.t('suite.offline');
      if (v && v !== 'suite.offline') return v;
    }
    return 'No arrancada — usa suite_launcher.py';
  }

  function paint(link, ok) {
    const dot = link.querySelector('.suite-dot');
    if (!dot) return;
    dot.textContent = ok ? '●' : '○';
    dot.classList.toggle('text-success', ok);
    dot.classList.toggle('text-secondary', !ok);
    if (ok) {
      link.removeAttribute('title');
    } else {
      link.title = offlineTooltip();
    }
  }

  function pingAll() {
    document.querySelectorAll('#suite-banner a[data-suite-port]').forEach((link) => {
      const port = link.dataset.suitePort;
      fetch(`http://127.0.0.1:${port}/api/ping`, { signal: AbortSignal.timeout(PING_TIMEOUT_MS) })
        .then((res) => paint(link, res.ok))
        .catch(() => paint(link, false));
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('suite-banner')) return;
    pingAll();
    setInterval(pingAll, PING_INTERVAL_MS);
  });
})();
