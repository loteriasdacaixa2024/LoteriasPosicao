/**
 * Análise Tubular Inteligente — rankings e insights.
 */
(function () {
  'use strict';

  const root = document.getElementById('ati-root');
  if (!root) return;

  const API = root.dataset.api || '/analise/api/analise-tubular';
  const EXTRA_MES = root.dataset.extraMes === '1';

  let baseAtual = 'geral';
  let janelaAtual = 0;

  function statusClass(st) {
    if (st === 'MAIS') return 'success';
    if (st === 'MENOS') return 'danger';
    return 'warning';
  }

  function cardRanking(titulo, padroes, icone) {
    const medalhas = ['🥇', '🥈', '🥉'];
    const badges = ['badge-top1', 'badge-top2', 'badge-top3'];
    const rows = (padroes || []).map((p, index) => {
      const pos = index < 3
        ? `<span class="${badges[index]}">${medalhas[index]}</span>`
        : `${index + 1}º`;
      return `<tr>
        <td class="text-center">${pos}</td>
        <td>${p.descricao}</td>
        <td class="text-center"><strong>${p.frequencia}</strong></td>
        <td class="text-center">${p.percentual}%</td>
        <td class="text-center"><span class="badge bg-${statusClass(p.status)}">${p.status}</span></td>
      </tr>`;
    }).join('');

    return `<div class="card mb-3 border-0 shadow-sm">
      <div class="card-header ati-head"><i class="fas ${icone}"></i> ${titulo}</div>
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-striped table-hover mb-0">
            <thead><tr>
              <th class="text-center">Ranking</th>
              <th>Padrão</th>
              <th class="text-center">Frequência</th>
              <th class="text-center">%</th>
              <th class="text-center">Status</th>
            </tr></thead>
            <tbody>${rows || '<tr><td colspan="5" class="text-center text-muted">Sem dados</td></tr>'}</tbody>
          </table>
        </div>
      </div>
    </div>`;
  }

  function exibirResumo(data) {
    const totalFinais = (data.finais || []).reduce((t, i) => t + (i.frequencia || 0), 0);
    const cats = EXTRA_MES ? 8 : 7;
    const topFinal = data.finais && data.finais[0] ? data.finais[0].percentual : 0;
    document.getElementById('atiResumo').innerHTML = `
      <div class="col-md-2 col-6 mb-3"><h3>${data.total_concursos}</h3><small class="text-muted">Concursos<br>Analisados</small></div>
      <div class="col-md-2 col-6 mb-3"><h3>${data.sequencias.total}</h3><small class="text-muted">Padrões de<br>Sequência</small></div>
      <div class="col-md-2 col-6 mb-3"><h3>${totalFinais}</h3><small class="text-muted">Finais<br>Iguais</small></div>
      <div class="col-md-2 col-6 mb-3"><h3>${data.repeticoes.total}</h3><small class="text-muted">Repetições</small></div>
      <div class="col-md-2 col-6 mb-3"><h3>${cats}</h3><small class="text-muted">Categorias<br>Analisadas</small></div>
      <div class="col-md-2 col-6 mb-3"><h3>${topFinal}%</h3><small class="text-muted">Top Final<br>Dominante</small></div>`;
  }

  function exibirRankings(data) {
    let html = '';
    html += cardRanking('Sequências', data.sequencias.padroes, 'fa-bars-staggered');
    html += cardRanking('Finais Iguais', (data.finais || []).slice(0, 5), 'fa-hashtag');
    html += cardRanking('Repetições', [{
      descricao: 'Concursos com Repetições',
      frequencia: data.repeticoes.total,
      percentual: data.repeticoes.percentual,
      status: data.repeticoes.status,
    }], 'fa-rotate');
    html += cardRanking('Somas Mais Frequentes', data.somas.padroes, 'fa-calculator');
    html += cardRanking('Padrões Par/Ímpar', (data.pares_impares || []).slice(0, 5), 'fa-sliders');
    html += cardRanking('Padrões Inicial/Final', (data.padroes_iniciais_finais || []).slice(0, 5), 'fa-arrows-left-right');
    if (EXTRA_MES) {
      html += cardRanking('Meses da Sorte', data.meses, 'fa-calendar');
    }
    html += cardRanking('Dígitos Únicos', data.digitos_unicos, 'fa-1');
    document.getElementById('atiRankings').innerHTML = html;
  }

  function exibirInsights(data) {
    const seqTop = (data.sequencias.padroes || [])[0];
    const finaisTop = (data.finais || [])[0];
    const piTop = (data.pares_impares || [])[0];
    const mesesTop3 = EXTRA_MES
      ? (data.meses || []).slice(0, 3).map((m) => m.descricao).join(', ')
      : '';

    let html = '';
    if (seqTop) {
      html += `<div class="insight-box"><h6><i class="fas fa-chart-line"></i> Sequências</h6>
        <p class="mb-0">Padrão mais comum: <strong>${seqTop.descricao}</strong>
        (${seqTop.frequencia} · ${seqTop.percentual}%).
        Status: <span class="badge bg-${statusClass(seqTop.status)}">${seqTop.status}</span></p></div>`;
    }
    if (finaisTop) {
      const totalFin = (data.finais || []).reduce((t, i) => t + i.frequencia, 0);
      html += `<div class="insight-box"><h6><i class="fas fa-hashtag"></i> Finais Iguais</h6>
        <p class="mb-0">Dominante: <strong>${finaisTop.descricao}</strong>
        (${finaisTop.frequencia} · ${finaisTop.percentual}%).
        Total de ocorrências com finais iguais: <strong>${totalFin}</strong>.</p></div>`;
    }
    html += `<div class="insight-box"><h6><i class="fas fa-rotate"></i> Repetições</h6>
      <p class="mb-0"><strong>${data.repeticoes.percentual}%</strong> dos concursos (após o 1º) repetiram dezenas do anterior.
      Status: <span class="badge bg-${statusClass(data.repeticoes.status)}">${data.repeticoes.status}</span></p></div>`;
    if (piTop) {
      html += `<div class="insight-box"><h6><i class="fas fa-sliders"></i> Par/Ímpar</h6>
        <p class="mb-0">Mais frequente: <strong>${piTop.descricao}</strong>
        (${piTop.frequencia} · ${piTop.percentual}%).</p></div>`;
    }
    if (mesesTop3) {
      html += `<div class="insight-box"><h6><i class="fas fa-calendar-check"></i> Meses Prioritários</h6>
        <p class="mb-0">Top 3: <strong>${mesesTop3}</strong>.</p></div>`;
    }

    const recParts = [];
    if (seqTop) recParts.push(`priorizar <strong>${seqTop.descricao}</strong>`);
    if (finaisTop) recParts.push(`considerar finais <strong>${finaisTop.descricao}</strong>`);
    if (piTop) recParts.push(`manter <strong>${piTop.descricao}</strong>`);
    if (mesesTop3) recParts.push(`priorizar meses <strong>${mesesTop3}</strong>`);

    html += `<div class="insight-box ati-final"><h6><i class="fas fa-star"></i> Recomendação Estratégica</h6>
      <p class="mb-0">Com base nos Top padrões: ${recParts.join('; ') || 'dados insuficientes'}.</p></div>`;

    document.getElementById('atiInsights').innerHTML = html;
  }

  async function carregar() {
    const loading = document.getElementById('atiLoading');
    const content = document.getElementById('atiContent');
    loading.style.display = 'block';
    content.style.display = 'none';
    try {
      const qs = new URLSearchParams({ base: baseAtual, janela: String(janelaAtual) });
      const r = await fetch(`${API}/dados?${qs}`);
      const data = await r.json();
      if (!data.sucesso) throw new Error(data.erro || 'Falha na análise');
      exibirResumo(data);
      exibirRankings(data);
      exibirInsights(data);
      loading.style.display = 'none';
      content.style.display = 'block';
    } catch (err) {
      loading.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-triangle"></i> ${err.message}</div>`;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('atiBtnAtualizar').addEventListener('click', carregar);
    document.querySelectorAll('#atiTabsBase .base-tab-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#atiTabsBase .base-tab-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        baseAtual = btn.dataset.base;
        carregar();
      });
    });
    document.querySelectorAll('#atiJanelas .janela-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#atiJanelas .janela-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        janelaAtual = parseInt(btn.dataset.janela, 10) || 0;
        carregar();
      });
    });
    carregar();
  });
})();
