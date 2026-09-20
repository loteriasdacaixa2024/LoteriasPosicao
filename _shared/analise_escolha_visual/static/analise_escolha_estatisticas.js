/**
 * Escolha Visual — aba Estatísticas (enriquecimento).
 * Não altera a lógica da aba Escolha.
 */
(function () {
  'use strict';

  const root = document.getElementById('ev-root');
  if (!root) return;

  const API = root.dataset.api || '/analise/api/escolha-visual';
  const PAD = parseInt(root.dataset.padWidth || '2', 10) || 2;

  let payload = null;
  let charts = { paridade: null, grupos: null, cruz: null };
  let dirty = true;
  let linhasCache = { ordem: '', rows: [] };

  const CORES = {
    pares: '#28a745',
    impares: '#17a2b8',
    repetidos: '#9b59b6',
    sequencias: '#4ade80',
    finais: '#ffc107',
  };

  function fmt(n) {
    return String(Number(n)).padStart(PAD, '0');
  }

  function chips(dezenas) {
    if (!dezenas || !dezenas.length) return '<span class="text-muted">—</span>';
    return dezenas.map((d) => `<span class="ev-chip">${fmt(d)}</span>`).join('');
  }

  function filtros() {
    if (window.EvEscolha && window.EvEscolha.getFiltros) {
      return window.EvEscolha.getFiltros();
    }
    return {
      ordem: document.getElementById('evSelectOrdem')?.value || 'desc',
      limite: document.getElementById('evSelectLimite')?.value || '0',
    };
  }

  function progresso(pct, cor) {
    const p = Math.max(0, Math.min(100, Number(pct) || 0));
    return `<div class="progress ev-prog" role="progressbar" aria-valuenow="${p}">
      <div class="progress-bar" style="width:${p}%;background:${cor}"></div>
    </div>`;
  }

  async function carregarEnriquecimento(concurso) {
    const loading = document.getElementById('evStatLoading');
    const content = document.getElementById('evStatContent');
    loading.style.display = 'block';
    const f = filtros();
    const qs = new URLSearchParams({
      ordem: f.ordem,
      limite: f.limite,
      base: 'geral',
    });
    if (concurso) qs.set('concurso', String(concurso));

    try {
      const r = await fetch(`${API}/enriquecimento?${qs}`);
      const data = await r.json();
      if (!data.sucesso) throw new Error(data.erro || 'Falha no enriquecimento');
      payload = data;
      dirty = false;
      await garantirLinhasCompletas(f.ordem);
      preencherSelect();
      renderTudo();
      content.style.display = 'block';
    } catch (err) {
      content.innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
    } finally {
      loading.style.display = 'none';
    }
  }

  function preencherSelect() {
    const sel = document.getElementById('evStatSelectConc');
    const foco = payload.concurso_foco?.concurso;
    sel.innerHTML = (payload.concursos || []).map((c) =>
      `<option value="${c.concurso}"${c.concurso === foco ? ' selected' : ''}>Concurso ${c.concurso} — ${c.data || ''}</option>`
    ).join('');
    document.getElementById('evStatLabelJanela').textContent =
      `${payload.resumo?.total_sorteios || 0} concursos na janela`;
  }

  function renderKpis() {
    const r = payload.resumo || {};
    const medias = r.medias || {};
    const pct = r.pct_com || {};
    const items = [
      ['Pares (média)', medias.pares, pct.pares, CORES.pares],
      ['Ímpares (média)', medias.impares, pct.impares, CORES.impares],
      ['Repetidos (média)', medias.repetidos, pct.repetidos, CORES.repetidos],
      ['Em sequência (média)', medias.sequencias, pct.sequencias, CORES.sequencias],
      ['Finais iguais (média)', medias.finais, pct.finais, CORES.finais],
    ];
    document.getElementById('evStatKpis').innerHTML = items.map(([lab, med, p, cor]) => `
      <div class="col-6 col-md">
        <div class="ev-kpi-card">
          <div class="ev-kpi-lab">${lab}</div>
          <div class="ev-kpi-val" style="color:${cor}">${med ?? '—'}</div>
          <div class="small text-muted">${p ?? 0}% dos concursos com ≥1</div>
          ${progresso(p, cor)}
        </div>
      </div>`).join('');
  }

  function seqGrupos(nums) {
    const sorted = [...(nums || [])].map(Number).filter(Number.isFinite).sort((a, b) => a - b);
    const grupos = [];
    let i = 0;
    while (i < sorted.length) {
      if (i < sorted.length - 1 && sorted[i + 1] - sorted[i] === 1) {
        const g = [sorted[i]];
        while (i < sorted.length - 1 && sorted[i + 1] - sorted[i] === 1) {
          i += 1;
          g.push(sorted[i]);
        }
        grupos.push(g);
      }
      i += 1;
    }
    return grupos;
  }

  function finaisGrupos(nums) {
    const by = {};
    (nums || []).forEach((n) => {
      const v = Number(n);
      if (!Number.isFinite(v)) return;
      const d = v % 10;
      (by[d] = by[d] || []).push(v);
    });
    return Object.keys(by).map(Number).sort((a, b) => a - b)
      .map((d) => (by[d] || []).sort((a, b) => a - b))
      .filter((g) => g.length > 1);
  }

  function blocoGrupo(nome, itens, extra) {
    const lista = [...new Set((itens || []).map(Number).filter(Number.isFinite))].sort((a, b) => a - b);
    const out = { nome, quantidade: lista.length, dezenas: lista };
    if (extra) out.detalhe = extra;
    return out;
  }

  function linhaDeSorteio(s, anterior) {
    const nums = (s.numeros || []).map(Number).filter(Number.isFinite);
    const ant = new Set((anterior || []).map(Number));
    const pares = nums.filter((n) => n % 2 === 0);
    const impares = nums.filter((n) => n % 2 !== 0);
    const repetidos = nums.filter((n) => ant.has(n));
    const seqG = seqGrupos(nums);
    const seqFlat = [...new Set(seqG.flat())].sort((a, b) => a - b);
    const finG = finaisGrupos(nums);
    const finFlat = [...new Set(finG.flat())].sort((a, b) => a - b);
    return {
      concurso: s.concurso,
      data: s.data || '',
      numeros: nums,
      pares: blocoGrupo('Pares', pares),
      impares: blocoGrupo('Ímpares', impares),
      repetidos: blocoGrupo('Repetidos', repetidos),
      sequencias: blocoGrupo('Sequências', seqFlat, { grupos: seqG, qtd_grupos: seqG.length }),
      finais: blocoGrupo('Finais Iguais', finFlat, { grupos: finG, qtd_grupos: finG.length }),
    };
  }

  function linhasDeSorteios(sorteios, ordem) {
    const list = sorteios || [];
    return list.map((s, i) => {
      let ant = [];
      if (ordem === 'desc') {
        if (i < list.length - 1) ant = list[i + 1].numeros || [];
      } else if (i > 0) {
        ant = list[i - 1].numeros || [];
      }
      return linhaDeSorteio(s, ant);
    });
  }

  async function garantirLinhasCompletas(ordem) {
    const ord = ordem || 'desc';
    const atuais = payload && Array.isArray(payload.linhas_basicas) ? payload.linhas_basicas : [];
    const total = Number(payload && payload.total_disponivel) || 0;
    if (atuais.length && (!total || atuais.length >= total)) return;
    if (linhasCache.ordem === ord && linhasCache.rows.length && (!total || linhasCache.rows.length >= total)) {
      payload.linhas_basicas = linhasCache.rows;
      return;
    }
    const qs = new URLSearchParams({ ordem: ord, limite: '0', base: 'geral' });
    const r = await fetch(`${API}/sorteios?${qs}`);
    const data = await r.json();
    if (!data.sucesso) return;
    payload.linhas_basicas = linhasDeSorteios(data.sorteios || [], data.ordem || ord);
    linhasCache = { ordem: ord, rows: payload.linhas_basicas };
  }

  function detalheBasico(k, b) {
    if (k === 'sequencias' && b.detalhe?.grupos) {
      return `${b.detalhe.qtd_grupos} grupo(s): `
        + b.detalhe.grupos.map((g) => g.map(fmt).join('-')).join(' · ');
    }
    if (k === 'finais' && b.detalhe?.grupos) {
      return `${b.detalhe.qtd_grupos} final(is): `
        + b.detalhe.grupos.map((g) => g.map(fmt).join(',')).join(' · ');
    }
    return '';
  }

  function numsLinha(arr) {
    const lista = (arr || []).map(Number).filter(Number.isFinite);
    if (!lista.length) return '—';
    return lista.map(fmt).join(' ');
  }

  function celulaGrupo(k, b) {
    const bloco = b || {};
    if (k === 'sequencias') {
      const grupos = bloco.detalhe?.grupos || [];
      if (!grupos.length) return '—';
      return grupos.map((g) => g.map(fmt).join('-')).join(' · ');
    }
    if (k === 'finais') {
      const grupos = bloco.detalhe?.grupos || [];
      if (!grupos.length) return '—';
      return grupos.map((g) => g.map(fmt).join(',')).join(' · ');
    }
    return numsLinha(bloco.dezenas);
  }

  function renderBasicos() {
    const foco = payload.concurso_foco || {};
    const basicos = foco.basicos || {};
    const titulo = document.getElementById('evStatConcTitulo');
    if (titulo) titulo.textContent = String(foco.concurso || '—');
    const order = ['pares', 'impares', 'repetidos', 'sequencias', 'finais'];
    const rows = order.map((k) => {
      const b = basicos[k] || {};
      return { k, b, extra: detalheBasico(k, b) };
    });
    const cards = document.getElementById('evStatBasicos');
    if (cards) {
      cards.innerHTML = rows.map(({ k, b, extra }) => `
        <div class="col-md-6 col-xl">
          <div class="ev-basic-card" style="border-left-color:${CORES[k]}">
            <div class="fw-bold">${b.nome || k} = ${b.quantidade ?? 0}</div>
            <div class="mt-1">${chips(b.dezenas)}</div>
            ${extra ? `<div class="small text-muted mt-1">${extra}</div>` : ''}
          </div>
        </div>`).join('');
    }
    renderBasicosTabela();
  }

  function renderBasicosTabela() {
    const tbody = document.getElementById('evStatBasicosTabela');
    const nEl = document.getElementById('evStatBasicosN');
    if (!tbody) return;
    const linhas = payload.linhas_basicas || [];
    const focoN = Number(payload.concurso_foco?.concurso);
    if (nEl) {
      nEl.textContent = linhas.length
        ? `(${linhas.length.toLocaleString('pt-BR')} sorteio${linhas.length === 1 ? '' : 's'})`
        : '';
    }
    if (!linhas.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-muted">Sem sorteios na janela.</td></tr>';
      return;
    }
    tbody.innerHTML = linhas.map((ln) => {
      const isFoco = Number(ln.concurso) === focoN;
      return `<tr data-concurso="${ln.concurso}" class="${isFoco ? 'is-foco' : ''}">
        <td class="ev-basic-conc">${ln.concurso}</td>
        <td class="ev-basic-data">${ln.data || '—'}</td>
        <td class="ev-basic-nums" title="${numsLinha(ln.numeros)}">${numsLinha(ln.numeros)}</td>
        <td class="ev-basic-nums" style="color:${CORES.pares}" title="${celulaGrupo('pares', ln.pares)}">${celulaGrupo('pares', ln.pares)}</td>
        <td class="ev-basic-nums" style="color:${CORES.impares}" title="${celulaGrupo('impares', ln.impares)}">${celulaGrupo('impares', ln.impares)}</td>
        <td class="ev-basic-nums" style="color:${CORES.repetidos}" title="${celulaGrupo('repetidos', ln.repetidos)}">${celulaGrupo('repetidos', ln.repetidos)}</td>
        <td class="ev-basic-nums" style="color:${CORES.sequencias}" title="${celulaGrupo('sequencias', ln.sequencias)}">${celulaGrupo('sequencias', ln.sequencias)}</td>
        <td class="ev-basic-nums" style="color:${CORES.finais}" title="${celulaGrupo('finais', ln.finais)}">${celulaGrupo('finais', ln.finais)}</td>
      </tr>`;
    }).join('');
  }

  function scrollTabelaFoco() {
    const wrap = document.querySelector('#evStatBasicosTabelaBox .ev-basic-table-wrap');
    const row = document.querySelector('#evStatBasicosTabela tr.is-foco');
    if (!wrap || !row || wrap.closest('[hidden]')) return;
    try { row.scrollIntoView({ block: 'nearest' }); } catch (_) { /* ignore */ }
  }

  function renderCruzamentos() {
    const cruz = payload.concurso_foco?.cruzamentos || [];
    document.getElementById('evStatCruzConc').innerHTML = cruz.map((c) => `
      <div class="ev-cruz-row mb-2">
        <div class="d-flex justify-content-between gap-2">
          <strong class="small">${c.label}</strong>
          <span class="badge bg-secondary">${c.quantidade} · ${c.percentual_concurso}%</span>
        </div>
        <div class="mt-1">${chips(c.dezenas)}</div>
        ${progresso(c.percentual_concurso, 'var(--primary)')}
      </div>`).join('') || '<p class="text-muted small mb-0">Sem cruzamentos.</p>';

    const janela = payload.resumo?.cruzamentos_janela || [];
    document.getElementById('evStatCruzJanela').innerHTML = janela.map((c) => `
      <div class="ev-cruz-row mb-2">
        <div class="d-flex justify-content-between gap-2">
          <strong class="small">${c.label}</strong>
          <span class="badge bg-primary">${c.percentual_janela}%</span>
        </div>
        <div class="small text-muted">${c.concursos_com_intersecao} concursos · média ${c.media_dezenas} dezena(s)</div>
        ${progresso(c.percentual_janela, 'var(--accent)')}
      </div>`).join('') || '<p class="text-muted small mb-0">Sem dados.</p>';
  }

  function destroyChart(key) {
    if (charts[key]) {
      charts[key].destroy();
      charts[key] = null;
    }
  }

  function renderCharts() {
    const foco = payload.concurso_foco || {};
    const basicos = foco.basicos || {};
    const cruzJ = payload.resumo?.cruzamentos_janela || [];

    destroyChart('paridade');
    charts.paridade = new Chart(document.getElementById('evChartParidade'), {
      type: 'doughnut',
      data: {
        labels: ['Pares', 'Ímpares'],
        datasets: [{
          data: [
            basicos.pares?.quantidade || 0,
            basicos.impares?.quantidade || 0,
          ],
          backgroundColor: [CORES.pares, CORES.impares],
        }],
      },
      options: {
        plugins: { title: { display: true, text: `Paridade — Conc. ${foco.concurso || ''}` }, legend: { position: 'bottom' } },
      },
    });

    destroyChart('grupos');
    charts.grupos = new Chart(document.getElementById('evChartGrupos'), {
      type: 'bar',
      data: {
        labels: ['Pares', 'Ímpares', 'Repetidos', 'Sequências', 'Finais'],
        datasets: [{
          label: 'Qtd no concurso',
          data: [
            basicos.pares?.quantidade || 0,
            basicos.impares?.quantidade || 0,
            basicos.repetidos?.quantidade || 0,
            basicos.sequencias?.quantidade || 0,
            basicos.finais?.quantidade || 0,
          ],
          backgroundColor: [CORES.pares, CORES.impares, CORES.repetidos, CORES.sequencias, CORES.finais],
        }],
      },
      options: {
        plugins: { title: { display: true, text: 'Grupos no concurso' }, legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
      },
    });

    destroyChart('cruz');
    charts.cruz = new Chart(document.getElementById('evChartCruz'), {
      type: 'bar',
      data: {
        labels: cruzJ.map((c) => c.label.replace(' × ', '×')),
        datasets: [{
          label: '% janela',
          data: cruzJ.map((c) => c.percentual_janela),
          backgroundColor: '#c08b00',
        }],
      },
      options: {
        indexAxis: 'y',
        plugins: { title: { display: true, text: 'Cruzamentos na janela (%)' }, legend: { display: false } },
        scales: { x: { beginAtZero: true, max: 100 } },
      },
    });
  }

  function renderHeatmap() {
    const hm = payload.heatmap || {};
    const labels = hm.labels || [];
    const matrix = hm.matrix || [];
    const nomes = {
      pares: 'Pares', impares: 'Ímpares', repetidos: 'Rep.', sequencias: 'Seq.', finais: 'Finais',
    };
    let html = '<table class="table table-sm ev-heatmap mb-0"><thead><tr><th></th>';
    labels.forEach((l) => { html += `<th class="text-center">${nomes[l] || l}</th>`; });
    html += '</tr></thead><tbody>';
    labels.forEach((row, i) => {
      html += `<tr><th>${nomes[row] || row}</th>`;
      (matrix[i] || []).forEach((val, j) => {
        const isDiag = i === j;
        const intensity = isDiag ? Math.min(1, val / 7) : Math.min(1, val / 100);
        const bg = isDiag
          ? `rgba(192,139,0,${0.15 + intensity * 0.55})`
          : `rgba(21,101,192,${0.08 + intensity * 0.55})`;
        html += `<td class="text-center" style="background:${bg}" title="${isDiag ? 'média qtd' : '% janela'}">${Number(val).toFixed(1)}</td>`;
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    document.getElementById('evHeatmap').innerHTML = html;
  }

  function renderInsights() {
    const list = payload.insights || [];
    document.getElementById('evStatInsights').innerHTML = list.length
      ? list.map((ins) => `
        <div class="ev-insight ev-insight-${ins.tipo || 'info'}">
          <strong>${ins.titulo}</strong>
          <p class="mb-0 small">${ins.texto}</p>
        </div>`).join('')
      : '<p class="text-muted small">Sem insights para esta janela.</p>';
  }

  function renderTudo() {
    renderKpis();
    renderBasicos();
    renderCruzamentos();
    renderCharts();
    renderHeatmap();
    renderInsights();
  }

  function abrirEstatisticas(concurso) {
    const tabBtn = document.getElementById('ev-tab-estatisticas');
    if (tabBtn && window.bootstrap) {
      bootstrap.Tab.getOrCreateInstance(tabBtn).show();
    } else if (tabBtn) {
      tabBtn.click();
    }
    carregarEnriquecimento(concurso);
  }

  function nav(delta) {
    const sel = document.getElementById('evStatSelectConc');
    const opts = [...sel.options];
    if (!opts.length) return;
    let idx = sel.selectedIndex + delta;
    idx = Math.max(0, Math.min(opts.length - 1, idx));
    sel.selectedIndex = idx;
    carregarEnriquecimento(parseInt(sel.value, 10));
  }

  function init() {
    document.getElementById('evStatPrev')?.addEventListener('click', () => nav(-1));
    document.getElementById('evStatNext')?.addEventListener('click', () => nav(1));
    document.getElementById('evStatSelectConc')?.addEventListener('change', (e) => {
      carregarEnriquecimento(parseInt(e.target.value, 10));
    });
    document.getElementById('evStatRefresh')?.addEventListener('click', () => {
      const conc = parseInt(document.getElementById('evStatSelectConc').value, 10) || null;
      carregarEnriquecimento(conc);
    });
    document.getElementById('evStatBasicosFold')?.addEventListener('click', () => {
      const btn = document.getElementById('evStatBasicosFold');
      const box = document.getElementById('evStatBasicosTabelaBox');
      if (!btn || !box) return;
      const open = btn.getAttribute('aria-expanded') === 'true';
      btn.setAttribute('aria-expanded', open ? 'false' : 'true');
      box.hidden = open;
      if (!open) setTimeout(scrollTabelaFoco, 0);
    });

    document.getElementById('ev-tab-estatisticas')?.addEventListener('shown.bs.tab', () => {
      if (dirty || !payload) carregarEnriquecimento(null);
      else renderCharts();
    });

    ['evSelectOrdem', 'evSelectLimite'].forEach((id) => {
      document.getElementById(id)?.addEventListener('change', () => { dirty = true; });
    });
    document.getElementById('evBtnCarregar')?.addEventListener('click', () => { dirty = true; });

    window.addEventListener('ev:abrir-estatisticas', (e) => {
      abrirEstatisticas(e.detail?.concurso);
    });
    window.addEventListener('ev:sorteios-carregados', () => {
      dirty = true;
      linhasCache = { ordem: '', rows: [] };
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
