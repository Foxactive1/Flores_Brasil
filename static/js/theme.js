/* ============================================================
   FLORES BRASIL — theme.js
   Utilitários de UI compartilhados por todas as páginas.
   Não contém nenhuma chamada de API/lógica de negócio — apenas
   apresentação (toast, modais, navbar, reveal-on-scroll).
   ============================================================ */
(function (global) {
  'use strict';

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str).replace(/[&<>"']/g, function (m) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m];
    });
  }

  /* ---------- Toast ---------- */
  let toastTimer = null;
  function ensureToastEl() {
    let el = document.getElementById('fb-toast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'fb-toast';
      el.className = 'fb-toast';
      el.setAttribute('role', 'status');
      el.setAttribute('aria-live', 'polite');
      document.body.appendChild(el);
    }
    return el;
  }
  function showToast(msg, opts) {
    opts = opts || {};
    const el = ensureToastEl();
    el.textContent = msg;
    el.className = 'fb-toast show' + (opts.error ? ' fb-toast--error' : '');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      el.classList.remove('show');
    }, opts.duration || 2800);
  }

  /* ---------- Modal base ---------- */
  let modalOverlay = null;
  let lastFocusedEl = null;

  function ensureModalEl() {
    if (modalOverlay) return modalOverlay;
    modalOverlay = document.createElement('div');
    modalOverlay.className = 'fb-modal-overlay';
    modalOverlay.innerHTML = '<div class="fb-modal" role="dialog" aria-modal="true"></div>';
    document.body.appendChild(modalOverlay);
    modalOverlay.addEventListener('click', function (e) {
      if (e.target === modalOverlay) closeModal();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modalOverlay.classList.contains('open')) closeModal();
    });
    return modalOverlay;
  }

  function openModal(innerHtml, focusSelector) {
    const overlay = ensureModalEl();
    lastFocusedEl = document.activeElement;
    overlay.querySelector('.fb-modal').innerHTML = innerHtml;
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    const toFocus = overlay.querySelector(focusSelector || 'input, button');
    if (toFocus) toFocus.focus();
  }

  function closeModal() {
    if (!modalOverlay) return;
    modalOverlay.classList.remove('open');
    document.body.style.overflow = '';
    if (lastFocusedEl && lastFocusedEl.focus) lastFocusedEl.focus();
  }

  /* Substitui window.confirm() por um modal consistente com o tema.
     Retorna uma Promise<boolean>. */
  function confirmModal(message, opts) {
    opts = opts || {};
    return new Promise(function (resolve) {
      openModal(
        '<h3>' + escapeHtml(opts.title || 'Confirmar ação') + '</h3>' +
        '<p>' + escapeHtml(message) + '</p>' +
        '<div class="fb-modal__actions">' +
          '<button type="button" class="btn btn--ghost" data-action="cancel">' + escapeHtml(opts.cancelLabel || 'Cancelar') + '</button>' +
          '<button type="button" class="btn ' + (opts.danger ? 'btn--danger' : 'btn--primary') + '" data-action="ok">' + escapeHtml(opts.okLabel || 'Confirmar') + '</button>' +
        '</div>',
        '[data-action="ok"]'
      );
      const overlay = ensureModalEl();
      function handler(e) {
        const action = e.target.getAttribute && e.target.getAttribute('data-action');
        if (action === 'ok') { cleanup(); closeModal(); resolve(true); }
        else if (action === 'cancel') { cleanup(); closeModal(); resolve(false); }
      }
      function cleanup() { overlay.removeEventListener('click', handler); }
      overlay.addEventListener('click', handler);
    });
  }

  /* Substitui window.prompt() por um modal com um ou mais campos.
     fields: [{ id, label, placeholder, value, type }]
     Retorna Promise<Object|null> — null se cancelado. */
  function promptModal(fields, opts) {
    opts = opts || {};
    return new Promise(function (resolve) {
      const fieldsHtml = fields.map(function (f) {
        return '<div class="field">' +
          '<label for="fb-pm-' + f.id + '">' + escapeHtml(f.label) + '</label>' +
          '<input id="fb-pm-' + f.id + '" type="' + (f.type || 'text') + '" ' +
          'placeholder="' + escapeHtml(f.placeholder || '') + '" value="' + escapeHtml(f.value || '') + '">' +
          '</div>';
      }).join('');

      openModal(
        '<h3>' + escapeHtml(opts.title || 'Informe os dados') + '</h3>' +
        (opts.description ? '<p>' + escapeHtml(opts.description) + '</p>' : '') +
        '<form data-role="fb-prompt-form">' + fieldsHtml +
        '<div class="fb-modal__actions">' +
          '<button type="button" class="btn btn--ghost" data-action="cancel">Cancelar</button>' +
          '<button type="submit" class="btn btn--primary" data-action="ok">' + escapeHtml(opts.okLabel || 'Continuar') + '</button>' +
        '</div></form>',
        'input'
      );

      const overlay = ensureModalEl();
      const form = overlay.querySelector('[data-role="fb-prompt-form"]');

      function collect() {
        const result = {};
        fields.forEach(function (f) {
          result[f.id] = overlay.querySelector('#fb-pm-' + f.id).value.trim();
        });
        return result;
      }

      function onSubmit(e) {
        e.preventDefault();
        cleanup(); closeModal(); resolve(collect());
      }
      function onClick(e) {
        if (e.target.getAttribute && e.target.getAttribute('data-action') === 'cancel') {
          cleanup(); closeModal(); resolve(null);
        }
      }
      function cleanup() {
        form.removeEventListener('submit', onSubmit);
        overlay.removeEventListener('click', onClick);
      }
      form.addEventListener('submit', onSubmit);
      overlay.addEventListener('click', onClick);
    });
  }

  /* ---------- Navbar shadow-on-scroll ---------- */
  function initNavbarScroll(selector) {
    const nav = document.querySelector(selector || '.fb-navbar');
    if (!nav) return;
    const toggle = function () { nav.classList.toggle('is-scrolled', window.scrollY > 20); };
    window.addEventListener('scroll', toggle, { passive: true });
    toggle();
  }

  /* ---------- Reveal-on-scroll ---------- */
  function initReveal(selector) {
    const els = document.querySelectorAll(selector || '.reveal');
    if (!els.length || !('IntersectionObserver' in window)) {
      els.forEach(function (el) { el.classList.add('visible'); });
      return;
    }
    const obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { entry.target.classList.add('visible'); obs.unobserve(entry.target); }
      });
    }, { threshold: 0.1 });
    els.forEach(function (el) { obs.observe(el); });
  }

  global.FB = {
    escapeHtml: escapeHtml,
    showToast: showToast,
    confirmModal: confirmModal,
    promptModal: promptModal,
    closeModal: closeModal,
    initNavbarScroll: initNavbarScroll,
    initReveal: initReveal
  };
})(window);
