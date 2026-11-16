/**
 * Select de Time do Coração e Trevos.
 * O caminho da API é montado em partes para o proxy público não quebrar a URL.
 */
(function (global) {
  'use strict';

  const TAILS = {
    time: 'api/time-coracao-opcoes',
    trevo: 'api/trevos-opcoes',
  };

  function apiPath(tail) {
    return '/' + String(tail || '').replace(/^\/+/, '');
  }

  function rootBeforeToken(path, token) {
    const src = String(path || '');
    const at = src.indexOf('/' + token);
    if (at < 0) return '';
    return src.slice(0, at + token.length + 1);
  }

  function opcoesUrl(kind) {
    const tail = TAILS[kind] || TAILS.time;
    const fromPage = (typeof location !== 'undefined')
      ? rootBeforeToken(location.pathname, 'geradores-elite')
      : '';
    const root = (fromPage || '').replace(/\/$/, '');
    return (root || '') + apiPath(tail);
  }

  function fill(selectEl, data) {
    if (!selectEl || !data || !data.opcoes || !data.opcoes.length) return;
    const prev = selectEl.value;
    selectEl.innerHTML = '';
    data.opcoes.forEach((o) => {
      const opt = document.createElement('option');
      opt.value = o.value;
      opt.textContent = o.label;
      selectEl.appendChild(opt);
    });
    const prefer = prev || data.default || 'atrasado';
    if ([].some.call(selectEl.options, (o) => o.value === String(prefer))) {
      selectEl.value = String(prefer);
    } else if (selectEl.options.length) {
      selectEl.selectedIndex = 0;
    }
  }

  async function fillFromApi(selectEl, kind) {
    if (!selectEl) return null;
    const r = await fetch(opcoesUrl(kind));
    const j = await r.json();
    if (!j || !j.sucesso) throw new Error((j && j.erro) || 'Falha ao carregar opções');
    fill(selectEl, j);
    return j;
  }

  global.ExtraAnaliseSelect = { fill, fillFromApi, opcoesUrl };
})(typeof window !== 'undefined' ? window : globalThis);
