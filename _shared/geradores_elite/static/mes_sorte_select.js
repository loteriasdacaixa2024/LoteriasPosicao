/**
 * Select padronizado — Mês da Sorte
 * Ordem: + Atrasado (X) → + Frequente (Y) → meses restantes → + Aleatório
 */
(function (global) {
  'use strict';

  const CACHE = { data: null, apiBase: null, promise: null };

  function apiBaseFrom(selOrBase) {
    if (typeof selOrBase === 'string' && selOrBase) return selOrBase.replace(/\/$/, '');
    if (global.__CC_API__) return String(global.__CC_API__).replace(/\/$/, '');
    if (global.__GE_API__) return String(global.__GE_API__).replace(/\/$/, '');
    return '';
  }

  function opcoesUrl(apiBase) {
    if (global.__MES_SORTE_API__) return String(global.__MES_SORTE_API__);
    const base = apiBaseFrom(apiBase);
    const m = base.match(/^(.*\/geradores-elite)/);
    if (m) return m[1] + '/api/mes-sorte-opcoes';
    if (base.includes('/api/')) return base.replace(/\/api\/.*/, '/api/mes-sorte-opcoes');
    return '/geradores-elite/api/mes-sorte-opcoes';
  }

  async function load(apiBase) {
    const url = opcoesUrl(apiBase);
    if (CACHE.data && CACHE.apiBase === url) return CACHE.data;
    if (CACHE.promise && CACHE.apiBase === url) return CACHE.promise;
    CACHE.apiBase = url;
    CACHE.promise = fetch(url)
      .then((r) => r.json())
      .then((j) => {
        if (!j || !j.sucesso) throw new Error((j && j.erro) || 'Falha ao carregar meses');
        CACHE.data = j;
        CACHE.promise = null;
        return j;
      })
      .catch((e) => {
        CACHE.promise = null;
        throw e;
      });
    return CACHE.promise;
  }

  function fill(selectEl, data, opts) {
    if (!selectEl || !data || !data.opcoes) return;
    opts = opts || {};
    const prefer = opts.selected != null && opts.selected !== ''
      ? String(opts.selected)
      : (opts.defaultPrefer || data.default || 'atrasado');
    const prev = selectEl.value;
    selectEl.innerHTML = '';
    if (opts.includeEmpty) {
      const empty = document.createElement('option');
      empty.value = '';
      empty.textContent = opts.emptyLabel || '— selecionar —';
      selectEl.appendChild(empty);
    }
    data.opcoes.forEach((o) => {
      const opt = document.createElement('option');
      opt.value = o.value;
      opt.textContent = o.label;
      if (o.mes_num != null) opt.dataset.mesNum = String(o.mes_num);
      if (o.criterio) opt.dataset.criterio = o.criterio;
      selectEl.appendChild(opt);
    });
    // Seleção: preferência explícita → valor anterior se ainda existir → default
    const candidates = [prefer, prev, data.default, 'atrasado'];
    for (let i = 0; i < candidates.length; i++) {
      const v = candidates[i];
      if (v == null || v === '') continue;
      const vs = String(v);
      if ([].some.call(selectEl.options, (o) => o.value === vs)) {
        selectEl.value = vs;
        return;
      }
      // se passou mes_num numérico, mapeia para value str ou critério correspondente
      const n = parseInt(vs, 10);
      if (!isNaN(n) && n >= 1 && n <= 12) {
        const byNum = [].find.call(selectEl.options, (o) => o.value === String(n));
        if (byNum) {
          selectEl.value = byNum.value;
          return;
        }
        if (data.atrasado && Number(data.atrasado.mes_num) === n) {
          selectEl.value = 'atrasado';
          return;
        }
        if (data.frequente && Number(data.frequente.mes_num) === n) {
          selectEl.value = 'frequente';
          return;
        }
      }
    }
    if (selectEl.options.length) selectEl.selectedIndex = opts.includeEmpty ? 1 : 0;
  }

  function resolveSync(value, data) {
    if (value == null || value === '') return null;
    const v = String(value).trim().toLowerCase();
    if (v === 'atrasado') return Number((data && data.atrasado && data.atrasado.mes_num) || 1);
    if (v === 'frequente') return Number((data && data.frequente && data.frequente.mes_num) || 1);
    if (v === 'aleatorio') return Math.floor(Math.random() * 12) + 1;
    const n = parseInt(v, 10);
    if (!isNaN(n) && n >= 1 && n <= 12) return n;
    return null;
  }

  function resolveFromSelect(selectEl, data) {
    if (!selectEl) return null;
    return resolveSync(selectEl.value, data || CACHE.data);
  }

  async function fillFromApi(selectEl, apiBase, opts) {
    const data = await load(apiBase);
    fill(selectEl, data, opts || {});
    return data;
  }

  async function resolveFromSelectAsync(selectEl, apiBase) {
    const data = CACHE.data || (await load(apiBase));
    return resolveFromSelect(selectEl, data);
  }

  global.MesSorteSelect = {
    load,
    fill,
    fillFromApi,
    resolveSync,
    resolveFromSelect,
    resolveFromSelectAsync,
    get cached() { return CACHE.data; },
  };
})(typeof window !== 'undefined' ? window : globalThis);
