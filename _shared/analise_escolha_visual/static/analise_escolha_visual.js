/**
 * Escolha Visual — destaques no volante por concurso.
 */
(function () {
  'use strict';

  const root = document.getElementById('ev-root');
  if (!root) return;

  const API = root.dataset.api || '/analise/api/escolha-visual';
  const PAD = parseInt(root.dataset.padWidth || '2', 10) || 2;

  let sorteios = [];
  let ordemNumeros = 'crescente'; // 'sorteio' | 'crescente'

  function fmt(n) {
    return String(Number(n)).padStart(PAD, '0');
  }

  function identificarSequencias(numeros) {
    const sorted = [...numeros].map(Number).sort((a, b) => a - b);
    const map = {};
    let seqId = 0;
    for (let i = 0; i < sorted.length; i++) {
      const hasPrev = i > 0 && sorted[i] - sorted[i - 1] === 1;
      const hasNext = i < sorted.length - 1 && sorted[i + 1] - sorted[i] === 1;
      if (hasPrev || hasNext) {
        if (!hasPrev) seqId++;
        map[sorted[i]] = seqId;
      }
    }
    return map;
  }

  function estaEmFinais(num, sorteio) {
    const digito = Number(num) % 10;
    return sorteio.numeros.filter((n) => Number(n) % 10 === digito).length > 1;
  }

  function atualizarResumo(lista) {
    if (!lista.length) return;
    const total = lista.length;
    const ordem = document.getElementById('evSelectOrdem').value;
    const counts = { pares: 0, impares: 0, repetidos: 0, sequencias: 0, finais: 0 };

    lista.forEach((sorteio, index) => {
      let anterior = null;
      if (ordem === 'desc') {
        if (index < lista.length - 1) anterior = lista[index + 1];
      } else if (index > 0) {
        anterior = lista[index - 1];
      }

      const nums = sorteio.numeros.map(Number);
      let temPar = false;
      let temImpar = false;
      let temFinais = false;
      const finaisCount = {};

      nums.forEach((n) => {
        if (n % 2 === 0) temPar = true;
        else temImpar = true;
        const d = n % 10;
        finaisCount[d] = (finaisCount[d] || 0) + 1;
        if (finaisCount[d] > 1) temFinais = true;
      });

      const temRepetido = !!(anterior && nums.some((n) => anterior.numeros.map(Number).includes(n)));
      const temSequencia = Object.keys(identificarSequencias(nums)).length > 0;

      if (temPar) counts.pares++;
      if (temImpar) counts.impares++;
      if (temRepetido) counts.repetidos++;
      if (temSequencia) counts.sequencias++;
      if (temFinais) counts.finais++;
    });

    document.getElementById('evTotalStats').textContent = String(total);
    ['pares', 'impares', 'repetidos', 'sequencias', 'finais'].forEach((id) => {
      const el = document.getElementById(`ev-stat-${id}`);
      if (!el) return;
      const c = counts[id];
      const pct = Math.round((c / total) * 100);
      el.innerHTML = `${c} <small class="text-muted fw-normal">(${pct}%)</small>`;
    });
  }

  function renderNumeros(sorteio, tipo, anterior, highlightInfo) {
    const nums = ordemNumeros === 'crescente'
      ? [...sorteio.numeros].map(Number).sort((a, b) => a - b)
      : sorteio.numeros.map(Number);
    const seqMap = tipo === 'sequencias' ? identificarSequencias(sorteio.numeros) : {};

    return nums.map((num) => {
      let classes = 'numero-escolha';
      let destacar = false;

      if (tipo === 'pares' && num % 2 === 0) {
        classes += ' dest-pares'; destacar = true;
      } else if (tipo === 'impares' && num % 2 !== 0) {
        classes += ' dest-impares'; destacar = true;
      } else if (tipo === 'repetidos' && anterior && anterior.numeros.map(Number).includes(num)) {
        classes += ' dest-repetidos'; destacar = true;
      } else if (tipo === 'sequencias' && seqMap[num]) {
        classes += ` dest-sequencia-${Math.min(3, seqMap[num])}`; destacar = true;
      } else if (tipo === 'finais' && estaEmFinais(num, sorteio)) {
        classes += ' dest-finais'; destacar = true;
      }

      if (destacar && highlightInfo) highlightInfo.teveDestaque = true;
      return `<div class="${classes}"${destacar ? ' title="Destacado"' : ''}>${fmt(num)}</div>`;
    }).join('');
  }

  function renderizar() {
    const container = document.getElementById('evDisplay');
    if (!container) return;
    if (!sorteios.length) {
      container.innerHTML = '<div class="text-center text-muted py-4">Nenhum sorteio carregado.</div>';
      return;
    }

    const toggle = document.querySelector('#ev-root .toggle-escolha:checked');
    const tipo = toggle ? toggle.dataset.tipo : null;
    const ordem = document.getElementById('evSelectOrdem').value;
    let totalComDestaque = 0;

    atualizarResumo(sorteios);
    container.innerHTML = '';

    sorteios.forEach((sorteio, index) => {
      let anterior = null;
      if (ordem === 'desc') {
        if (index < sorteios.length - 1) anterior = sorteios[index + 1];
      } else if (index > 0) {
        anterior = sorteios[index - 1];
      }

      const info = { teveDestaque: false };
      const htmlNums = renderNumeros(sorteio, tipo, anterior, info);
      if (info.teveDestaque) totalComDestaque++;

      const div = document.createElement('div');
      div.className = 'sorteio-escolha';
      div.dataset.concurso = String(sorteio.concurso);
      div.title = 'Clique para abrir Estatísticas deste concurso';
      div.innerHTML = `
        <div class="mb-2"><small class="text-muted">Concurso ${sorteio.concurso} — ${sorteio.data || ''}</small></div>
        <div class="numeros-sorteio">${htmlNums}</div>`;
      div.addEventListener('click', () => {
        window.dispatchEvent(new CustomEvent('ev:abrir-estatisticas', {
          detail: { concurso: sorteio.concurso },
        }));
      });
      container.appendChild(div);
    });

    document.querySelectorAll('#ev-root .badge-contagem').forEach((el) => { el.style.display = 'none'; });
    if (tipo) {
      const countEl = document.getElementById(`ev-count-${tipo}`);
      if (countEl) {
        countEl.textContent = String(totalComDestaque);
        countEl.style.display = 'inline-block';
      }
    }
  }

  async function carregar() {
    const container = document.getElementById('evDisplay');
    const ordem = document.getElementById('evSelectOrdem').value;
    const limite = document.getElementById('evSelectLimite').value;
    container.innerHTML = `
      <div class="text-center text-muted py-4">
        <div class="spinner-border spinner-border-sm text-primary"></div>
        <p class="mt-2 small mb-0">Carregando sorteios…</p>
      </div>`;

    try {
      const qs = new URLSearchParams({ ordem, limite: limite || '0', base: 'geral' });
      const r = await fetch(`${API}/sorteios?${qs}`);
      const data = await r.json();
      if (!data.sucesso) throw new Error(data.erro || 'Falha ao carregar');
      sorteios = data.sorteios || [];
      document.getElementById('evBadgeTotal').textContent =
        `${sorteios.length} de ${data.total_disponivel || sorteios.length} concursos`;
      renderizar();
    } catch (err) {
      container.innerHTML = `<div class="alert alert-danger mb-0"><i class="fas fa-exclamation-triangle"></i> ${err.message}</div>`;
    }
  }

  function setOrdemNumeros(modo) {
    ordemNumeros = modo;
    document.getElementById('evBtnOrdemSorteio').classList.toggle('active', modo === 'sorteio');
    document.getElementById('evBtnOrdemCrescente').classList.toggle('active', modo === 'crescente');
    renderizar();
  }

  function init() {
    document.getElementById('evBtnCarregar').addEventListener('click', carregar);
    document.getElementById('evSelectOrdem').addEventListener('change', carregar);
    document.getElementById('evSelectLimite').addEventListener('change', carregar);
    document.getElementById('evBtnOrdemSorteio').addEventListener('click', () => setOrdemNumeros('sorteio'));
    document.getElementById('evBtnOrdemCrescente').addEventListener('click', () => setOrdemNumeros('crescente'));

    document.querySelectorAll('#ev-root .toggle-escolha').forEach((toggle) => {
      toggle.addEventListener('change', function () {
        if (this.checked) {
          document.querySelectorAll('#ev-root .toggle-escolha').forEach((other) => {
            if (other !== this) other.checked = false;
          });
        }
        renderizar();
      });
    });

    setOrdemNumeros('crescente');
    carregar();
  }

  // Expõe controles para a aba Estatísticas reutilizar a mesma janela
  window.EvEscolha = {
    getFiltros() {
      return {
        ordem: document.getElementById('evSelectOrdem').value,
        limite: document.getElementById('evSelectLimite').value || '0',
      };
    },
    onCarregado(cb) {
      window.addEventListener('ev:sorteios-carregados', cb);
    },
  };

  const _carregarOrig = carregar;
  carregar = async function () {
    await _carregarOrig();
    window.dispatchEvent(new CustomEvent('ev:sorteios-carregados', {
      detail: { total: sorteios.length },
    }));
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
