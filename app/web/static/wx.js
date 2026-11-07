/* WXCOMMAND-PRO shared UI behavior: theme, navigation drawer, confirmation
 * dialogs, toasts, the live status strip, and unsaved-change tracking.
 * No frameworks; htmx handles server round-trips. */
(function () {
  'use strict';
  var doc = document, root = doc.documentElement;

  /* ---- theme (system / light / dark), remembered per browser ---- */
  var THEME_KEY = 'wx-theme';
  function readTheme() { try { return localStorage.getItem(THEME_KEY) || 'system'; } catch (e) { return 'system'; } }
  function applyTheme(mode) {
    if (mode === 'light' || mode === 'dark') root.setAttribute('data-theme', mode);
    else root.removeAttribute('data-theme');
    var btn = doc.getElementById('theme-toggle');
    if (btn) {
      var label = { system: 'Theme: match system', light: 'Theme: light', dark: 'Theme: dark' }[mode];
      btn.setAttribute('aria-label', label); btn.title = label;
      btn.querySelectorAll('[data-theme-icon]').forEach(function (i) { i.hidden = i.getAttribute('data-theme-icon') !== mode; });
    }
  }
  function cycleTheme() {
    var next = { system: 'light', light: 'dark', dark: 'system' }[readTheme()] || 'system';
    try { localStorage.setItem(THEME_KEY, next); } catch (e) { /* private mode: still applies for this page */ }
    applyTheme(next);
    toast('Theme: ' + (next === 'system' ? 'matches your system' : next), 'info');
  }

  /* ---- toasts ---- */
  var ICONS = { success: 'check-circle', danger: 'alert', warning: 'alert', info: 'info' };
  function toast(message, tone, ms) {
    tone = tone || 'info';
    var host = doc.getElementById('toasts');
    if (!host) return;
    var t = doc.createElement('div');
    t.className = 'toast ' + tone;
    t.setAttribute('role', tone === 'danger' ? 'alert' : 'status');
    t.innerHTML = '<svg class="icon" aria-hidden="true"><use href="#i-' + ICONS[tone] + '"/></svg><div></div>' +
      '<button class="toast-close" type="button" aria-label="Dismiss"><svg class="icon sm" aria-hidden="true"><use href="#i-x"/></svg></button>';
    t.querySelector('div').textContent = message;
    t.querySelector('.toast-close').onclick = function () { t.remove(); };
    host.appendChild(t);
    setTimeout(function () { t.remove(); }, ms || (tone === 'danger' ? 8000 : 4000));
  }

  /* ---- confirmation dialog (replaces window.confirm) ---- */
  var dlg, dlgResolve;
  function confirmDialog(opts) {
    dlg = dlg || doc.getElementById('confirm-dialog');
    if (!dlg || typeof dlg.showModal !== 'function') return Promise.resolve(window.confirm(opts.text));
    dlg.classList.toggle('is-danger', opts.tone === 'danger');
    dlg.querySelector('.modal-title').textContent = opts.title || 'Are you sure?';
    dlg.querySelector('.modal-text').textContent = opts.text || '';
    var ok = dlg.querySelector('[data-confirm-ok]');
    ok.textContent = opts.ok || 'Continue';
    ok.className = 'btn ' + (opts.tone === 'danger' ? 'danger' : '');
    return new Promise(function (resolve) {
      dlgResolve = resolve;
      dlg.showModal();
      dlg.querySelector('[data-confirm-cancel]').focus();
    });
  }
  function bindDialog() {
    dlg = doc.getElementById('confirm-dialog');
    if (!dlg) return;
    dlg.addEventListener('close', function () {
      if (dlgResolve) { dlgResolve(dlg.returnValue === 'ok'); dlgResolve = null; }
    });
  }
  function confirmOpts(elt, question) {
    return {
      text: question,
      title: elt.getAttribute('data-confirm-title'),
      ok: elt.getAttribute('data-confirm-ok'),
      tone: elt.getAttribute('data-confirm-tone')
    };
  }
  // htmx: route every hx-confirm through the styled dialog.
  doc.addEventListener('htmx:confirm', function (e) {
    if (!e.detail.question) return;
    e.preventDefault();
    confirmDialog(confirmOpts(e.detail.elt, e.detail.question)).then(function (yes) { if (yes) e.detail.issueRequest(true); });
  });
  // plain forms / links: data-confirm="question"
  doc.addEventListener('submit', function (e) {
    var f = e.target;
    if (!f.hasAttribute('data-confirm') || f.hasAttribute('hx-post') || f.dataset.confirmed === '1') return;
    e.preventDefault();
    confirmDialog(confirmOpts(f, f.getAttribute('data-confirm'))).then(function (yes) {
      if (yes) { f.dataset.confirmed = '1'; f.requestSubmit ? f.requestSubmit() : f.submit(); delete f.dataset.confirmed; }
    });
  }, true);

  /* ---- htmx feedback: failures and success toasts ---- */
  doc.addEventListener('htmx:responseError', function (e) {
    var x = e.detail.xhr;
    toast('Request failed (' + x.status + '). ' + (x.status === 403 ? 'The app refused a cross-site request.' : 'Check Troubleshoot for details.'), 'danger');
  });
  doc.addEventListener('htmx:sendError', function () { setServerLost(true); });
  doc.addEventListener('htmx:afterRequest', function (e) {
    if (e.detail.successful) setServerLost(false);
    var msg = e.detail.elt && e.detail.elt.getAttribute('data-success-toast');
    if (msg && e.detail.successful) toast(msg, 'success');
  });

  /* ---- live status strip (one shared poll; pages can subscribe) ---- */
  var lost = false;
  function setServerLost(v) {
    if (v === lost) return;
    lost = v;
    doc.body.classList.toggle('server-lost', v);
  }
  function setChip(id, tone, label, title) {
    var chip = doc.getElementById(id);
    if (!chip) return;
    chip.className = 'status-chip ' + (chip.getAttribute('data-live') && tone === 'success' ? 'is-live ' : '') ;
    var dot = chip.querySelector('.pulse');
    if (dot) dot.className = 'pulse tone-' + tone;
    chip.querySelector('.chip-label').textContent = label;
    if (title) chip.title = title;
  }
  var HEALTH = { healthy: ['success', 'All systems normal'], degraded: ['warning', 'Degraded'], critical: ['danger', 'Needs attention'] };
  function renderStatus(d) {
    var h = HEALTH[d.health] || ['muted', d.health];
    setChip('chip-health', h[0], h[1], 'System health');
    var enabled = d.radios.filter(function (r) { return r.enabled; });
    var online = enabled.filter(function (r) { return r.connected; }).length;
    var tone = !enabled.length ? 'muted' : online === enabled.length ? 'success' : online ? 'warning' : 'danger';
    setChip('chip-radios', tone, enabled.length ? online + ' of ' + enabled.length + ' radios online' : 'No radios enabled', 'Radio connections');
    var dry = d.dry_run === true || String(d.dry_run).toLowerCase() === 'true';
    setChip('chip-mode', dry ? 'warning' : 'success', dry ? 'Paused (dry run)' : 'Broadcasting live',
      dry ? 'Alerts are processed but not transmitted' : 'Matching alerts are transmitted automatically');
    var up = doc.getElementById('chip-updated');
    if (up) up.textContent = 'Updated ' + new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  }
  var lastOverview = null;
  function pollStatus() {
    if (doc.hidden) return;   // no background work while the window is hidden
    fetch('/api/ux/overview', { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (d) {
        setServerLost(false); lastOverview = d; renderStatus(d);
        doc.dispatchEvent(new CustomEvent('wx:overview', { detail: d }));
      })
      .catch(function () { setServerLost(true); });
  }

  /* ---- unsaved-changes tracking: <form data-track-changes> + .action-bar ---- */
  function bindDirty() {
    doc.querySelectorAll('form[data-track-changes]').forEach(function (form) {
      var bar = form.querySelector('.action-bar'), dirty = false;
      function mark() { dirty = true; if (bar) bar.classList.add('is-dirty'); }
      form.addEventListener('input', mark);
      form.addEventListener('change', mark);
      form.addEventListener('submit', function () { dirty = false; });
      window.addEventListener('beforeunload', function (e) { if (dirty) { e.preventDefault(); e.returnValue = ''; } });
    });
  }

  /* ---- navigation drawer (narrow windows) ---- */
  function setNav(open) {
    doc.body.classList.toggle('nav-open', open);
    var b = doc.getElementById('menu-btn');
    if (b) b.setAttribute('aria-expanded', String(open));
  }

  /* ---- checkbox picker helpers: [data-picker] with filter + select all/none ---- */
  function bindPickers(scope) {
    (scope || doc).querySelectorAll('[data-picker]').forEach(function (p) {
      if (p.dataset.bound) return; p.dataset.bound = '1';
      var grid = p.querySelector('.checkgrid'), filter = p.querySelector('[data-picker-filter]'), count = p.querySelector('[data-picker-count]');
      function update() {
        if (!count || !grid) return;
        var n = grid.querySelectorAll('input:checked').length;
        count.textContent = n + ' selected';
      }
      if (filter) filter.addEventListener('input', function () {
        var q = filter.value.trim().toLowerCase();
        grid.querySelectorAll('.check').forEach(function (c) { c.hidden = q && c.textContent.toLowerCase().indexOf(q) < 0; });
      });
      p.querySelectorAll('[data-picker-all],[data-picker-none]').forEach(function (b) {
        b.addEventListener('click', function () {
          var on = b.hasAttribute('data-picker-all');
          grid.querySelectorAll('.check:not([hidden]) input').forEach(function (i) { i.checked = on; });
          grid.dispatchEvent(new Event('change', { bubbles: true })); update();
        });
      });
      if (grid) grid.addEventListener('change', update);
      update();
    });
  }

  /* ---- boot ---- */
  applyTheme(readTheme());
  doc.addEventListener('DOMContentLoaded', function () {
    applyTheme(readTheme());
    bindDialog(); bindDirty(); bindPickers();
    var tb = doc.getElementById('theme-toggle'); if (tb) tb.addEventListener('click', cycleTheme);
    var mb = doc.getElementById('menu-btn'); if (mb) mb.addEventListener('click', function () { setNav(!doc.body.classList.contains('nav-open')); });
    var sc = doc.querySelector('.nav-scrim'); if (sc) sc.addEventListener('click', function () { setNav(false); });
    doc.addEventListener('keydown', function (e) { if (e.key === 'Escape') setNav(false); });
    var params = new URLSearchParams(location.search);
    if (params.get('saved') === '1') {
      toast('Settings saved', 'success');
      history.replaceState(null, '', location.pathname + location.hash);
    }
    if (doc.getElementById('chip-health')) { pollStatus(); setInterval(pollStatus, 15000); }
    doc.addEventListener('visibilitychange', function () { if (!doc.hidden && doc.getElementById('chip-health')) pollStatus(); });
  });
  doc.addEventListener('htmx:afterSwap', function (e) { bindPickers(e.target); });

  window.WX = { toast: toast, confirm: confirmDialog, refreshStatus: pollStatus, lastOverview: function () { return lastOverview; } };
})();
