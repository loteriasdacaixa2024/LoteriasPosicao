(function () {
  'use strict';

  function pad(n) {
    return String(n).padStart(2, '0');
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function fmtDiag(d) {
    const sym = d.dir_sym || (d.dir === 'up' ? '↗' : '↘');
    const nums = d.nums_fmt || (d.nums || []).map(pad).join('-');
    return `${sym} ${nums}`;
  }

  function volanteHtml(itens) {
    const rows = [];
    let atual = [];
    (itens || []).forEach((item, i) => {
      const cls = item.estado === 'pendente' ? 'pend' : (item.estado === 'saiu' ? 'saiu' : 'fora');
      const title = item.estado === 'pendente' ? 'Ainda não saiu neste ciclo' : 'Já saiu neste ciclo';
      atual.push(`<span class="tf-ball ${cls}" title="${title}">${pad(item.n)}</span>`);
      if (atual.length === 10 || i === itens.length - 1) {
        rows.push(`<div class="tf-volante-row">${atual.join('')}</div>`);
        atual = [];
      }
    });
    return rows.join('');
  }

  function banner(info) {
    const modo = (info && info.modo) || '';
    const n = info && info.pendentes != null ? info.pendentes : '—';
    if (modo === 'fim') {
      return `<p class="small mb-2"><span class="tf-chip tf-st-proxima">Ciclo no fim · ${n} pendentes</span> entram na aposta quando cabem no padrão.</p>`;
    }
    if (modo === 'fechado') {
      return `<p class="small mb-2"><span class="tf-chip tf-st-dentro">Ciclo fechado</span> sem dezena amarela. O próximo sorteio reabre.</p>`;
    }
    if (modo === 'inicio') {
      return `<p class="small mb-2"><span class="tf-chip">Ciclo no começo · ${n} pendentes</span> ficam na prévia e não travam o jogo.</p>`;
    }
    return '';
  }

  function renderCiclo(ctx) {
    const el = document.getElementById('tfCiclo');
    if (!el) return;
    const c = ctx.ciclo || {};
    const info = ctx.ciclo_panorama || {};
    const pct = c.percentual_completo || 0;
    el.innerHTML = `
      ${banner(info)}
      <p class="small mb-2">Ciclo <strong>${c.numero_ciclo ?? '—'}</strong>
        · ${c.quantidade_concursos ?? '—'} concursos
        · <strong>${pct}%</strong> coberto</p>
      <div class="progress mb-2" style="height:.45rem">
        <div class="progress-bar" style="width:${pct}%;background:var(--primary)"></div>
      </div>
      <p class="small mb-1">Amarelo ainda não saiu · verde já saiu neste ciclo</p>
      ${volanteHtml(ctx.volante || [])}
    `;
  }

  function descarteLigado() {
    const chk = document.getElementById('chkDescartarHist');
    return !chk || chk.checked;
  }

  function textoAlvoForma(alvo) {
    const pares = `<strong>${alvo.pares ?? '—'} pares</strong>`;
    if (descarteLigado()) {
      return `Alvo da geração: ${pares}. Com “Descartar já sorteadas” ligado, a aposta não leva dezenas do último concurso.`;
    }
    return `Alvo da geração: ${pares} e <strong>${alvo.rep_min ?? 1}–${alvo.rep_max ?? 2}</strong> repetidas do último concurso.`;
  }

  let statsCtx = null;

  function renderStats(ctx) {
    statsCtx = ctx;
    const el = document.getElementById('tfStats');
    if (!el) return;
    const est = ctx.estatisticas || {};
    const m = est.medias || {};
    const pct = est.pct_com || {};
    const alvo = ctx.alvo_forma || {};
    el.innerHTML = `
      <p class="small text-muted mb-2">Janela inteira · ${est.total_sorteios ?? '—'} sorteios. Não depende de um concurso só.</p>
      <div class="d-flex flex-wrap gap-1 mb-2">
        <span class="tf-chip">Pares <strong>${m.pares ?? '—'}</strong></span>
        <span class="tf-chip">Ímpares <strong>${m.impares ?? '—'}</strong></span>
        <span class="tf-chip">Repetidos <strong>${m.repetidos ?? '—'}</strong></span>
        <span class="tf-chip">Em sequência <strong>${m.sequencias ?? '—'}</strong></span>
        <span class="tf-chip">Finais iguais <strong>${m.finais ?? '—'}</strong></span>
      </div>
      <p class="small mb-1">${textoAlvoForma(alvo)}</p>
      <p class="small text-muted mb-0">% da janela com o grupo — P ${pct.pares ?? '—'} · I ${pct.impares ?? '—'} · R ${pct.repetidos ?? '—'} · S ${pct.sequencias ?? '—'} · F ${pct.finais ?? '—'}</p>
    `;
  }

  function renderDiags(ctx) {
    const el = document.getElementById('tfDiags');
    if (!el) return;
    const info = ctx.diagonais || {};
    const ultimo = info.ultimo || [];
    el.innerHTML = `
      <p class="small mb-1">Último concurso ${info.ultimo_concurso || '—'}</p>
      <div class="mb-2">${ultimo.length
        ? ultimo.map((d) => `<span class="tf-chip tf-chip-diag">${esc(fmtDiag(d))}</span>`).join(' ')
        : '<span class="text-muted small">Sem diagonal neste concurso</span>'}</div>
      <p class="small text-muted mb-0">
        Na janela: <strong>${info.janela_com_diagonal ?? '—'}</strong> de ${info.janela_total ?? '—'}
        ${info.janela_pct != null ? ` (${info.janela_pct}%)` : ''} com diagonal.
        Cada aposta gerada mostra a diagonal dela.
      </p>
    `;
  }

  function stClass(status) {
    if (status === 'dentro') return 'tf-st-dentro';
    if (status === 'proxima') return 'tf-st-proxima';
    return 'tf-st-fora';
  }

  const SEQ_COLS = [
    { key: 'concurso', label: 'Concurso' },
    { key: 'padrao', label: 'Padrão' },
    { key: 'sequencia_n', label: 'Nº' },
    { key: 'dezenas_fmt', label: 'Dezenas' },
    { key: 'soma', label: 'Soma' },
    { key: 'status_media_label', label: 'Status' },
  ];
  const SEQ_DESC_FIRST = new Set(['concurso', 'sequencia_n', 'soma']);
  let seqSort = { key: 'concurso', dir: 'desc' };
  let seqView = null;

  function textoSeq(row, key) {
    if (key === 'status_media_label') return row.status_media_label || row.status_media || '—';
    const v = row[key];
    if (v == null || v === '') return '—';
    return String(v);
  }

  function valorSeq(row, key) {
    if (key === 'concurso' || key === 'soma' || key === 'sequencia_n') {
      const n = Number(row[key]);
      return Number.isFinite(n) ? n : null;
    }
    const s = textoSeq(row, key);
    return s === '—' ? '' : s;
  }

  function linhasSeq() {
    const rows = (seqView && seqView.rows) ? seqView.rows.slice() : [];
    const key = seqSort.key;
    const dir = seqSort.dir === 'asc' ? 1 : -1;
    rows.sort((a, b) => {
      const va = valorSeq(a, key);
      const vb = valorSeq(b, key);
      const aVazio = va == null || va === '';
      const bVazio = vb == null || vb === '';
      if (aVazio && bVazio) return a._i - b._i;
      if (aVazio) return 1;
      if (bVazio) return -1;
      let cmp = 0;
      if (typeof va === 'number' && typeof vb === 'number') cmp = va - vb;
      else cmp = String(va).localeCompare(String(vb), 'pt-BR', { numeric: true });
      if (!cmp) return a._i - b._i;
      return cmp * dir;
    });
    return rows;
  }

  function larguraCh(rows, key) {
    let n = 1;
    rows.forEach((row) => {
      const len = textoSeq(row, key).length;
      if (len > n) n = len;
    });
    return n;
  }

  function thSort(col) {
    const ativo = seqSort.key === col.key;
    const cls = ativo ? (seqSort.dir === 'asc' ? 'tf-sort tf-sort-asc' : 'tf-sort tf-sort-desc') : 'tf-sort';
    const ind = ativo ? (seqSort.dir === 'asc' ? '▲' : '▼') : '⇅';
    return `<th class="${cls}" data-sort="${col.key}" title="Clique para ordenar" scope="col" role="button" tabindex="0">${col.label} <span class="tf-sort-ind">${ind}</span></th>`;
  }

  function tdAlinha(texto, ch) {
    return `<td><span class="tf-alinha" style="min-width:${ch}ch">${esc(texto)}</span></td>`;
  }

  function bindSortSeq() {
    const el = document.getElementById('tfSeq');
    if (!el || el.dataset.tfSortBound) return;
    el.dataset.tfSortBound = '1';
    el.addEventListener('click', (ev) => {
      const th = ev.target.closest('th.tf-sort');
      if (!th || !seqView || !seqView.rows.length) return;
      const key = th.dataset.sort;
      if (!key) return;
      if (seqSort.key === key) seqSort.dir = seqSort.dir === 'asc' ? 'desc' : 'asc';
      else {
        seqSort.key = key;
        seqSort.dir = SEQ_DESC_FIRST.has(key) ? 'desc' : 'asc';
      }
      pintarSeq();
    });
    el.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Enter' && ev.key !== ' ') return;
      const th = ev.target.closest('th.tf-sort');
      if (!th) return;
      ev.preventDefault();
      th.click();
    });
  }

  function pintarSeq() {
    const el = document.getElementById('tfSeq');
    if (!el || !seqView) return;
    const seq = seqView.seq || {};
    const st = seq.status || {};
    const base = seqView.rows;
    const rows = linhasSeq();
    const larguras = {};
    SEQ_COLS.forEach((col) => {
      if (col.key !== 'status_media_label') larguras[col.key] = larguraCh(base, col.key);
    });
    const body = rows.map((r) => `
      <tr>
        ${tdAlinha(textoSeq(r, 'concurso'), larguras.concurso)}
        ${tdAlinha(textoSeq(r, 'padrao'), larguras.padrao)}
        ${tdAlinha(textoSeq(r, 'sequencia_n'), larguras.sequencia_n)}
        ${tdAlinha(textoSeq(r, 'dezenas_fmt'), larguras.dezenas_fmt)}
        ${tdAlinha(textoSeq(r, 'soma'), larguras.soma)}
        <td class="tf-status-td"><span class="tf-status-slot"><span class="tf-status ${stClass(r.status_media)}">${(r.status_media === 'dentro' || r.status_media === 'proxima') ? '●' : '○'} ${esc(textoSeq(r, 'status_media_label'))}</span></span></td>
      </tr>`).join('');
    el.innerHTML = `
      <p class="small mb-2">
        ${seq.total ?? 0} concursos
        ${seq.primeiro_concurso ? `· ${seq.primeiro_concurso}` : ''}
        ${seq.ultimo_concurso ? `a ${seq.ultimo_concurso}` : ''}.
        Status da soma:
        <span class="tf-chip tf-st-dentro">${st.pct_dentro ?? 0}% dentro</span>
        <span class="tf-chip tf-st-proxima">${st.pct_proxima ?? 0}% próxima</span>
        <span class="tf-chip tf-st-fora">${st.pct_fora ?? 0}% fora</span>
      </p>
      <div class="table-responsive">
        <table class="table table-sm mb-0 tf-seq">
          <thead>
            <tr>${SEQ_COLS.map(thSort).join('')}</tr>
          </thead>
          <tbody>${body || '<tr><td colspan="6" class="text-muted">Sem concursos.</td></tr>'}</tbody>
        </table>
      </div>
      <p class="small text-muted mb-0 mt-2">Últimos concursos da tabela. Clique no título da coluna para ordenar. A geração usa o histórico inteiro, com mais peso nos padrões frequentes e nas somas dentro ou próximas da média.</p>
    `;
  }

  function renderSeq(ctx) {
    const el = document.getElementById('tfSeq');
    if (!el) return;
    const seq = (ctx && ctx.sequencias) || {};
    seqView = {
      seq,
      rows: (seq.recentes || []).map((row, i) => Object.assign({ _i: i }, row)),
    };
    bindSortSeq();
    pintarSeq();
  }

  const chkDesc = document.getElementById('chkDescartarHist');
  if (chkDesc && !chkDesc.dataset.tfAlvoBound) {
    chkDesc.dataset.tfAlvoBound = '1';
    chkDesc.addEventListener('change', () => {
      if (statsCtx) renderStats(statsCtx);
    });
  }

  window.TresFontes = {
    render(ctx) {
      const ideia = document.getElementById('tfIdeia');
      if (ideia) ideia.textContent = (ctx && ctx.ideia) || 'Sem leitura das três fontes.';
      if (!ctx || !ctx.sucesso) {
        const msg = (ctx && ctx.erro) || 'Falha ao carregar.';
        ['tfCiclo', 'tfStats', 'tfDiags', 'tfSeq'].forEach((id) => {
          const el = document.getElementById(id);
          if (el) el.innerHTML = `<span class="text-danger small">${esc(msg)}</span>`;
        });
        return;
      }
      renderCiclo(ctx);
      renderStats(ctx);
      renderDiags(ctx);
      renderSeq(ctx);
    },
  };
})();
