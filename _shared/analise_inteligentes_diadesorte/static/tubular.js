/**
 * Visualização Tubular — lógica fiel a vizualizacao_tubular.html
 * Cores: .seq-2 / .seq-3 / .seq-4 / .repetition (+ gradientes)
 * Emojis SEQ/FINAIS/Rept: ❌0 ✅n 🔥n 🚨n 🔸
 */
(function (global) {
  'use strict';

  const MESES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
  const MESES_ABREV = ['JAN','FEV','MAR','ABR','MAI','JUN','JUL','AGO','SET','OUT','NOV','DEZ'];

  function limitsFrom(el) {
    const root = el && el.closest ? el.closest('#ai-tubular-root') : (el || document.getElementById('ai-tubular-root'));
    const dmin = parseInt(root && root.dataset.dezenaMin, 10);
    const dmax = parseInt(root && root.dataset.dezenaMax, 10);
    const sort = parseInt(root && root.dataset.sorteadas, 10);
    return {
      dezenaMin: Number.isFinite(dmin) ? dmin : 1,
      dezenaMax: Number.isFinite(dmax) ? dmax : 31,
      sorteadas: Number.isFinite(sort) ? sort : 7,
      extraMes: !!(root && String(root.dataset.extraMes || '') === '1'),
    };
  }

  function hasMes(root) {
    return !!(root && String(root.dataset.extraMes || '') === '1');
  }

  /** Dezena com zero à esquerda (01, 02…); aceita 0 → "00" quando a modalidade usa dezena 0. */
  function fmt2(n) {
    if (n === '' || n == null) return '';
    const v = Number(n);
    if (!Number.isFinite(v)) return '';
    return String(Math.trunc(v)).padStart(2, '0');
  }

  /** Combinação C(n,k) — inteiro seguro para n típico de loteria. */
  function binom(n, k) {
    n = Number(n); k = Number(k);
    if (!Number.isFinite(n) || !Number.isFinite(k) || k < 0 || n < k) return 0;
    if (k === 0 || k === n) return 1;
    k = Math.min(k, n - k);
    let r = 1;
    for (let i = 1; i <= k; i++) r = (r * (n - k + i)) / i;
    return Math.round(r);
  }

  function fmtIntBR(n) {
    return String(Math.round(Number(n) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  function parityPool(L) {
    let even = 0;
    let odd = 0;
    for (let n = L.dezenaMin; n <= L.dezenaMax; n++) {
      if (n % 2 === 0) even++;
      else odd++;
    }
    return { even, odd };
  }

  /** Combinações com exatamente `pares` pares e (sorteadas − pares) ímpares. */
  function paresImparesCombos(pares, L) {
    const nSort = L.sorteadas;
    const p = Math.max(0, Math.min(nSort, Number(pares) || 0));
    const imp = nSort - p;
    const { even, odd } = parityPool(L);
    return binom(even, p) * binom(odd, imp);
  }

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  function analyzeSequences(numbers) {
    const sequences = [];
    const nums = numbers.map(Number);
    for (let i = 0; i < nums.length - 1; i++) {
      if (nums[i + 1] === nums[i] + 1) {
        let seqEnd = i + 1;
        while (seqEnd < nums.length - 1 && nums[seqEnd + 1] === nums[seqEnd] + 1) seqEnd++;
        sequences.push({ start: i, end: seqEnd, length: seqEnd - i + 1, numbers: nums.slice(i, seqEnd + 1) });
        i = seqEnd;
      }
    }
    return sequences;
  }

  function getEmojiByCount(count) {
    const c = Number(count) || 0;
    if (c === 0) return { emoji: '❌', text: '❌0' };
    if (c <= 2) return { emoji: '✅', text: `✅${c}` };
    if (c <= 4) return { emoji: '🔥', text: `🔥${c}` };
    return { emoji: '🚨', text: `🚨${c}` };
  }

  function calculateCompleteAnalysis(numbers, monthName) {
    const nums = numbers.map(Number);
    const sequences = analyzeSequences(nums);
    let seqQtde = 0;
    let seqQuais = '-';
    if (sequences.length === 1) seqQtde = sequences[0].length;
    else if (sequences.length > 1) seqQtde = sequences.length;
    if (sequences.length) {
      seqQuais = sequences.map(seq =>
        seq.length >= 3
          ? `${fmt2(seq.numbers[0])}-${fmt2(seq.numbers[seq.numbers.length - 1])}`
          : seq.numbers.map(fmt2).join(',')
      ).join(' ');
    }
    const finais = {};
    nums.forEach(num => { const f = num % 10; (finais[f] ||= []).push(num); });
    const finRep = Object.values(finais).filter(g => g.length > 1);
    const pares = nums.filter(n => n % 2 === 0).length;
    const digitos = [...new Set(nums.flatMap(n => String(n).padStart(2, '0').split('').map(Number)))].sort((a, b) => a - b);
    return {
      sequences,
      sequencesInfo: { tem: sequences.length > 0, qtde: seqQtde, quais: seqQuais },
      finaisIguais: {
        tem: finRep.length > 0,
        qtde: finRep.length,
        quais: finRep.length ? finRep.map(g => g.map(fmt2).join(',')).join(' ') : '-',
      },
      soma: nums.reduce((a, b) => a + b, 0),
      pares,
      impares: nums.length - pares,
      padroes: {
        inicial: nums.map(n => Math.floor(n / 10)).join(' '),
        final: nums.map(n => n % 10).join(' '),
      },
      mes: { nome: monthName || '', qtde: digitos.reduce((s, d) => s + d, 0) },
      digitosUnicos: digitos.join(' '),
      digitosLista: digitos,
      qtdeDigitos: digitos.length,
    };
  }

  function calculateRepetitions(currentNumbers, previousNumbers) {
    if (!previousNumbers || !previousNumbers.length) {
      return { count: 0, text: '🔸', title: 'Primeiro concurso (sem anterior)', emoji: '🔸', list: [] };
    }
    const list = currentNumbers.filter(n => previousNumbers.includes(n));
    const count = list.length;
    const emojiData = getEmojiByCount(count);
    let title;
    const listFmt = list.map(fmt2).join(', ');
    if (count === 0) title = 'Nenhuma repetição do concurso anterior';
    else if (count <= 2) title = `${count} número(s) repetido(s): ${listFmt}`;
    else if (count <= 4) title = `${count} números repetiram (alta): ${listFmt}`;
    else title = `${count} números repetiram (extrema!): ${listFmt}`;
    return { count, text: emojiData.text, title, emoji: emojiData.emoji, list };
  }

  function detectAllConditions(number, sequences, repetitions) {
    const conditions = [];
    if (repetitions.includes(number)) conditions.push('repetition');
    let maxLen = 0;
    sequences.forEach(seq => {
      if (seq.numbers.includes(number)) maxLen = Math.max(maxLen, seq.length);
    });
    if (maxLen >= 4) conditions.push('seq-4');
    else if (maxLen === 3) conditions.push('seq-3');
    else if (maxLen === 2) conditions.push('seq-2');
    return conditions;
  }

  function createGradientStyle(conditions) {
    if (!conditions.length) return { background: '', title: 'Número normal' };
    if (conditions.length === 1) {
      const map = {
        repetition: { color: 'var(--cor-repetidos)', text: 'var(--cor-repetidos-texto)', name: 'Repetição' },
        'seq-2': { color: 'var(--cor-sequencia-1)', text: 'var(--cor-sequencia-1-texto)', name: 'Sequência de 2' },
        'seq-3': { color: 'var(--cor-sequencia-2)', text: 'var(--cor-sequencia-2-texto)', name: 'Sequência de 3' },
        'seq-4': { color: 'var(--cor-sequencia-3)', text: 'var(--cor-sequencia-3-texto)', name: 'Sequência de 4+' },
      };
      const d = map[conditions[0]];
      return { background: `background-color:${d.color};color:${d.text}`, title: d.name };
    }
    const priority = ['repetition', 'seq-4', 'seq-3', 'seq-2'];
    const colors = [];
    const desc = [];
    priority.forEach(t => {
      if (!conditions.includes(t)) return;
      if (t === 'repetition') { colors.push('var(--cor-repetidos)'); desc.push('Repetição'); }
      if (t === 'seq-2') { colors.push('var(--cor-sequencia-1)'); desc.push('Seq. 2'); }
      if (t === 'seq-3') { colors.push('var(--cor-sequencia-2)'); desc.push('Seq. 3'); }
      if (t === 'seq-4') { colors.push('var(--cor-sequencia-3)'); desc.push('Seq. 4+'); }
    });
    const textMap = {
      repetition: 'var(--cor-repetidos-texto)',
      'seq-2': 'var(--cor-sequencia-1-texto)',
      'seq-3': 'var(--cor-sequencia-2-texto)',
      'seq-4': 'var(--cor-sequencia-3-texto)',
    };
    const textColor = textMap[conditions[0]] || '#000';
    let bg = '';
    if (colors.length === 2) {
      bg = `background:linear-gradient(135deg,${colors[0]} 0%,${colors[0]} 50%,${colors[1]} 50%,${colors[1]} 100%);color:${textColor}`;
    } else if (colors.length === 3) {
      bg = `background:linear-gradient(135deg,${colors[0]} 0%,${colors[0]} 33%,${colors[1]} 33%,${colors[1]} 66%,${colors[2]} 66%,${colors[2]} 100%);color:${textColor}`;
    } else {
      bg = `background:linear-gradient(135deg,${colors[0]} 0%,${colors[0]} 25%,${colors[1]} 25%,${colors[1]} 50%,${colors[2]} 50%,${colors[2]} 75%,${colors[3]} 75%,${colors[3]} 100%);color:${textColor}`;
    }
    return { background: bg, title: `MÚLTIPLAS: ${desc.join(' + ')}` };
  }

  function modeFreq(values) {
    if (!values.length) return '-';
    const f = {};
    values.forEach(v => { f[v] = (f[v] || 0) + 1; });
    return Object.entries(f).sort((a, b) => b[1] - a[1])[0][0];
  }
  function leastFreq(values) {
    if (!values.length) return '-';
    const f = {};
    values.forEach(v => { f[v] = (f[v] || 0) + 1; });
    return Object.entries(f).sort((a, b) => a[1] - b[1])[0][0];
  }
  function avgNum(values) {
    const nums = values.map(Number).filter(n => !isNaN(n));
    if (!nums.length) return '-';
    return Math.round(nums.reduce((a, b) => a + b, 0) / nums.length);
  }

  function parseJogosTexto(txt, lim) {
    const L = lim || limitsFrom(document.getElementById('ai-tubular-root'));
    return String(txt || '').split(/\n+/).map(line => {
      const nums = (line.match(/\d{1,2}/g) || []).map(Number).filter(n => n >= L.dezenaMin && n <= L.dezenaMax);
      if (nums.length < L.sorteadas) return null;
      let mes = 0;
      let monthName = '';
      if (L.extraMes) {
        mes = 1;
        monthName = MESES[0];
        const mName = line.match(/(Janeiro|Fevereiro|Março|Marco|Abril|Maio|Junho|Julho|Agosto|Setembro|Outubro|Novembro|Dezembro|JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)/i);
        if (mName) {
          const raw = mName[1].toUpperCase().normalize('NFD').replace(/\p{M}/gu, '');
          const idx = MESES_ABREV.findIndex(a => a === raw.slice(0, 3) || MESES[MESES_ABREV.indexOf(a)]?.toUpperCase().normalize('NFD').replace(/\p{M}/gu, '').startsWith(raw.slice(0, 3)));
          const i2 = MESES.findIndex(m => m.toUpperCase().normalize('NFD').replace(/\p{M}/gu, '').startsWith(raw.slice(0, 3)));
          mes = (idx >= 0 ? idx : i2) + 1 || 1;
          monthName = MESES[mes - 1] || '';
        } else {
          const mNum = line.match(/-\s*(\d{1,2})\s*$/);
          if (mNum) {
            mes = Math.min(12, Math.max(1, +mNum[1]));
            monthName = MESES[mes - 1] || '';
          }
        }
      }
      return { numbers: nums.slice(0, L.sorteadas), month: mes, monthName };
    }).filter(Boolean);
  }

  function downloadBlob(content, nome, type) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([content], { type }));
    a.download = nome;
    a.click();
  }

  function TubularApp(root) {
    this.root = root;
    this.api = root.dataset.api || '/analise/api/inteligentes';
    this.extraMes = hasMes(root);
    this.mesesCores = {};
    try { this.mesesCores = JSON.parse(root.dataset.mesesCores || '{}'); } catch (_) {}
    this.data = [];
    this.view = 'asc'; // draw | asc — Crescente por padrão
    this.marked = true;
    this.page = 1;
    this.pageSize = 100;
    this.sortKey = 'contest';
    this.sortDir = 'asc';
    this.manual10 = [];
    this.manual11 = [];
    this._manualUid = 0;
    this.manual10SortKey = null;
    this.manual10SortDir = 'asc';
    this.manual11SortKey = null;
    this.manual11SortDir = 'asc';
    this.stats11Open = false;
    this.conferencia11 = null; // { contest, nums: number[] }
    this.faltantesCiclo = new Set(); // dezenas pendentes do ciclo atual
    this.manual10BlockMsg = '';
    this.auto11Janela = 10;
    this.auto11SomaModo = 'padrao';
    this.auto11ParesModo = 'fix_4';
    this._bind();
  }

  TubularApp.prototype._effectivePageSize = function () {
    const n = Number(this.pageSize);
    if (!n || n <= 0) return Math.max(1, this.data.length || 1);
    return n;
  };

  /** Última página = concursos mais recentes (ordem crescente por concurso). */
  TubularApp.prototype._goLastPage = function () {
    const size = this._effectivePageSize();
    const total = (this.data || []).length;
    this.page = Math.max(1, Math.ceil(total / size) || 1);
  };

  TubularApp.prototype._chronoAsc = function () {
    return [...this.data].sort((a, b) => a.contest - b.contest);
  };

  TubularApp.prototype._sortValue = function (c, chronoAsc, key, idxMap) {
    const nums = this.numsFor(c);
    const idx = idxMap ? idxMap.get(c.contest) : chronoAsc.findIndex(x => x.contest === c.contest);
    const prev = idx > 0 ? this.numsFor(chronoAsc[idx - 1]) : [];
    const an = calculateCompleteAnalysis(nums, c.monthName);
    const rept = calculateRepetitions(nums, prev);
    if (String(key || '').startsWith('dez')) {
      const i = parseInt(String(key).slice(3), 10);
      return Number.isFinite(i) ? (nums[i] || 0) : 0;
    }
    switch (key) {
      case 'contest': return +c.contest || 0;
      case 'date': return String(c.date || '');
      case 'mes': return +c.month || 0;
      case 'seq': return an.sequencesInfo.qtde || 0;
      case 'finais': return an.finaisIguais.qtde || 0;
      case 'rept': return (rept.list || []).length;
      case 'soma': return an.soma || 0;
      case 'pares': return an.pares || 0;
      case 'impares': return an.impares || 0;
      case 'inicial': return String(an.padroes.inicial || '');
      case 'final': return String(an.padroes.final || '');
      case 'qtde': return an.qtdeDigitos || 0;
      case 'numeros': return String(an.digitosUnicos || '');
      default: return +c.contest || 0;
    }
  };

  TubularApp.prototype._visibleRows = function () {
    const chronoAsc = this._chronoAsc();
    const idxMap = new Map(chronoAsc.map((c, i) => [c.contest, i]));
    const key = this.sortKey || 'contest';
    const dir = this.sortDir === 'desc' ? -1 : 1;
    let sortedDisplay;
    if (key === 'contest') {
      sortedDisplay = dir === 1 ? chronoAsc.slice() : chronoAsc.slice().reverse();
    } else {
      const decorated = chronoAsc.map(c => ({ c, val: this._sortValue(c, chronoAsc, key, idxMap) }));
      decorated.sort((a, b) => {
        const va = a.val;
        const vb = b.val;
        if (typeof va === 'string' || typeof vb === 'string') {
          return dir * String(va).localeCompare(String(vb), 'pt-BR', { numeric: true });
        }
        return dir * ((+va || 0) - (+vb || 0));
      });
      sortedDisplay = decorated.map(x => x.c);
    }
    const size = this._effectivePageSize();
    const pages = Math.max(1, Math.ceil(sortedDisplay.length / size) || 1);
    if (this.page > pages) this.page = pages;
    const start = (this.page - 1) * size;
    return {
      chronoAsc,
      sortedAsc: chronoAsc,
      sortedDisplay,
      size,
      pages,
      start,
      rows: sortedDisplay.slice(start, start + size),
    };
  };

  TubularApp.prototype._updateSortHeaders = function () {
    const key = this.sortKey || 'contest';
    const dir = this.sortDir || 'asc';
    this.root.querySelectorAll('#tbTabela thead th.tb-sort').forEach(th => {
      const active = th.dataset.sort === key;
      th.classList.toggle('tb-sort-asc', active && dir === 'asc');
      th.classList.toggle('tb-sort-desc', active && dir === 'desc');
    });
  };

  TubularApp.prototype._qtdeClass = function (q) {
    const n = Math.min(10, Math.max(3, Number(q) || 0));
    return `tb-qtde tb-qtde-${n}`;
  };

  TubularApp.prototype._bind = function () {
    const r = this.root;
    r.querySelectorAll('[data-tb-sub]').forEach(btn => {
      btn.addEventListener('click', () => this.showSub(btn.dataset.tbSub));
    });
    r.querySelector('#tbBtnLoad')?.addEventListener('click', () => this.load());
    r.querySelector('#tbBtnMark')?.addEventListener('click', () => {
      this.marked = true;
      this.renderTable();
      this.renderManual(10);
    });
    r.querySelector('#tbBtnReset')?.addEventListener('click', () => {
      this.marked = false;
      this.renderTable();
      this.renderManual(10);
    });
    r.querySelector('#tbBtnMark10')?.addEventListener('click', () => {
      this.marked = true;
      this.renderManual(10);
      this.renderTable();
    });
    r.querySelector('#tbBtnReset10')?.addEventListener('click', () => {
      this.marked = false;
      this.renderManual(10);
      this.renderTable();
    });
    r.querySelector('#tbCondStatsToggle')?.addEventListener('click', () => this.toggleCondStats());
    r.querySelector('#tbViewDraw')?.addEventListener('click', () => this.setView('draw'));
    r.querySelector('#tbViewAsc')?.addEventListener('click', () => this.setView('asc'));
    r.querySelector('#tbPageSize')?.addEventListener('change', (e) => {
      this.pageSize = +e.target.value || 0;
      this._goLastPage();
      this.renderTable();
    });
    r.querySelector('#tbPrint')?.addEventListener('click', () => window.print());
    r.querySelector('#tbPager')?.addEventListener('click', (ev) => {
      const b = ev.target.closest('[data-page]');
      if (!b) return;
      this.page = +b.dataset.page;
      this.renderTable();
    });
    r.querySelector('#tbTabela thead')?.addEventListener('click', (ev) => {
      const th = ev.target.closest('th.tb-sort');
      if (!th || !th.dataset.sort) return;
      const key = th.dataset.sort;
      if (this.sortKey === key) {
        this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
      } else {
        this.sortKey = key;
        this.sortDir = (key === 'contest' || key === 'date' || key === 'soma' || key === 'qtde' || key.startsWith('dez'))
          ? 'desc'
          : 'asc';
        if (key === 'contest') this.sortDir = 'asc';
      }
      this.page = 1;
      this.renderTable();
    });
    ['txt', 'xlsx', 'html'].forEach(fmt => {
      r.querySelector(`#tbExport${fmt.toUpperCase()}`)?.addEventListener('click', () => this.exportMain(fmt));
    });
    r.querySelector('#tbAdd10')?.addEventListener('click', () => this.addManualRow(10));
    r.querySelector('#tbProcess10')?.addEventListener('click', () => this.processPaste(10));
    r.querySelector('#tbExport10')?.addEventListener('click', () => this.exportManualApostas(10));
    r.querySelector('#tbExport11')?.addEventListener('click', () => this.exportManualApostas(11));
    r.querySelector('#tbGerar11')?.addEventListener('click', () => this.gerarAutomatico11(10));
    r.querySelector('#tbGerarMais11')?.addEventListener('click', () => this.gerarMaisAutomatico11());
    r.querySelector('#tbClear10')?.addEventListener('click', () => {
      this.manual10 = [];
      this.manual10BlockMsg = '';
      this.manual10SortKey = null;
      this.manual10SortDir = 'asc';
      this._manualUid = 0;
      this.renderManual(10);
    });
    r.querySelector('#tbAuto11Janela')?.addEventListener('click', (ev) => {
      const btn = ev.target.closest('[data-janela]');
      if (!btn) return;
      this.auto11Janela = parseInt(btn.dataset.janela, 10);
      if (!Number.isFinite(this.auto11Janela)) this.auto11Janela = 10;
      r.querySelectorAll('#tbAuto11Janela [data-janela]').forEach(b => {
        b.classList.toggle('active', parseInt(b.dataset.janela, 10) === this.auto11Janela);
      });
      this._updateAuto11Hints();
    });
    r.querySelector('#tbAuto11SomaModo')?.addEventListener('change', (ev) => {
      const inp = ev.target.closest('input[name="tbAuto11Soma"]');
      if (!inp) return;
      this.auto11SomaModo = inp.value || 'padrao';
      this._updateAuto11Hints();
    });
    r.querySelector('#tbAuto11ParesModo')?.addEventListener('change', (ev) => {
      const inp = ev.target.closest('input[name="tbAuto11Pares"]');
      if (!inp) return;
      this.auto11ParesModo = inp.value || 'fix_4';
      this._updateAuto11Hints();
    });
    r.querySelector('#tbClear11')?.addEventListener('click', () => {
      this.manual11 = [];
      this.manual11SortKey = null;
      this.manual11SortDir = 'asc';
      this.renderManual(11);
      const info = this.root.querySelector('#tbGerar11Info');
      if (info) info.textContent = '—';
    });
    r.querySelector('#tbStats11Toggle')?.addEventListener('click', () => {
      this.stats11Open = !this.stats11Open;
      this._syncStats11Collapse();
    });
    r.querySelector('#tbConferir11')?.addEventListener('click', () => this.conferir11());
    r.querySelector('#tbConferir11Clear')?.addEventListener('click', () => this.limparConferencia11());
    r.querySelector('#tbManual10 thead')?.addEventListener('click', (ev) => {
      const th = ev.target.closest('th.tb-sort');
      if (!th || !th.dataset.sort) return;
      const key = th.dataset.sort;
      // Ciclo alinhado ao pedido: ↑ → ↓ → ordem original (classes tb-sort da aba Sequências)
      if (this.manual10SortKey === key) {
        if (this.manual10SortDir === 'asc') this.manual10SortDir = 'desc';
        else {
          this.manual10SortKey = null;
          this.manual10SortDir = 'asc';
        }
      } else {
        this.manual10SortKey = key;
        this.manual10SortDir = 'asc';
      }
      this.renderManual(10);
    });
    r.querySelector('#tbManual11 thead')?.addEventListener('click', (ev) => {
      const th = ev.target.closest('th.tb-sort');
      if (!th || !th.dataset.sort) return;
      const key = th.dataset.sort;
      if (this.manual11SortKey === key) {
        if (this.manual11SortDir === 'asc') this.manual11SortDir = 'desc';
        else {
          this.manual11SortKey = null;
          this.manual11SortDir = 'asc';
        }
      } else {
        this.manual11SortKey = key;
        this.manual11SortDir = 'asc';
      }
      this.renderManual(11);
    });
    this._setupDrop(r.querySelector('#tbDrop10'), 10);
    // Futuro: apostas do Elite
    r.addEventListener('ai-elite-compare', (ev) => {
      const jogos = (ev.detail && ev.detail.jogos) || [];
      const section = (ev.detail && ev.detail.section) === 11 ? 11 : 10;
      const parsed = jogos.map(j => {
        const L = limitsFrom(this.root);
        const numbers = Array.isArray(j) ? j.map(Number).slice(0, L.sorteadas) : parseJogosTexto(String(j), L)[0]?.numbers;
        if (!numbers || numbers.length < L.sorteadas) return null;
        return {
          numbers,
          month: this.extraMes ? 1 : 0,
          monthName: this.extraMes ? 'Janeiro' : '',
          editable: true,
          _uid: ++this._manualUid,
        };
      }).filter(Boolean);
      if (section === 10) this.manual10 = this.manual10.concat(parsed);
      else this.manual11 = this.manual11.concat(parsed);
      this.renderManual(section);
    });
    this._syncStats11Collapse();
    this._updateAuto11Hints();
  };

  TubularApp.prototype._setupDrop = function (el, section) {
    if (!el) return;
    el.addEventListener('dragover', ev => { ev.preventDefault(); el.classList.add('dragover'); });
    el.addEventListener('dragleave', () => el.classList.remove('dragover'));
    el.addEventListener('drop', ev => {
      ev.preventDefault();
      el.classList.remove('dragover');
      const f = ev.dataTransfer.files && ev.dataTransfer.files[0];
      if (f) {
        const reader = new FileReader();
        reader.onload = () => {
          const ta = this.root.querySelector(section === 10 ? '#tbPaste10' : '#tbPaste11');
          if (ta) ta.value = String(reader.result || '');
          this.processPaste(section);
        };
        reader.readAsText(f);
        return;
      }
      const text = ev.dataTransfer.getData('text/plain');
      if (text) {
        const ta = this.root.querySelector(section === 10 ? '#tbPaste10' : '#tbPaste11');
        if (ta) ta.value = text;
        this.processPaste(section);
      }
    });
  };

  TubularApp.prototype.showSub = function (key) {
    this.root.querySelectorAll('[data-tb-sub]').forEach(b => b.classList.toggle('active', b.dataset.tbSub === key));
    this.root.querySelectorAll('[data-tb-panel]').forEach(p => {
      p.classList.toggle('d-none', p.dataset.tbPanel !== key);
    });
    if ((key === 's10' || key === 's11') && !this.data.length) this.load();
    else if (key === 's10' || key === 's11') this.renderUltimo10();
    if (key === 's10') this.renderManual(10);
    if (key === 's11') {
      this._updateAuto11Hints();
      this._fillConferir11Select();
      this.renderManual(11);
    }
  };

  TubularApp.prototype.setView = function (view) {
    this.view = view;
    this.root.querySelector('#tbViewDraw')?.classList.toggle('active', view === 'draw');
    this.root.querySelector('#tbViewAsc')?.classList.toggle('active', view === 'asc');
    this.renderTable();
  };

  TubularApp.prototype.numsFor = function (c) {
    return this.view === 'draw' ? (c.numbersDrawOrder || c.numbersAscending) : (c.numbersAscending || c.numbersDrawOrder);
  };

  TubularApp.prototype.mesClass = function (name) {
    const n = String(name || '').replace(/\s+/g, '');
    return n ? `mes-nome-${n}` : '';
  };

  TubularApp.prototype.mesStyle = function (name) {
    const cor = this.mesesCores[name] || this.mesesCores[String(name || '').replace(/\s+/g, '')];
    return cor ? `background-color:${cor}` : 'background-color:#6c757d';
  };

  TubularApp.prototype._loadFaltantesCiclo = async function () {
    try {
      const r = await fetch('/analise/api/ciclo-cobertura/ciclo-atual');
      const j = await r.json();
      const dados = (j && j.dados) || j || {};
      const pend = dados.dezenas_pendentes || [];
      this.faltantesCiclo = new Set((Array.isArray(pend) ? pend : []).map(Number).filter(Number.isFinite));
    } catch (_) {
      this.faltantesCiclo = new Set();
    }
  };

  /** Hit-set do último concurso carregado (Seção 10 — comparar com a prévia). */
  TubularApp.prototype._ultimoHitSet = function () {
    const chrono = this._chronoAsc();
    if (!chrono.length) return null;
    const nums = chrono[chrono.length - 1].numbersAscending || [];
    return nums.length ? new Set(nums.map(Number)) : null;
  };

  TubularApp.prototype._acertosSpan = function (acertos, title) {
    if (acertos == null) return '—';
    const n = Number(acertos);
    let tier = 'tb-ac-0';
    if (n >= 7) tier = 'tb-ac-7';
    else if (n >= 6) tier = 'tb-ac-6';
    else if (n >= 5) tier = 'tb-ac-5';
    else if (n >= 4) tier = 'tb-ac-4';
    else if (n >= 3) tier = 'tb-ac-3';
    else if (n >= 1) tier = 'tb-ac-low';
    return `<span class="tb-acertos ${tier}" title="${esc(title || `${n} acertos`)}">${n}</span>`;
  };

  TubularApp.prototype.load = async function () {
    const st = this.root.querySelector('#tbStatus');
    const stMini = this.root.querySelector('#tbStatusMini');
    if (st) st.textContent = 'Carregando…';
    if (stMini) stMini.textContent = 'Carregando…';
    try {
      const [r] = await Promise.all([
        fetch(`${this.api}/tubular?base=geral`),
        this._loadFaltantesCiclo(),
      ]);
      const j = await r.json();
      if (!j.sucesso) throw new Error(j.erro || 'Falha');
      this.data = (j.sorteios || []).map(s => {
        const asc = (s.listaDezenas || []).map(Number);
        const draw = (s.ordem_caixa || asc).map(Number);
        let mesNum = 0;
        let mesNome = '';
        if (this.extraMes) {
          mesNum = s.mesSorte || s.mes_num || 0;
          mesNome = s.mesSorteNome || s.nomeMesSorte || (mesNum ? (MESES[mesNum - 1] || '') : '') || '';
        }
        return {
          contest: s.concurso || s.numero,
          date: s.data || s.dataApuracao || '',
          numbersAscending: asc,
          numbersDrawOrder: draw,
          month: mesNum,
          monthName: mesNome,
        };
      });
      this._goLastPage();
      this.renderKpis();
      this.renderCondStats();
      this.renderTable();
      this.renderUltimo10();
      this.renderManual(10);
      this._fillConferir11Select();
      const statusTxt = this.data.length
        ? `${this.data[0].contest} → ${this.data[this.data.length - 1].contest} (${this.data.length})`
        : 'Sem dados';
      if (st) st.textContent = statusTxt;
      if (stMini) stMini.textContent = statusTxt;
    } catch (e) {
      if (st) st.textContent = 'Erro ao carregar';
      if (stMini) stMini.textContent = 'Erro ao carregar';
      alert(e.message || e);
    }
  };

  TubularApp.prototype.toggleCondStats = function () {
    const btn = this.root.querySelector('#tbCondStatsToggle');
    const body = this.root.querySelector('#tbCondStatsBody');
    if (!btn || !body) return;
    const open = btn.getAttribute('aria-expanded') === 'true';
    btn.setAttribute('aria-expanded', open ? 'false' : 'true');
    body.classList.toggle('d-none', open);
  };

  TubularApp.prototype.computeConditionStats = function () {
    const sorted = [...this.data].sort((a, b) => a.contest - b.contest);
    const total = sorted.length;
    const counts = {
      seq2: 0,
      seq3: 0,
      seq4: 0,
      repetition: 0,
      seq2Rep: 0,
      seq432: 0,
    };
    sorted.forEach((c, i) => {
      const nums = c.numbersAscending || this.numsFor(c);
      const prev = i > 0 ? (sorted[i - 1].numbersAscending || this.numsFor(sorted[i - 1])) : [];
      const sequences = analyzeSequences(nums);
      const rept = calculateRepetitions(nums, prev);
      const hasSeq2 = sequences.some(s => s.length === 2);
      const hasSeq3 = sequences.some(s => s.length === 3);
      const hasSeq4 = sequences.some(s => s.length >= 4);
      const hasRept = rept.count > 0;
      if (hasSeq2) counts.seq2++;
      if (hasSeq3) counts.seq3++;
      if (hasSeq4) counts.seq4++;
      if (hasRept) counts.repetition++;
      let has2R = false;
      nums.forEach(n => {
        const cond = detectAllConditions(n, sequences, rept.list);
        if (cond.includes('seq-2') && cond.includes('repetition')) has2R = true;
      });
      if (has2R) counts.seq2Rep++;
      if (hasSeq2 && hasSeq3 && hasSeq4) counts.seq432++;
    });
    return { total, counts };
  };

  TubularApp.prototype.renderCondStats = function () {
    const tbody = this.root.querySelector('#tbCondStatsTable tbody');
    const meta = this.root.querySelector('#tbCondStatsMeta');
    if (!tbody) return;
    const { total, counts } = this.computeConditionStats();
    if (meta) meta.textContent = total ? `· ${total} concursos` : '';
    if (!total) {
      tbody.innerHTML = '<tr><td colspan="4" class="text-muted">Carregue os dados do banco local</td></tr>';
      return;
    }
    const pct = (n) => ((100 * n) / total).toFixed(1).replace('.', ',') + '%';
    const rows = [
      {
        swatch: '<div class="tb-swatch seq-2">2</div>',
        name: 'Sequência de 2',
        n: counts.seq2,
      },
      {
        swatch: '<div class="tb-swatch seq-3">3</div>',
        name: 'Sequência de 3',
        n: counts.seq3,
      },
      {
        swatch: '<div class="tb-swatch seq-4">4+</div>',
        name: 'Sequência de 4+',
        n: counts.seq4,
      },
      {
        swatch: '<div class="tb-swatch repetition">R</div>',
        name: 'Repetição',
        n: counts.repetition,
      },
      {
        swatch: '<div class="tb-swatch-grad" style="background:linear-gradient(135deg,var(--cor-sequencia-1) 0%,var(--cor-sequencia-1) 50%,var(--cor-repetidos) 50%,var(--cor-repetidos) 100%);color:var(--cor-sequencia-1-texto)">2+R</div>',
        name: 'Seq. 2 + Repetição',
        n: counts.seq2Rep,
      },
      {
        swatch: '<div class="tb-swatch-grad" style="background:linear-gradient(135deg,var(--cor-sequencia-3) 0%,var(--cor-sequencia-3) 33%,var(--cor-sequencia-2) 33%,var(--cor-sequencia-2) 66%,var(--cor-sequencia-1) 66%,var(--cor-sequencia-1) 100%);color:var(--cor-sequencia-3-texto)">4+3+2</div>',
        name: 'Seq. 4+ + Seq. 3 + Seq. 2',
        n: counts.seq432,
      },
    ];
    tbody.innerHTML = rows.map(r => `
      <tr>
        <td>${r.swatch}</td>
        <td class="tb-cond-name">${esc(r.name)}</td>
        <td><strong>${r.n}</strong></td>
        <td>${pct(r.n)}</td>
      </tr>`).join('');
  };

  TubularApp.prototype.renderKpis = function () {
    const box = this.root.querySelector('#tbKpis');
    if (!box) return;
    const sorted = [...this.data].sort((a, b) => a.contest - b.contest);
    let comRept = 0, comSeq = 0;
    sorted.forEach((c, i) => {
      const nums = this.numsFor(c);
      const prev = i > 0 ? this.numsFor(sorted[i - 1]) : [];
      if (calculateRepetitions(nums, prev).count > 0) comRept++;
      if (analyzeSequences(nums).length) comSeq++;
    });
    const pct = this.data.length ? ((100 * comRept) / this.data.length).toFixed(1) : '0';
    box.innerHTML = `
      <div class="tb-kpi tb-kpi-gold"><div class="v">${this.data.length}</div><div class="l">Total Concursos</div></div>
      <div class="tb-kpi tb-kpi-green"><div class="v">${comRept}</div><div class="l">Com Repetição</div></div>
      <div class="tb-kpi tb-kpi-blue"><div class="v">${comSeq}</div><div class="l">Com Sequência</div></div>
      <div class="tb-kpi tb-kpi-red"><div class="v">${pct}%</div><div class="l">% Repetição Entre Jogos</div></div>`;
  };

  TubularApp.prototype._cellNum = function (n, sequences, reps, hitSet) {
    const cond = this.marked ? detectAllConditions(n, sequences, reps) : [];
    const style = this.marked ? createGradientStyle(cond) : { background: '', title: '' };
    const hit = hitSet && hitSet.has(Number(n));
    const cls = `${cond.join(' ')}${hit ? ' tb-hit' : ''}`.trim();
    const inline = (!hit && style.background) ? `style="${style.background}"` : '';
    const title = hit
      ? `${fmt2(n)} — acerto`
      : (style.title || fmt2(n));
    return `<span class="number-cell tb-number ${esc(cls)}" ${inline} title="${esc(title)}">${fmt2(n)}</span>`;
  };

  /** Números da aposta na ordem de exibição da Seção 10 (crescente) / 11 (sorteio). */
  TubularApp.prototype._manualNumsDisplay = function (g, mode, L) {
    let nums = (g.numbers || []).map(n => (n === '' || n == null ? null : Number(n)));
    if (mode === 'asc') {
      const filled = nums.filter(n => n != null && Number.isFinite(n) && n >= L.dezenaMin && n <= L.dezenaMax)
        .sort((a, b) => a - b);
      nums = filled.slice();
    }
    while (nums.length < L.sorteadas) nums.push(null);
    return nums.slice(0, L.sorteadas);
  };

  /** HTML da coluna Dezenas — Seção 10: P1–P7 com spinner (labels só no aria; seleção = faltantes do ciclo). */
  TubularApp.prototype._manualPosControlsHtml = function (section, rowIdx, nums, sequences, reps, L, dupCols, hitSet) {
    const dups = dupCols || new Set();
    const hits = hitSet || null;
    const falt = this.faltantesCiclo || new Set();
    return `<div class="tb-pos-row">${nums.map((n, k) => {
      const pos = `P${k + 1}`;
      const isHit = hits && n != null && hits.has(Number(n));
      const isFalt = this.marked && n != null && !dups.has(k) && !isHit && falt.has(Number(n));
      const cond = (this.marked && n != null && !dups.has(k) && !isHit)
        ? detectAllConditions(n, sequences || [], reps || [])
        : [];
      const style = (this.marked && n != null && !dups.has(k) && !isHit && !isFalt)
        ? createGradientStyle(cond)
        : { background: '', title: '' };
      const cls = [
        cond.join(' '),
        isHit ? 'tb-hit' : '',
        isFalt ? 'tb-faltante' : '',
        dups.has(k) ? 'tb-pos-dup' : '',
      ].filter(Boolean).join(' ');
      const inline = style.background ? `style="${style.background}"` : '';
      let title;
      if (dups.has(k)) title = `${pos}: ${fmt2(n)} — dezena repetida nesta aposta`;
      else if (isHit) title = `${pos}: ${fmt2(n)} — acerto (último concurso)`;
      else if (isFalt) title = `${pos}: ${fmt2(n)} — faltante do ciclo`;
      else title = style.title || `${pos}: ${n == null ? '—' : fmt2(n)}`;
      const val = n == null || n === '' ? '' : fmt2(n);
      return `<div class="tb-pos-ctrl" title="${esc(title)}">
        <div class="tb-pos-box ${esc(cls)}" ${inline}>
          <input class="tb-manual-input" data-sec="${section}" data-row="${rowIdx}" data-col="${k}"
            value="${val}" maxlength="2" inputmode="numeric" pattern="[0-9]{1,2}"
            aria-label="${pos}" title="${esc(title)}">
          <span class="tb-pos-spin" aria-hidden="true">
            <button type="button" class="tb-pos-btn tb-pos-up" data-sec="${section}" data-row="${rowIdx}" data-col="${k}" data-delta="1" tabindex="-1" aria-label="Aumentar ${pos}">▲</button>
            <button type="button" class="tb-pos-btn tb-pos-dn" data-sec="${section}" data-row="${rowIdx}" data-col="${k}" data-delta="-1" tabindex="-1" aria-label="Diminuir ${pos}">▼</button>
          </span>
        </div>
      </div>`;
    }).join('')}</div>`;
  };

  /** Detecta dezenas repetidas dentro de uma aposta (só entre P1–P7 da mesma linha). */
  TubularApp.prototype._manualDupInfo = function (nums) {
    const map = {};
    (nums || []).forEach((n, i) => {
      if (n == null || n === '') return;
      const k = Number(n);
      if (!Number.isFinite(k)) return;
      if (!map[k]) map[k] = [];
      map[k].push(i);
    });
    const dupCols = new Set();
    const messages = [];
    Object.keys(map).forEach((dez) => {
      const cols = map[dez];
      if (cols.length < 2) return;
      cols.forEach(c => dupCols.add(c));
      const pos = cols.map(c => `P${c + 1}`).join(' e ');
      messages.push(`Dezena ${fmt2(dez)} repetida em ${pos}.`);
    });
    return { dupCols, messages, hasDup: dupCols.size > 0 };
  };

  TubularApp.prototype._wouldManualDup = function (nums, col, val) {
    if (val == null || val === '') return false;
    const v = Number(val);
    if (!Number.isFinite(v)) return false;
    return (nums || []).some((n, i) => i !== col && n != null && n !== '' && Number(n) === v);
  };

  /** Atualiza posição Pk da aposta (grava array na ordem de exibição). Bloqueia duplicata na Seção 10. */
  TubularApp.prototype._setManualPos = function (sec, row, col, nextVal, L) {
    const arr = sec === 10 ? this.manual10 : this.manual11;
    if (!arr[row]) return false;
    const mode = sec === 10 ? 'asc' : 'draw';
    const nums = this._manualNumsDisplay(arr[row], mode, L);
    let value = nextVal;
    if (value === null || value === '') {
      nums[col] = null;
    } else {
      let v = Math.trunc(Number(value));
      if (!Number.isFinite(v)) {
        nums[col] = null;
      } else {
        v = Math.min(L.dezenaMax, Math.max(L.dezenaMin, v));
        if (sec === 10 && this._wouldManualDup(nums, col, v)) {
          const other = nums.findIndex((n, i) => i !== col && n != null && Number(n) === v);
          const aposta = arr[row]._uid != null ? arr[row]._uid : (row + 1);
          this.manual10BlockMsg =
            `Dezena repetida na aposta ${aposta}: ${fmt2(v)} já está em P${other + 1}.`;
          return false;
        }
        nums[col] = v;
      }
    }
    arr[row].numbers = nums;
    if (sec === 10) this.manual10BlockMsg = '';
    return true;
  };

  TubularApp.prototype._manualSortValue = function (g, key, origIdx, L, last, hitSet) {
    const nums = this._manualNumsDisplay(g, 'asc', L);
    const valid = nums.filter(n => n != null && n >= L.dezenaMin && n <= L.dezenaMax);
    const uniqueOk = !this._manualDupInfo(nums).hasDup;
    const an = (valid.length === L.sorteadas && uniqueOk)
      ? calculateCompleteAnalysis(valid, g.monthName)
      : null;
    const rept = (valid.length === L.sorteadas && uniqueOk)
      ? calculateRepetitions(valid, last)
      : { list: [] };
    switch (key) {
      case 'idx': return g._uid != null ? g._uid : origIdx;
      case 'dezenas': return valid.map(fmt2).join(' ') || '';
      case 'mes': {
        const nome = String(g.monthName || '');
        const idx = MESES.indexOf(nome);
        if (idx >= 0) return idx;
        if (g.month != null && g.month >= 1 && g.month <= 12) return g.month - 1;
        return 99;
      }
      case 'seq': return an ? (an.sequencesInfo.qtde || 0) : -1;
      case 'finais': return an ? (an.finaisIguais.qtde || 0) : -1;
      case 'rept': return (rept.list || []).length;
      case 'soma': return an ? an.soma : -1;
      case 'pares': return an ? an.pares : -1;
      case 'impares': return an ? an.impares : -1;
      case 'inicial': return an ? String(an.padroes.inicial || '') : '';
      case 'final': return an ? String(an.padroes.final || '') : '';
      case 'qtde': return an ? an.qtdeDigitos : -1;
      case 'numeros': return an ? String(an.digitosUnicos || '') : '';
      case 'acertos': {
        if (!hitSet || !hitSet.size) return -1;
        return valid.filter(n => hitSet.has(Number(n))).length;
      }
      default: return g._uid != null ? g._uid : origIdx;
    }
  };

  TubularApp.prototype._orderedManual10 = function (list, L, last) {
    return this._orderedManualList(list, L, last, this.manual10SortKey, this.manual10SortDir, this._ultimoHitSet());
  };

  TubularApp.prototype._orderedManual11 = function (list, L, last) {
    const hitSet = (this.conferencia11 && this.conferencia11.nums)
      ? new Set(this.conferencia11.nums.map(Number))
      : null;
    return this._orderedManualList(list, L, last, this.manual11SortKey, this.manual11SortDir, hitSet);
  };

  TubularApp.prototype._orderedManualList = function (list, L, last, sortKey, sortDir, hitSet) {
    const idxs = list.map((_, i) => i);
    const key = sortKey;
    if (!key) {
      return idxs.sort((a, b) => {
        const ua = list[a]._uid != null ? list[a]._uid : a;
        const ub = list[b]._uid != null ? list[b]._uid : b;
        return ua - ub;
      });
    }
    const dir = sortDir === 'desc' ? -1 : 1;
    return idxs.sort((a, b) => {
      const va = this._manualSortValue(list[a], key, a, L, last, hitSet);
      const vb = this._manualSortValue(list[b], key, b, L, last, hitSet);
      if (typeof va === 'string' || typeof vb === 'string') {
        return dir * String(va).localeCompare(String(vb), 'pt-BR', { numeric: true });
      }
      return dir * ((+va || 0) - (+vb || 0));
    });
  };

  TubularApp.prototype._updateManual10SortHeaders = function () {
    this._updateManualSortHeaders('#tbManual10', this.manual10SortKey, this.manual10SortDir);
  };

  TubularApp.prototype._updateManual11SortHeaders = function () {
    this._updateManualSortHeaders('#tbManual11', this.manual11SortKey, this.manual11SortDir);
  };

  TubularApp.prototype._updateManualSortHeaders = function (tableSel, sortKey, sortDir) {
    const key = sortKey;
    const dir = sortDir || 'asc';
    this.root.querySelectorAll(`${tableSel} thead th.tb-sort`).forEach(th => {
      const active = !!key && th.dataset.sort === key;
      th.classList.toggle('tb-sort-asc', active && dir === 'asc');
      th.classList.toggle('tb-sort-desc', active && dir === 'desc');
      const ind = th.querySelector('.tb-sort-ind');
      if (ind) ind.textContent = active ? (dir === 'asc' ? '↑' : '↓') : '⇅';
    });
  };

  TubularApp.prototype._syncStats11Collapse = function () {
    const btn = this.root.querySelector('#tbStats11Toggle');
    const body = this.root.querySelector('#tbStats11Body');
    if (!btn || !body) return;
    const open = !!this.stats11Open;
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    body.classList.toggle('d-none', !open);
  };

  /** Select de concursos já apurados (dados tubulares carregados). */
  TubularApp.prototype._fillConferir11Select = function () {
    const sel = this.root.querySelector('#tbConferir11Select');
    if (!sel) return;
    const prev = sel.value;
    const chrono = this.data.slice().sort((a, b) => (+b.contest || 0) - (+a.contest || 0));
    const opts = ['<option value="">— concurso apurado —</option>'];
    chrono.forEach((c) => {
      const nums = (c.numbersAscending || c.numbersDrawOrder || []).map(Number).filter(Number.isFinite);
      const label = `${c.contest} — ${nums.map(fmt2).join(' ')}${c.monthName ? ` (${c.monthName})` : ''}`;
      opts.push(`<option value="${esc(String(c.contest))}">${esc(label)}</option>`);
    });
    sel.innerHTML = opts.join('');
    if (prev && [...sel.options].some(o => o.value === prev)) sel.value = prev;
    else if (this.conferencia11) sel.value = String(this.conferencia11.contest);
  };

  TubularApp.prototype.conferir11 = function () {
    const sel = this.root.querySelector('#tbConferir11Select');
    const info = this.root.querySelector('#tbConferir11Info');
    const contest = sel ? String(sel.value || '').trim() : '';
    if (!contest) {
      alert('Selecione um concurso apurado para conferir.');
      return;
    }
    if (!this.data.length) {
      alert('Carregue os dados antes de conferir.');
      return;
    }
    const c = this.data.find(x => String(x.contest) === contest);
    if (!c) {
      alert('Concurso não encontrado nos resultados carregados.');
      return;
    }
    const nums = (c.numbersAscending || c.numbersDrawOrder || []).map(Number).filter(Number.isFinite);
    this.conferencia11 = { contest: c.contest, nums };
    this.renderManual(11);
    if (info) {
      info.textContent = `Concurso ${c.contest}: ${nums.map(fmt2).join(' ')} — dezenas acertadas em verde`;
    }
  };

  TubularApp.prototype.limparConferencia11 = function () {
    this.conferencia11 = null;
    const sel = this.root.querySelector('#tbConferir11Select');
    const info = this.root.querySelector('#tbConferir11Info');
    if (sel) sel.value = '';
    if (info) info.textContent = 'Selecione um concurso e clique em Conferir';
    this.renderManual(11);
  };

  TubularApp.prototype._renderManual10DupMsg = function (alerts) {
    const el = this.root.querySelector('#tbDupMsg10');
    if (!el) return;
    const parts = [];
    if (this.manual10BlockMsg) parts.push(this.manual10BlockMsg);
    (alerts || []).forEach(a => parts.push(a));
    if (!parts.length) {
      el.classList.add('d-none');
      el.innerHTML = '';
      return;
    }
    el.classList.remove('d-none');
    el.innerHTML = parts.map(m => `<div>⚠ ${esc(m)}</div>`).join('');
  };

  TubularApp.prototype._renderFaltantesHint = function () {
    const el = this.root.querySelector('#tbFaltantesHint10');
    if (!el) return;
    const n = this.faltantesCiclo ? this.faltantesCiclo.size : 0;
    if (!n) {
      el.classList.add('d-none');
      el.textContent = '';
      return;
    }
    const sample = [...this.faltantesCiclo].sort((a, b) => a - b).slice(0, 16).map(fmt2).join(' ');
    el.classList.remove('d-none');
    el.innerHTML = this.marked
      ? `Seleção (laranja): <strong>${n} faltantes do ciclo</strong> · ${esc(sample)}${n > 16 ? '…' : ''} · acertos em verde vs último`
      : `Ciclo: <strong>${n} faltantes</strong> · use «Marcar» para destacar na grade`;
  };

  TubularApp.prototype.renderTable = function () {
    const tbody = this.root.querySelector('#tbTabela tbody');
    if (!tbody) return;
    const { chronoAsc, sortedAsc, size, pages, start, rows } = this._visibleRows();
    this._updateSortHeaders();
    const idxMap = new Map(chronoAsc.map((c, i) => [c.contest, i]));

    // Ranking sutil dos padrões de dígitos únicos (mais frequente = 1º)
    const freqDig = {};
    chronoAsc.forEach(c => {
      const key = calculateCompleteAnalysis(this.numsFor(c), c.monthName).digitosUnicos;
      freqDig[key] = (freqDig[key] || 0) + 1;
    });
    const ranked = Object.entries(freqDig).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    const rankMap = {};
    ranked.forEach(([key], i) => { rankMap[key] = i + 1; });

    tbody.innerHTML = rows.map(c => {
      const nums = this.numsFor(c);
      const idx = idxMap.has(c.contest) ? idxMap.get(c.contest) : -1;
      const prev = idx > 0 ? this.numsFor(chronoAsc[idx - 1]) : [];
      const an = calculateCompleteAnalysis(nums, c.monthName);
      const rept = calculateRepetitions(nums, prev);
      const seqEmoji = getEmojiByCount(an.sequencesInfo.qtde);
      const finEmoji = getEmojiByCount(an.finaisIguais.qtde);
      const tds = nums.map((n, i) => {
        const edge = i === 0 ? ' tb-dez-first' : (i === nums.length - 1 ? ' tb-dez-last' : '');
        return `<td class="tb-dez${edge}">${this._cellNum(n, an.sequences, rept.list)}</td>`;
      }).join('');
      const pad = Array.from({ length: Math.max(0, limitsFrom(this.root).sorteadas - nums.length) }, (_, i) => {
        const abs = nums.length + i;
        const lastIdx = limitsFrom(this.root).sorteadas - 1;
        const edge = abs === 0 ? ' tb-dez-first' : (abs === lastIdx ? ' tb-dez-last' : '');
        return `<td class="tb-dez${edge}">—</td>`;
      }).join('');
      const qCls = this._qtdeClass(an.qtdeDigitos);
      const rank = rankMap[an.digitosUnicos] || 0;
      const rankHtml = rank
        ? `<span class="tb-rank${rank <= 3 ? ` tb-rank-${rank}` : ''}" data-rank="${rank}" title="Classificação do padrão de dígitos únicos: ${rank}º lugar (${freqDig[an.digitosUnicos]}x)">${rank}º</span>`
        : '';
      const mesTd = this.extraMes
        ? `<td><span class="mes-cor ${esc(this.mesClass(c.monthName))}" style="${this.mesStyle(c.monthName)}">${esc((c.monthName || '—').slice(0, 3).toUpperCase())}</span></td>`
        : '';
      return `<tr>
        <td><strong>${esc(c.contest)}</strong></td>
        <td class="small">${esc(c.date)}</td>
        ${tds}${pad}
        ${mesTd}
        <td title="${esc(an.sequencesInfo.quais)}">${seqEmoji.text}</td>
        <td title="${esc(an.finaisIguais.quais)}">${finEmoji.text}</td>
        <td title="${esc(rept.title)}">${rept.text}</td>
        <td class="tb-align-mono"><span class="tb-mono tb-mono-soma">${String(an.soma).padStart(3, ' ')}</span></td>
        <td>${an.pares}</td>
        <td>${an.impares}</td>
        <td class="tb-align-mono"><span class="tb-mono">${esc(an.padroes.inicial)}</span></td>
        <td class="tb-align-mono"><span class="tb-mono">${esc(an.padroes.final)}</span></td>
        <td><span class="${qCls}" title="Dígitos únicos: ${an.qtdeDigitos}">${an.qtdeDigitos}</span></td>
        <td class="tb-align-mono"><span class="tb-mono tb-mono-digs">${esc(an.digitosUnicos)}</span>${rankHtml}</td>
      </tr>`;
    }).join('') || `<tr><td colspan="${2 + limitsFrom(this.root).sorteadas + (this.extraMes ? 1 : 0) + 10}" class="text-muted py-4">Carregue os dados do banco local</td></tr>`;

    this._appendStats(tbody, sortedAsc);
    this._renderPager(sortedAsc.length, pages, start, size);
  };

  TubularApp.prototype._appendStats = function (tbody, sortedAsc) {
    if (!sortedAsc.length) return;
    const nSorteadas = limitsFrom(this.root).sorteadas;
    const cols = {
      concurso: [],
      num: Array.from({ length: nSorteadas }, () => []),
      mes: [],
      seq: [], finais: [], rept: [],
      soma: [], pares: [], impares: [], inicial: [], final: [], qtde: [], numeros: [],
    };
    sortedAsc.forEach((c, i) => {
      const nums = this.numsFor(c);
      const prev = i > 0 ? this.numsFor(sortedAsc[i - 1]) : [];
      const an = calculateCompleteAnalysis(nums, c.monthName);
      const rept = calculateRepetitions(nums, prev);
      cols.concurso.push(c.contest);
      for (let k = 0; k < nSorteadas; k++) cols.num[k].push(nums[k]);
      if (this.extraMes) cols.mes.push(c.monthName);
      cols.seq.push(getEmojiByCount(an.sequencesInfo.qtde).text);
      cols.finais.push(getEmojiByCount(an.finaisIguais.qtde).text);
      cols.rept.push(rept.text);
      cols.soma.push(an.soma);
      cols.pares.push(an.pares);
      cols.impares.push(an.impares);
      cols.inicial.push(an.padroes.inicial);
      cols.final.push(an.padroes.final);
      cols.qtde.push(an.qtdeDigitos);
      cols.numeros.push(an.digitosUnicos);
    });
    const pack = (label, getter) => ([
      label,
      '',
      ...cols.num.map((arr) => {
        const v = getter(arr);
        if (v === '-' || v == null || v === '') return '-';
        const n = Number(v);
        return Number.isFinite(n) ? fmt2(n) : String(v);
      }),
      ...(this.extraMes ? [getter(cols.mes)] : []),
      getter(cols.seq),
      getter(cols.finais),
      getter(cols.rept),
      getter(cols.soma),
      getter(cols.pares),
      getter(cols.impares),
      getter(cols.inicial),
      getter(cols.final),
      getter(cols.qtde),
      getter(cols.numeros),
    ]);
    const mkRow = (cls, label, getter) => {
      const vals = pack(label, getter);
      const tr = document.createElement('tr');
      tr.className = `statistical-row ${cls}`;
      tr.innerHTML = vals.map((v, i) => `<td title="${esc(String(v))}">${i === 0 ? label : esc(String(v ?? '-'))}</td>`).join('');
      tbody.appendChild(tr);
    };
    mkRow('statistical-most', 'MAIS', modeFreq);
    mkRow('statistical-least', 'MENOS', leastFreq);
    mkRow('statistical-avg', 'MÉDIA', (arr) => {
      if (!arr.length) return '-';
      if (typeof arr[0] === 'number' || !isNaN(Number(arr[0]))) return avgNum(arr);
      return modeFreq(arr);
    });
  };

  TubularApp.prototype._renderPager = function (total, pages, start, size) {
    const el = this.root.querySelector('#tbPager');
    if (!el) return;
    if (!total) { el.innerHTML = ''; return; }
    const pageSize = size || this._effectivePageSize();
    const de = start + 1;
    const ate = Math.min(start + pageSize, total);
    el.innerHTML = `
      <button type="button" class="btn btn-sm btn-outline-secondary" data-page="1" ${this.page<=1?'disabled':''}>«</button>
      <button type="button" class="btn btn-sm btn-outline-secondary" data-page="${this.page-1}" ${this.page<=1?'disabled':''}>‹</button>
      <span class="small fw-semibold text-muted px-2">Pág. ${this.page}/${pages} · ${de}–${ate} de ${total}</span>
      <button type="button" class="btn btn-sm btn-outline-secondary" data-page="${this.page+1}" ${this.page>=pages?'disabled':''}>›</button>
      <button type="button" class="btn btn-sm btn-outline-secondary" data-page="${pages}" ${this.page>=pages?'disabled':''}>»</button>`;
  };

  TubularApp.prototype.addManualRow = function (section) {
    const L = limitsFrom(this.root);
    const row = {
      numbers: Array.from({ length: L.sorteadas }, () => null),
      month: this.extraMes ? 1 : 0,
      monthName: this.extraMes ? 'Janeiro' : '',
      editable: true,
      _uid: ++this._manualUid,
    };
    if (section === 10) this.manual10.push(row);
    else this.manual11.push(row);
    this.renderManual(section);
  };

  TubularApp.prototype.processPaste = function (section) {
    const ta = this.root.querySelector(section === 10 ? '#tbPaste10' : '#tbPaste11');
    const parsed = parseJogosTexto(ta?.value || '').map(p => ({
      ...p,
      editable: true,
      _uid: ++this._manualUid,
    }));
    if (section === 10) this.manual10 = this.manual10.concat(parsed);
    else this.manual11 = this.manual11.concat(parsed);
    this.renderManual(section);
  };

  TubularApp.prototype.renderUltimo10 = function () {
    // Mesma prévia reutilizada na Seção 10 e Seção 11
    this._fillUltimoPreview('#tbUltimo10', '#tbUltimo10Lbl');
    this._fillUltimoPreview('#tbUltimo11', '#tbUltimo11Lbl');
  };

  TubularApp.prototype._fillUltimoPreview = function (tbodySel, lblSel) {
    const tbody = this.root.querySelector(`${tbodySel} tbody`);
    const lbl = this.root.querySelector(lblSel);
    if (!tbody) return;
    const L = limitsFrom(this.root);
    const nCols = 2 + L.sorteadas + (this.extraMes ? 1 : 0) + 10;
    if (!this.data.length) {
      tbody.innerHTML = `<tr><td colspan="${nCols}" class="text-muted">Carregando histórico tubular…</td></tr>`;
      if (lbl) lbl.textContent = 'Último resultado (referência)';
      return;
    }
    const chrono = this.data.slice().sort((a, b) => (+a.contest || 0) - (+b.contest || 0));
    const c = chrono[chrono.length - 1];
    const prev = chrono.length > 1 ? chrono[chrono.length - 2] : null;
    const nums = (c.numbersAscending || c.numbersDrawOrder || []).map(Number);
    const prevNums = prev ? (prev.numbersAscending || prev.numbersDrawOrder || []).map(Number) : [];
    const an = calculateCompleteAnalysis(nums, c.monthName);
    const rept = calculateRepetitions(nums, prevNums);
    const seqEmoji = getEmojiByCount(an.sequencesInfo.qtde);
    const finEmoji = getEmojiByCount(an.finaisIguais.qtde);
    const qCls = this._qtdeClass(an.qtdeDigitos);
    const tds = nums.map((n, i) => {
      const edge = i === 0 ? ' tb-dez-first' : (i === nums.length - 1 ? ' tb-dez-last' : '');
      return `<td class="tb-dez${edge}">${this._cellNum(n, an.sequences, rept.list)}</td>`;
    }).join('');
    const pad = Array.from({ length: Math.max(0, L.sorteadas - nums.length) }, (_, i) => {
      const abs = nums.length + i;
      const lastIdx = L.sorteadas - 1;
      const edge = abs === 0 ? ' tb-dez-first' : (abs === lastIdx ? ' tb-dez-last' : '');
      return `<td class="tb-dez${edge}">—</td>`;
    }).join('');
    const mesTd = this.extraMes
      ? `<td><span class="mes-cor ${esc(this.mesClass(c.monthName))}" style="${this.mesStyle(c.monthName)}">${esc((c.monthName || '—').slice(0, 3).toUpperCase())}</span></td>`
      : '';
    if (lbl) {
      lbl.textContent = `Último resultado — concurso ${c.contest} (ordem crescente · histórico tubular)`;
    }
    tbody.innerHTML = `<tr class="tb-row-ultimo">
      <td><strong>${esc(c.contest)}</strong></td>
      <td class="small">${esc(c.date)}</td>
      ${tds}${pad}
      ${mesTd}
      <td title="${esc(an.sequencesInfo.quais)}">${seqEmoji.text}</td>
      <td title="${esc(an.finaisIguais.quais)}">${finEmoji.text}</td>
      <td title="${esc(rept.title)}">${rept.text}</td>
      <td class="tb-align-mono"><span class="tb-mono tb-mono-soma">${String(an.soma).padStart(3, ' ')}</span></td>
      <td>${an.pares}</td>
      <td>${an.impares}</td>
      <td class="tb-align-mono"><span class="tb-mono">${esc(an.padroes.inicial)}</span></td>
      <td class="tb-align-mono"><span class="tb-mono">${esc(an.padroes.final)}</span></td>
      <td><span class="${qCls}" title="Dígitos únicos: ${an.qtdeDigitos}">${an.qtdeDigitos}</span></td>
      <td class="tb-align-mono"><span class="tb-mono tb-mono-digs">${esc(an.digitosUnicos)}</span></td>
    </tr>`;
  };

  TubularApp.prototype.renderManual = function (section) {
    const list = section === 10 ? this.manual10 : this.manual11;
    const tbody = this.root.querySelector(section === 10 ? '#tbManual10 tbody' : '#tbManual11 tbody');
    const statsEl = this.root.querySelector(section === 10 ? '#tbStats10' : '#tbStats11');
    if (!tbody) return;
    if (section === 10) {
      this.renderUltimo10();
      this._updateManual10SortHeaders();
    }
    if (section === 11) {
      this.renderUltimo10();
      this._updateManual11SortHeaders();
      this._syncStats11Collapse();
    }
    const L = limitsFrom(this.root);
    const mode = 'asc';
    const chrono = this.data.slice().sort((a, b) => (+a.contest || 0) - (+b.contest || 0));
    const last = chrono.length
      ? (chrono[chrono.length - 1].numbersAscending || [])
      : [];
    const hitSet = section === 11
      ? ((this.conferencia11 && this.conferencia11.nums)
        ? new Set(this.conferencia11.nums.map(Number))
        : null)
      : this._ultimoHitSet();

    const order = section === 10
      ? this._orderedManual10(list, L, last)
      : this._orderedManual11(list, L, last);

    const alertMsgs = [];
    let sumAcertos = 0;
    let nComAcertos = 0;
    const emptyCols = section === 10
      ? (14 + (this.extraMes ? 1 : 0))
      : (13 + (this.extraMes ? 1 : 0));
    tbody.innerHTML = order.map((origIdx) => {
      const g = list[origIdx];
      const i = origIdx;
      const apostaNum = (g && g._uid != null) ? g._uid : (origIdx + 1);
      const nums = this._manualNumsDisplay(g, mode, L);
      const dup = this._manualDupInfo(nums);
      if (section === 10 && dup.hasDup) {
        dup.messages.forEach(m => alertMsgs.push(`Aposta ${apostaNum}: ${m}`));
      }
      const valid = nums.filter(n => n != null && n >= L.dezenaMin && n <= L.dezenaMax);
      const completeOk = valid.length === L.sorteadas && !dup.hasDup;
      const an = completeOk ? calculateCompleteAnalysis(valid, g.monthName) : null;
      const rept = completeOk ? calculateRepetitions(valid, last) : { text: '—', list: [] };
      const qCls = an ? this._qtdeClass(an.qtdeDigitos) : '';
      const sequences = an ? an.sequences : [];
      const repsList = rept.list || [];
      const acertos = hitSet
        ? valid.filter(n => hitSet.has(Number(n))).length
        : null;
      if (acertos != null && completeOk) {
        sumAcertos += acertos;
        nComAcertos += 1;
      }
      const dezenasTd = section === 10
        ? this._manualPosControlsHtml(section, i, nums, sequences, repsList, L, dup.dupCols, hitSet)
        : nums.map((n) => (n == null ? '—' : this._cellNum(n, sequences, repsList, hitSet))).join(' ');
      const mesTd = (section === 10 && this.extraMes)
        ? `<td>${g.monthName
          ? `<span class="mes-cor ${esc(this.mesClass(g.monthName))}" style="${this.mesStyle(g.monthName)}">${esc((g.monthName || '').slice(0, 3).toUpperCase())}</span>`
          : '—'}</td>`
        : '';
      const rowCls = dup.hasDup ? ' class="tb-row-dup"' : '';
      if (section === 10) {
        const acTitle = hitSet
          ? `Acertos vs último concurso`
          : 'Carregue o histórico tubular para conferir';
        const acertosTd10 = `<td class="tb-acertos-td">${this._acertosSpan(acertos, acTitle)}</td>`;
        return `<tr${rowCls}>
          <td>${apostaNum}</td>
          <td class="text-nowrap">${dezenasTd}</td>
          ${acertosTd10}
          ${mesTd}
          <td>${an ? getEmojiByCount(an.sequencesInfo.qtde).text : '—'}</td>
          <td>${an ? getEmojiByCount(an.finaisIguais.qtde).text : '—'}</td>
          <td>${rept.text}</td>
          <td>${an ? an.soma : '—'}</td>
          <td>${an ? an.pares : '—'}</td>
          <td>${an ? an.impares : '—'}</td>
          <td>${an ? esc(an.padroes.inicial) : '—'}</td>
          <td>${an ? esc(an.padroes.final) : '—'}</td>
          <td>${an ? `<span class="${qCls}" title="Dígitos únicos: ${an.qtdeDigitos}">${an.qtdeDigitos}</span>` : '—'}</td>
          <td class="tb-align-mono">${an ? `<span class="tb-mono tb-mono-digs">${esc(an.digitosUnicos)}</span>` : '—'}</td>
          <td><button type="button" class="btn btn-sm btn-outline-danger py-0" data-rm="${section}" data-idx="${i}">×</button></td>
        </tr>`;
      }
      const mesTd11 = this.extraMes
        ? `<td>${g.monthName
          ? `<span class="mes-cor ${esc(this.mesClass(g.monthName))}" style="${this.mesStyle(g.monthName)}">${esc((g.monthName || '').slice(0, 3).toUpperCase())}</span>`
          : '—'}</td>`
        : '';
      const acertosTd = `<td class="tb-acertos-td">${this._acertosSpan(
        acertos,
        this.conferencia11 ? `Acertos no concurso ${this.conferencia11.contest}` : 'Conferir um concurso'
      )}</td>`;
      return `<tr${rowCls}>
        <td>${apostaNum}</td>
        <td class="text-nowrap">${dezenasTd}</td>
        ${acertosTd}
        ${mesTd11}
        <td>${an ? getEmojiByCount(an.sequencesInfo.qtde).text : '—'}</td>
        <td>${an ? getEmojiByCount(an.finaisIguais.qtde).text : '—'}</td>
        <td>${rept.text}</td>
        <td>${an ? an.soma : '—'}</td>
        <td>${an ? an.pares : '—'}</td>
        <td>${an ? an.impares : '—'}</td>
        <td>${an ? esc(an.padroes.inicial) : '—'}</td>
        <td>${an ? esc(an.padroes.final) : '—'}</td>
        <td>${an ? `<span class="${qCls}" title="Dígitos únicos: ${an.qtdeDigitos}">${an.qtdeDigitos}</span>` : '—'}</td>
        <td><button type="button" class="btn btn-sm btn-outline-danger py-0" data-rm="${section}" data-idx="${i}">×</button></td>
      </tr>`;
    }).join('') || `<tr><td colspan="${emptyCols}" class="text-muted">${section === 11 ? 'Clique em «GERAR 10 APOSTAS»' : 'Clique em "+ Adicionar Linha" ou cole jogos acima'}</td></tr>`;

    if (section === 11 && hitSet) {
      const info = this.root.querySelector('#tbConferir11Info');
      if (info && this.conferencia11) {
        const nums = this.conferencia11.nums.map(fmt2).join(' ');
        const tot = sumAcertos;
        const med = nComAcertos ? (sumAcertos / nComAcertos).toFixed(2) : '0';
        info.textContent = `Conc. ${this.conferencia11.contest}: ${nums} · Σ acertos ${tot} · média ${med}`;
      }
    }
    if (section === 10) {
      this._renderManual10DupMsg(alertMsgs);
      this._renderFaltantesHint();
    }

    tbody.querySelectorAll('.tb-manual-input').forEach(inp => {
      inp.addEventListener('change', () => {
        const sec = +inp.dataset.sec;
        const row = +inp.dataset.row;
        const col = +inp.dataset.col;
        const raw = String(inp.value || '').trim();
        const ok = raw === ''
          ? this._setManualPos(sec, row, col, null, L)
          : this._setManualPos(sec, row, col, raw, L);
        this.renderManual(sec);
        if (!ok) return;
      });
      if (+inp.dataset.sec === 10) {
        inp.addEventListener('keydown', (ev) => {
          if (ev.key !== 'ArrowUp' && ev.key !== 'ArrowDown') return;
          ev.preventDefault();
          const sec = +inp.dataset.sec;
          const row = +inp.dataset.row;
          const col = +inp.dataset.col;
          const cur = String(inp.value || '').trim();
          let v = cur === '' ? null : Number(cur);
          if (ev.key === 'ArrowUp') {
            v = v == null ? L.dezenaMin : Math.min(L.dezenaMax, v + 1);
          } else {
            v = v == null ? L.dezenaMin : Math.max(L.dezenaMin, v - 1);
          }
          this._setManualPos(sec, row, col, v, L);
          this.renderManual(sec);
        });
      }
    });
    tbody.querySelectorAll('.tb-pos-btn').forEach(btn => {
      btn.addEventListener('click', (ev) => {
        ev.preventDefault();
        const sec = +btn.dataset.sec;
        const row = +btn.dataset.row;
        const col = +btn.dataset.col;
        const delta = +btn.dataset.delta || 0;
        const arr = sec === 10 ? this.manual10 : this.manual11;
        if (!arr[row]) return;
        const nums = this._manualNumsDisplay(arr[row], sec === 10 ? 'asc' : 'draw', L);
        let cur = nums[col];
        if (cur == null || cur === '') cur = delta > 0 ? L.dezenaMin - 1 : L.dezenaMin;
        const next = Math.min(L.dezenaMax, Math.max(L.dezenaMin, cur + delta));
        this._setManualPos(sec, row, col, next, L);
        this.renderManual(sec);
      });
    });
    tbody.querySelectorAll('[data-rm]').forEach(btn => {
      btn.addEventListener('click', () => {
        const sec = +btn.dataset.rm;
        const idx = +btn.dataset.idx;
        if (sec === 10) this.manual10.splice(idx, 1);
        else this.manual11.splice(idx, 1);
        this.renderManual(sec);
      });
    });

    // Stats tempo real — só apostas completas e sem duplicidade
    if (statsEl) {
      const validGames = list.map(g => {
        let n = (g.numbers || [])
          .filter(x => x !== '' && x != null)
          .map(Number)
          .filter(x => Number.isFinite(x) && x >= L.dezenaMin && x <= L.dezenaMax);
        if (mode === 'asc') n = [...n].sort((a, b) => a - b);
        if (n.length !== L.sorteadas) return null;
        if (this._manualDupInfo(n).hasDup) return null;
        return { nums: n, month: g.monthName };
      }).filter(Boolean);
      let sumSoma = 0, sumP = 0, sumI = 0, sumSeq = 0;
      const freq = {};
      validGames.forEach(g => {
        const an = calculateCompleteAnalysis(g.nums, g.month || 'Janeiro');
        sumSoma += an.soma; sumP += an.pares; sumI += an.impares;
        sumSeq += an.sequencesInfo.qtde;
        g.nums.forEach(n => { freq[n] = (freq[n] || 0) + 1; });
      });
      const n = validGames.length || 1;
      const top = Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([k, v]) => `${fmt2(k)}(${v})`).join(' ') || '—';
      if (section === 11) {
        const sep = '<span class="tb-stats-sep">·</span>';
        statsEl.innerHTML = `<span class="tb-stats-line"><strong>Jogos válidos:</strong> ${validGames.length} / ${list.length}${sep}<strong>Soma média:</strong> ${validGames.length ? (sumSoma / n).toFixed(1) : 0}${sep}<strong>Pares / Ímpares méd.:</strong> ${validGames.length ? (sumP / n).toFixed(1) : 0} / ${validGames.length ? (sumI / n).toFixed(1) : 0}${sep}<strong>Média SEQ:</strong> ${validGames.length ? (sumSeq / n).toFixed(1) : 0}${sep}<strong>Top dezenas:</strong> ${top}</span>`;
      } else {
        statsEl.innerHTML = `
        <div class="tb-stats-item"><strong>Jogos válidos</strong>${validGames.length} / ${list.length}</div>
        <div class="tb-stats-item"><strong>Soma média</strong>${validGames.length ? (sumSoma / n).toFixed(1) : 0}</div>
        <div class="tb-stats-item"><strong>Pares / Ímpares méd.</strong>${validGames.length ? (sumP / n).toFixed(1) : 0} / ${validGames.length ? (sumI / n).toFixed(1) : 0}</div>
        <div class="tb-stats-item"><strong>Média SEQ</strong>${validGames.length ? (sumSeq / n).toFixed(1) : 0}</div>
        <div class="tb-stats-item"><strong>Top dezenas</strong>${top}</div>`;
      }
    }
  };

  TubularApp.prototype._mesAbrevExport = function (g) {
    if (!this.extraMes) return '';
    let idx = -1;
    if (g.month != null && g.month >= 1 && g.month <= 12) idx = g.month - 1;
    else if (g.monthName) {
      const nome = String(g.monthName).normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
      idx = MESES.findIndex(m => m.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase() === nome);
    }
    if (idx < 0) return '';
    const a = MESES_ABREV[idx];
    return a.charAt(0) + a.slice(1).toLowerCase();
  };

  /** Exporta somente dezenas + mês abreviado (reutiliza downloadBlob). */
  TubularApp.prototype.exportManualApostas = function (section) {
    const list = section === 10 ? this.manual10 : this.manual11;
    const L = limitsFrom(this.root);
    const lines = [];
    list.forEach((g) => {
      let nums = (g.numbers || [])
        .filter(n => n !== '' && n != null)
        .map(Number)
        .filter(n => Number.isFinite(n) && n >= L.dezenaMin && n <= L.dezenaMax);
      nums = [...new Set(nums)].sort((a, b) => a - b);
      if (nums.length !== L.sorteadas) return;
      if (this._manualDupInfo(nums).hasDup) return;
      let line = nums.map(fmt2).join(' ');
      if (this.extraMes) {
        const ab = this._mesAbrevExport(g);
        if (ab) line += ` ${ab}`;
      }
      lines.push(line);
    });
    if (!lines.length) {
      alert('Nenhuma aposta válida para exportar.');
      return;
    }
    downloadBlob(lines.join('\n') + '\n', `secao${section}_apostas.txt`, 'text/plain');
  };

  TubularApp.prototype._fpAposta = function (nums, monthName, prevNums) {
    const sorted = [...nums].map(Number).sort((a, b) => a - b);
    const an = calculateCompleteAnalysis(sorted, monthName || '');
    const rept = calculateRepetitions(sorted, prevNums || []);
    return {
      key: sorted.map(fmt2).join('-'),
      soma: an.soma,
      pares: an.pares,
      seq: an.sequencesInfo.qtde,
      seqQuais: an.sequencesInfo.quais || '-',
      finais: an.finaisIguais.qtde,
      finaisQuais: an.finaisIguais.quais || '-',
      reptKey: (rept.list || []).map(fmt2).sort().join(',') || '∅',
      reptCount: rept.count || 0,
      inicial: an.padroes.inicial,
      final: an.padroes.final,
      qtde: an.qtdeDigitos,
      monthName: monthName || '',
    };
  };

  TubularApp.prototype._fpTooSimilar = function (a, b) {
    if (!a || !b) return false;
    if (a.key === b.key) return true;
    let hits = 0;
    if (a.soma === b.soma) hits++;
    if (a.pares === b.pares) hits++;
    if (a.seq === b.seq) hits++;
    if (a.finais === b.finais) hits++;
    if (a.inicial === b.inicial) hits++;
    if (a.final === b.final) hits++;
    if (this.extraMes && a.monthName && b.monthName && a.monthName === b.monthName) hits++;
    return hits >= 4;
  };

  /** Registro extensível de critérios de Soma (priorização na geração). */
  TubularApp.prototype._somaCriterios = {
    padrao: {
      label: 'Padrão',
      hint: 'Modo padrão — coerente com o histórico, sem forçar soma específica.',
      resolve() {
        return { target: null, tol: 35, mode: 'soft', label: 'padrão' };
      },
    },
    frequente: {
      label: 'Mais frequente',
      hint: (ctx) => `Soma mais frequente na janela: ${ctx.target} (${ctx.freq}x).`,
      resolve(somas) {
        const f = {};
        somas.forEach(s => { f[s] = (f[s] || 0) + 1; });
        const best = Object.entries(f).sort((a, b) => b[1] - a[1] || Number(b[0]) - Number(a[0]))[0];
        return { target: Number(best[0]), tol: 0, mode: 'exact', freq: best[1], label: 'mais frequente' };
      },
    },
    alta: {
      label: 'Mais alta',
      hint: (ctx) => `Soma mais alta na janela: ${ctx.target} (±${ctx.tol}).`,
      resolve(somas) {
        const mx = Math.max(...somas);
        const mn = Math.min(...somas);
        const tol = Math.max(3, Math.floor((mx - mn) / 5) || 3);
        return { target: mx, tol, mode: 'min', label: 'mais alta' };
      },
    },
    baixa: {
      label: 'Mais baixa',
      hint: (ctx) => `Soma mais baixa na janela: ${ctx.target} (±${ctx.tol}).`,
      resolve(somas) {
        const mx = Math.max(...somas);
        const mn = Math.min(...somas);
        const tol = Math.max(3, Math.floor((mx - mn) / 5) || 3);
        return { target: mn, tol, mode: 'max', label: 'mais baixa' };
      },
    },
    media: {
      label: 'Média',
      hint: (ctx) => `Soma média na janela: ${ctx.target} (±${ctx.tol}).`,
      resolve(somas) {
        const avg = somas.reduce((a, b) => a + b, 0) / somas.length;
        const mean = Math.round(avg);
        const variance = somas.reduce((s, v) => s + (v - avg) ** 2, 0) / somas.length;
        const std = Math.sqrt(variance);
        const span = Math.max(...somas) - Math.min(...somas);
        const tol = Math.max(2, Math.round(std || span / 4 || 4));
        return { target: mean, tol, mode: 'near', label: 'média' };
      },
    },
  };

  TubularApp.prototype._somaAceita = function (soma, crit) {
    if (!crit || crit.target == null || crit.mode === 'soft') return true;
    if (crit.mode === 'exact') return soma === crit.target;
    if (crit.mode === 'min') return soma >= crit.target - (crit.tol || 0);
    if (crit.mode === 'max') return soma <= crit.target + (crit.tol || 0);
    if (crit.mode === 'near') return Math.abs(soma - crit.target) <= (crit.tol || 0);
    return true;
  };

  TubularApp.prototype._updateAuto11Hints = function () {
    const janela = this.auto11Janela;
    const badge = this.root.querySelector('#tbAuto11Badge');
    if (badge) badge.textContent = janela === 0 ? 'janela: todos' : `janela ${janela}`;

    const modo = this.auto11SomaModo || 'padrao';
    const def = this._somaCriterios[modo] || this._somaCriterios.padrao;
    const hint = this.root.querySelector('#tbAuto11SomaHint');
    const paresHint = this.root.querySelector('#tbAuto11ParesHint');
    const modoPares = this.auto11ParesModo || 'fix_4';
    const L = limitsFrom(this.root);

    if (!this.data.length) {
      if (hint) hint.textContent = def.hint && typeof def.hint === 'string' ? def.hint : def.label;
      if (paresHint) {
        const crit0 = this._resolveParesCrit(modoPares, [], {}, L);
        paresHint.textContent = crit0.hint || crit0.label;
      }
      this._decorateParesComboTitles(L);
      return;
    }
    const chrono = this.data.slice().sort((a, b) => (+a.contest || 0) - (+b.contest || 0));
    const recent = janela > 0 ? chrono.slice(-janela) : chrono.slice();
    const somas = [];
    const paresHist = [];
    const freq = {};
    recent.forEach((c) => {
      const nums = (c.numbersAscending || c.numbersDrawOrder || []).map(Number);
      const an = calculateCompleteAnalysis(nums, c.monthName);
      somas.push(an.soma);
      paresHist.push(an.pares);
      nums.forEach((n) => { freq[n] = (freq[n] || 0) + 1; });
    });

    if (hint) {
      if (!somas.length) {
        hint.textContent = typeof def.hint === 'string' ? def.hint : def.label;
      } else {
        const crit = def.resolve(somas);
        if (typeof def.hint === 'function') hint.textContent = def.hint(crit);
        else if (crit.target != null) hint.textContent = `${def.label}: alvo ${crit.target}${crit.tol ? ` (±${crit.tol})` : ''}.`;
        else hint.textContent = typeof def.hint === 'string' ? def.hint : def.label;
      }
    }

    if (paresHint) {
      const crit = this._resolveParesCrit(modoPares, paresHist, freq, L);
      paresHint.textContent = crit.hint || crit.label;
    }
    this._decorateParesComboTitles(L);
  };

  TubularApp.prototype._decorateParesComboTitles = function (L) {
    const totalUniv = binom(L.dezenaMax - L.dezenaMin + 1, L.sorteadas);
    this.root.querySelectorAll('#tbAuto11ParesModo input[name="tbAuto11Pares"]').forEach((inp) => {
      const lab = inp.closest('label');
      if (!lab) return;
      const nEl = lab.querySelector('[data-pares-n]');
      const m = /^fix_(\d+)$/.exec(inp.value || '');
      let n = 0;
      let title = '';
      if (m) {
        n = paresImparesCombos(Number(m[1]), L);
        title = `${m[1]}P / ${L.sorteadas - Number(m[1])}I → ${fmtIntBR(n)} combinações possíveis`;
      } else if (inp.value === 'aleatorio') {
        n = totalUniv;
        title = `Universo total → ${fmtIntBR(n)} combinações possíveis`;
      }
      lab.title = title;
      if (nEl) nEl.textContent = n ? fmtIntBR(n) : '—';
    });
  };

  /**
   * Resolve o critério de Pares/Ímpares escolhido pelo usuário.
   * fix_N = distribuição fixa; aleatorio = uniforme; historico = pesos da janela.
   */
  TubularApp.prototype._resolveParesCrit = function (modo, paresHist, _freq, L) {
    const nSort = (L && L.sorteadas) || 7;
    const modoKey = modo || 'fix_4';
    const totalUniverso = binom(
      (L.dezenaMax - L.dezenaMin + 1),
      nSort
    );

    if (modoKey === 'historico' || modoKey === 'padrao' || modoKey === 'frequente') {
      const weights = this._paresWeightMap(paresHist);
      const top = this._paresTopFromWeights(weights);
      const weightTotal = Object.values(weights).reduce((s, w) => s + w, 0);
      const parts = Object.entries(weights)
        .sort((a, b) => b[1] - a[1] || Number(b[0]) - Number(a[0]))
        .slice(0, 4)
        .map(([p, w]) => {
          const pp = Number(p);
          const pct = weightTotal ? Math.round((100 * w) / weightTotal) : 0;
          return `${pp}P/${nSort - pp}I ${pct}%`;
        });
      const topCombos = top != null ? paresImparesCombos(top, L) : 0;
      return {
        targetPares: top != null ? top : Math.floor(nSort / 2),
        weights,
        weightTotal,
        mode: 'weighted',
        label: 'histórico',
        sorteadas: nSort,
        combos: topCombos,
        hint: parts.length
          ? `Histórico ponderado: ${parts.join(' · ')} · universo ${fmtIntBR(totalUniverso)} combinações`
          : `Histórico ponderado · universo ${fmtIntBR(totalUniverso)} combinações`,
      };
    }

    if (modoKey === 'aleatorio') {
      // Aleatório com viés dos resultados reais da janela (não uniforme extremo 0P/7P)
      const hist = this._paresWeightMap(paresHist);
      const weights = {};
      for (let p = 0; p <= nSort; p++) {
        weights[p] = Math.max(0.35, Number(hist[p]) || 0);
      }
      const top = this._paresTopFromWeights(weights);
      return {
        targetPares: top != null ? top : Math.floor(nSort / 2),
        weights,
        mode: 'weighted',
        label: 'aleatório',
        sorteadas: nSort,
        combos: totalUniverso,
        hint: `Aleatório com viés dos resultados reais · universo ${fmtIntBR(totalUniverso)}`,
      };
    }

    if (modoKey === 'mais_sai') {
      return this._resolveParesCrit('historico', paresHist, _freq, L);
    }

    const m = /^fix_(\d+)$/.exec(modoKey);
    let tp = 4;
    if (m) tp = Number(m[1]);
    tp = Math.max(0, Math.min(nSort, Number.isFinite(tp) ? tp : 4));
    const imp = nSort - tp;
    const combos = paresImparesCombos(tp, L);
    return {
      targetPares: tp,
      weights: { [tp]: 1 },
      mode: 'exact',
      label: `${tp}P / ${imp}I`,
      sorteadas: nSort,
      combos,
      hint: `Fixo: ${tp} pares / ${imp} ímpares · ${fmtIntBR(combos)} combinações possíveis`,
    };
  };

  /** Alias legado (evita quebras em referências antigas). */
  TubularApp.prototype._paresCriterios = {};

  /** Mapa frequência → peso a partir do histórico de contagens de pares. */
  TubularApp.prototype._paresWeightMap = function (paresHist) {
    const weights = {};
    (paresHist || []).forEach((p) => {
      const n = Number(p);
      if (!Number.isFinite(n)) return;
      weights[n] = (weights[n] || 0) + 1;
    });
    return weights;
  };

  TubularApp.prototype._paresTopFromWeights = function (weights) {
    const entries = Object.entries(weights || {});
    if (!entries.length) return null;
    return Number(entries.sort((a, b) => b[1] - a[1] || Number(b[0]) - Number(a[0]))[0][0]);
  };

  /**
   * Cota ponderada (método do maior resto) + embaralhamento.
   * Garante variedade em lotes grandes alinhada aos pesos históricos.
   */
  TubularApp.prototype._paresQuotaBag = function (alvo, weights, opts) {
    opts = opts || {};
    const entries = Object.entries(weights || {})
      .map(([p, w]) => ({ pares: Number(p), w: Number(w) }))
      .filter(e => Number.isFinite(e.pares) && e.w > 0);
    if (!entries.length || alvo < 1) {
      const fallback = opts.fallback != null ? opts.fallback : 4;
      return Array.from({ length: Math.max(0, alvo) }, () => fallback);
    }
    // Suavização só no modo histórico (evita monopólio da moda)
    const damp = entries.map(e => ({
      ...e,
      w: opts.smooth ? e.w + 0.35 : e.w,
    }));
    if (opts.avoidPares != null) {
      damp.forEach((e) => {
        if (e.pares === opts.avoidPares) e.w *= 0.55;
      });
    }
    const totalW = damp.reduce((s, e) => s + e.w, 0);
    const exacts = damp.map(e => ({ pares: e.pares, exact: (alvo * e.w) / totalW }));
    const quotas = exacts.map(e => ({
      pares: e.pares,
      n: Math.floor(e.exact),
      frac: e.exact - Math.floor(e.exact),
    }));
    let assigned = quotas.reduce((s, q) => s + q.n, 0);
    quotas.sort((a, b) => b.frac - a.frac || a.pares - b.pares);
    let i = 0;
    while (assigned < alvo && quotas.length) {
      quotas[i % quotas.length].n += 1;
      assigned += 1;
      i += 1;
    }
    const bag = [];
    quotas.forEach((q) => {
      for (let k = 0; k < q.n; k++) bag.push(q.pares);
    });
    for (let a = bag.length - 1; a > 0; a--) {
      const b = Math.floor(Math.random() * (a + 1));
      const tmp = bag[a];
      bag[a] = bag[b];
      bag[b] = tmp;
    }
    return bag;
  };

  TubularApp.prototype._paresAceita = function (pares, crit, currentTarget) {
    if (!crit || crit.mode === 'soft') return true;
    if (crit.mode === 'weighted') {
      if (currentTarget != null) return pares === currentTarget;
      const w = crit.weights || {};
      return w[pares] != null && w[pares] > 0;
    }
    if (crit.mode === 'exact') return pares === crit.targetPares;
    if (crit.mode === 'near') return Math.abs(pares - crit.targetPares) <= (crit.tol || 1);
    return true;
  };

  TubularApp.prototype._pickWeighted = function (items, weights) {
    const total = weights.reduce((s, w) => s + w, 0);
    if (total <= 0) return items[Math.floor(Math.random() * items.length)];
    let r = Math.random() * total;
    for (let i = 0; i < items.length; i++) {
      r -= weights[i];
      if (r <= 0) return items[i];
    }
    return items[items.length - 1];
  };

  TubularApp.prototype._modeNum = function (arr) {
    if (!arr.length) return null;
    const f = {};
    arr.forEach(v => { f[v] = (f[v] || 0) + 1; });
    return Number(Object.entries(f).sort((a, b) => b[1] - a[1] || a[0] - b[0])[0][0]);
  };

  /** Entrada separada: quantidade personalizada, mesma lógica de geração. */
  TubularApp.prototype.gerarMaisAutomatico11 = async function () {
    const inp = this.root.querySelector('#tbGerarMais11Qtd');
    let qtd = parseInt(inp && inp.value, 10);
    if (!Number.isFinite(qtd) || qtd < 1) qtd = 50;
    // Limite técnico de segurança (UI/memória); geração continua acumulativa
    const maxCap = 5000;
    if (qtd > maxCap) {
      alert(`Quantidade máxima por lote: ${maxCap}. Ajuste e tente novamente.`);
      if (inp) inp.value = String(maxCap);
      qtd = maxCap;
    }
    if (inp) inp.value = String(qtd);
    await this.gerarAutomatico11(qtd, { maxCap, bulkBtn: '#tbGerarMais11' });
  };

  /**
   * Gera +N apostas com janela configurável e critério de Soma.
   * Obrigatório: SEQ, FINAIS e REPT ≠ padrões da janela.
   * Chamada padrão (botão verde): gerarAutomatico11(10) — comportamento preservado.
   */
  TubularApp.prototype.gerarAutomatico11 = async function (qtd, opts) {
    opts = opts || {};
    const info = this.root.querySelector('#tbGerar11Info');
    const btn = this.root.querySelector('#tbGerar11');
    const bulkBtn = opts.bulkBtn ? this.root.querySelector(opts.bulkBtn) : null;
    const L = limitsFrom(this.root);
    // Botão verde: teto histórico 50; GERAR MAIS usa maxCap próprio
    const maxCap = opts.maxCap != null ? opts.maxCap : 50;
    const alvo = Math.max(1, Math.min(maxCap, Number(qtd) || 10));
    const janela = this.auto11Janela;
    const modoSoma = this.auto11SomaModo || 'padrao';
    const modoPares = this.auto11ParesModo || 'fix_4';

    if (!this.data.length) {
      if (info) info.textContent = 'Carregando histórico…';
      try { await this.load(); } catch (_) { /* ignore */ }
    }
    if (!this.data.length) {
      alert('Não foi possível carregar o histórico tubular. Tente novamente.');
      if (info) info.textContent = 'Sem dados históricos.';
      return;
    }

    const chrono = this.data.slice().sort((a, b) => (+a.contest || 0) - (+b.contest || 0));
    const recent = janela > 0 ? chrono.slice(-janela) : chrono.slice();
    if (!recent.length) {
      alert('Janela sem sorteios.');
      return;
    }
    const lastC = chrono[chrono.length - 1];
    const lastNums = (lastC.numbersAscending || lastC.numbersDrawOrder || []).map(Number).sort((a, b) => a - b);
    const prevLast = chrono.length > 1
      ? (chrono[chrono.length - 2].numbersAscending || []).map(Number)
      : [];
    const lastFp = this._fpAposta(lastNums, lastC.monthName, prevLast);

    const forbidSeq = new Set();
    const forbidFinais = new Set();
    const forbidRept = new Set();
    const freq = {};
    const paresHist = [];
    const somaHist = [];
    const mesHist = [];

    // Padrões reais da janela (mesma classificação SEQ / FINAIS / Rept da tabela)
    const reptCountHist = [];
    recent.forEach((c, i) => {
      const nums = (c.numbersAscending || c.numbersDrawOrder || []).map(Number).sort((a, b) => a - b);
      const prev = i > 0
        ? (recent[i - 1].numbersAscending || []).map(Number)
        : (chrono.length > recent.length
          ? (chrono[chrono.length - recent.length - 1]?.numbersAscending || []).map(Number)
          : []);
      const fp = this._fpAposta(nums, c.monthName, prev);
      forbidSeq.add(`${fp.seq}|${fp.seqQuais}`);
      forbidFinais.add(`${fp.finais}|${fp.finaisQuais}`);
      forbidRept.add(fp.reptKey);
      reptCountHist.push(fp.reptCount);
      nums.forEach((n) => { freq[n] = (freq[n] || 0) + 1; });
      paresHist.push(fp.pares);
      somaHist.push(fp.soma);
      if (c.monthName) mesHist.push(c.monthName);
    });

    const somaDef = this._somaCriterios[modoSoma] || this._somaCriterios.padrao;
    const somaCrit = somaDef.resolve(somaHist);
    const paresCrit = this._resolveParesCrit(modoPares, paresHist, freq, L);

    // Cotas Pares/Ímpares
    const paresWeights = paresCrit.weights && Object.keys(paresCrit.weights).length
      ? paresCrit.weights
      : this._paresWeightMap(paresHist);
    const paresBag = this._paresQuotaBag(alvo, paresWeights, {
      fallback: paresCrit.targetPares != null ? paresCrit.targetPares : 4,
      avoidPares: null,
      smooth: false,
    });
    let paresBagIdx = 0;
    let targetPares = paresBag.length
      ? paresBag[0]
      : (paresCrit.targetPares != null ? paresCrit.targetPares : 4);

    // Cotas de Rept por frequência REAL da janela (1–2 comuns; 3+ raro)
    const reptWeights = this._paresWeightMap(reptCountHist);
    // ∅ proibido na janela → não gerar count 0
    if (forbidRept.has('∅')) delete reptWeights[0];
    // Se a janela não tiver contagem útil, prioriza 1 e 2 (padrão histórico geral)
    if (!Object.keys(reptWeights).length) {
      reptWeights[1] = 4;
      reptWeights[2] = 4;
      reptWeights[3] = 1;
    }
    const reptBag = this._paresQuotaBag(alvo, reptWeights, {
      fallback: 1,
      avoidPares: null,
      smooth: true,
    });
    let reptBagIdx = 0;
    let targetRept = reptBag.length ? reptBag[0] : 1;

    const pool = [];
    for (let n = L.dezenaMin; n <= L.dezenaMax; n++) pool.push(n);
    const freqMul = paresCrit.boostFreq ? 4 : 2;
    let weights = pool.map(n => 1 + (freq[n] || 0) * freqMul);
    if (somaCrit.mode === 'min') weights = pool.map((n, i) => weights[i] * (1 + n / L.dezenaMax));
    if (somaCrit.mode === 'max') weights = pool.map((n, i) => weights[i] * (1 + (L.dezenaMax - n + 1) / L.dezenaMax));

    const lastSet = new Set(lastNums);

    const existingKeys = new Set(
      this.manual11.map((g) => {
        const nums = (g.numbers || []).map(Number).filter(Number.isFinite).sort((a, b) => a - b);
        return nums.length === L.sorteadas ? nums.map(fmt2).join('-') : '';
      }).filter(Boolean)
    );
    recent.forEach((c) => {
      const nums = (c.numbersAscending || []).map(Number).sort((a, b) => a - b);
      if (nums.length === L.sorteadas) existingKeys.add(nums.map(fmt2).join('-'));
    });

    const pickMonth = () => {
      if (!this.extraMes) return { month: 0, monthName: '' };
      const cand = mesHist.filter(m => m && m !== lastC.monthName);
      const nome = cand.length
        ? cand[Math.floor(Math.random() * cand.length)]
        : (mesHist[0] || lastC.monthName || 'Janeiro');
      const idx = MESES.indexOf(nome);
      return { month: idx >= 0 ? idx + 1 : 1, monthName: nome };
    };

    /** Monta aposta com exatamente wantRept overlaps com o último sorteio (padrão real). */
    const tryBuild = (tp, wantRept) => {
      const picked = [];
      const localPool = pool.slice();
      const localW = weights.slice();
      const wantPares = tp != null ? tp : targetPares;
      const needRept = Math.max(0, Math.min(wantRept != null ? wantRept : 1, lastNums.length, L.sorteadas));

      // 1) Semeia EXATAMENTE needRept dezenas do último (não mais)
      if (needRept > 0 && lastNums.length) {
        const seeds = lastNums.slice().sort(() => Math.random() - 0.5);
        for (let s = 0; s < seeds.length && picked.length < needRept; s++) {
          const n = seeds[s];
          const ix = localPool.indexOf(n);
          if (ix < 0) continue;
          const isPar = n % 2 === 0;
          const needPar = picked.filter(x => x % 2 === 0).length;
          if (isPar && needPar >= wantPares) continue;
          if (!isPar && (picked.length - needPar) >= (L.sorteadas - wantPares)) continue;
          picked.push(n);
          localPool.splice(ix, 1);
          localW.splice(ix, 1);
        }
      }

      // 2) Remove o restante do último sorteio do pool → evita Rept 3/4/5 acidental
      for (let i = localPool.length - 1; i >= 0; i--) {
        if (lastSet.has(localPool[i])) {
          localPool.splice(i, 1);
          localW.splice(i, 1);
        }
      }

      while (picked.length < L.sorteadas && localPool.length) {
        const needPar = picked.filter(n => n % 2 === 0).length;
        const remain = L.sorteadas - picked.length;
        const needImp = L.sorteadas - wantPares - (picked.length - needPar);
        let candidates = localPool.map((n, i) => ({ n, w: localW[i], i }));
        if (needPar >= wantPares) candidates = candidates.filter(c => c.n % 2 === 1);
        else if (needImp <= 0) candidates = candidates.filter(c => c.n % 2 === 0);
        else if (remain === 1) {
          if (needPar < wantPares) candidates = candidates.filter(c => c.n % 2 === 0);
          else candidates = candidates.filter(c => c.n % 2 === 1);
        }
        if (!candidates.length) candidates = localPool.map((n, i) => ({ n, w: localW[i], i }));
        const choice = this._pickWeighted(candidates.map(c => c.n), candidates.map(c => c.w));
        const ix = localPool.indexOf(choice);
        picked.push(choice);
        if (ix >= 0) { localPool.splice(ix, 1); localW.splice(ix, 1); }
      }
      return picked.sort((a, b) => a - b);
    };

    if (btn) btn.disabled = true;
    if (bulkBtn) bulkBtn.disabled = true;
    if (info) info.textContent = 'Gerando…';
    this._updateAuto11Hints();

    const aprovadas = [];
    const maxTries = Math.max(alvo * 4000, 20000);
    let tries = 0;
    let failStreak = 0;

    while (aprovadas.length < alvo && tries < maxTries) {
      tries++;
      targetPares = paresBagIdx < paresBag.length
        ? paresBag[paresBagIdx]
        : (() => {
          const ks = Object.keys(paresWeights).map(Number).filter(Number.isFinite);
          if (!ks.length) return 4;
          return this._pickWeighted(ks, ks.map(k => paresWeights[k] || 1));
        })();
      targetRept = reptBagIdx < reptBag.length
        ? reptBag[reptBagIdx]
        : (() => {
          const ks = Object.keys(reptWeights).map(Number).filter(Number.isFinite);
          if (!ks.length) return 1;
          return this._pickWeighted(ks, ks.map(k => reptWeights[k] || 1));
        })();

      const nums = tryBuild(targetPares, targetRept);
      if (nums.length !== L.sorteadas) { failStreak++; continue; }
      if (this._manualDupInfo(nums).hasDup) { failStreak++; continue; }
      const key = nums.map(fmt2).join('-');
      if (existingKeys.has(key) || aprovadas.some(a => a.key === key)) {
        failStreak++;
        if (failStreak >= 120) {
          paresBagIdx += 1;
          reptBagIdx += 1;
          failStreak = 0;
        }
        continue;
      }

      const mes = pickMonth();
      const fp = this._fpAposta(nums, mes.monthName, lastNums);

      // Rept deve seguir a cota do histórico real (1–2 predominante)
      if (fp.reptCount !== targetRept) {
        failStreak++;
        if (failStreak >= 120) { paresBagIdx += 1; reptBagIdx += 1; failStreak = 0; }
        continue;
      }

      // Obrigatório: padrões reais da janela (SEQ / FINAIS / REPT-lista)
      const seqKey = `${fp.seq}|${fp.seqQuais}`;
      const finKey = `${fp.finais}|${fp.finaisQuais}`;
      if (forbidSeq.has(seqKey) || forbidFinais.has(finKey) || forbidRept.has(fp.reptKey)) {
        failStreak++;
        if (failStreak >= 120) { paresBagIdx += 1; reptBagIdx += 1; failStreak = 0; }
        continue;
      }

      // Não copiar o padrão global do último sorteio
      if (this._fpTooSimilar(fp, lastFp)) {
        failStreak++;
        if (failStreak >= 120) { paresBagIdx += 1; reptBagIdx += 1; failStreak = 0; }
        continue;
      }

      // Pares/Ímpares (critério escolhido)
      if (!this._paresAceita(fp.pares, paresCrit, targetPares)) {
        failStreak++;
        if (failStreak >= 120) { paresBagIdx += 1; reptBagIdx += 1; failStreak = 0; }
        continue;
      }

      // Soma (critério escolhido)
      if (!this._somaAceita(fp.soma, somaCrit)) {
        failStreak++;
        if (failStreak >= 120) { paresBagIdx += 1; reptBagIdx += 1; failStreak = 0; }
        continue;
      }
      if (modoSoma === 'padrao' && somaHist.length) {
        const soft = this._modeNum(somaHist);
        if (soft != null && Math.abs(fp.soma - soft) > 35) {
          failStreak++;
          if (failStreak >= 120) { paresBagIdx += 1; reptBagIdx += 1; failStreak = 0; }
          continue;
        }
      }

      existingKeys.add(key);
      aprovadas.push({
        key,
        numbers: nums,
        month: mes.month,
        monthName: mes.monthName,
        editable: false,
        _uid: ++this._manualUid,
      });
      paresBagIdx += 1;
      reptBagIdx += 1;
      failStreak = 0;

      if (alvo > 30 && aprovadas.length % 25 === 0) {
        if (info) info.textContent = `Gerando… ${aprovadas.length}/${alvo}`;
        await new Promise(r => setTimeout(r, 0));
      }
    }

    this.manual11 = this.manual11.concat(aprovadas);
    this.renderManual(11);

    if (btn) btn.disabled = false;
    if (bulkBtn) bulkBtn.disabled = false;
    const modoLbl = (this._somaCriterios[modoSoma] || {}).label || modoSoma;
    const paresLbl = paresCrit.label || modoPares;
    if (info) {
      info.textContent = aprovadas.length === alvo
        ? `+${aprovadas.length} (${modoLbl} · ${paresLbl}) · total ${this.manual11.length}`
        : `Geradas ${aprovadas.length}/${alvo} (${modoLbl} · ${paresLbl}, limite). Total ${this.manual11.length}`;
    }
    if (aprovadas.length < alvo) {
      alert(`Foram geradas ${aprovadas.length} de ${alvo} apostas válidas após ${tries} tentativas.\nSoma: ${modoLbl}. Pares/Ímpares: ${paresLbl}. Janela: ${janela === 0 ? 'todos' : janela}.`);
    }
  };

  TubularApp.prototype.exportMain = function (fmt) {
    // Exporta a mesma fatia visível (página atual / seletor 100·200·500·todos)
    const { rows } = this._visibleRows();
    const nSort = limitsFrom(this.root).sorteadas;
    const fname = 'tubular_analise';
    if (fmt === 'txt') {
      const lines = rows.map(c => {
        const n = this.numsFor(c);
        const base = `${c.contest}\t${c.date}\t${n.map(fmt2).join(' ')}`;
        return this.extraMes ? `${base}\t${c.monthName || ''}` : base;
      });
      downloadBlob(lines.join('\n') + '\n', `${fname}.txt`, 'text/plain');
      return;
    }
    if (fmt === 'html') {
      const table = this.root.querySelector('#tbTabela')?.outerHTML || '';
      downloadBlob(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Tubular</title></head><body>${table}</body></html>`, `${fname}.html`, 'text/html');
      return;
    }
    if (fmt === 'xlsx') {
      const dezHeaders = Array.from({ length: nSort }, (_, i) => String(i + 1));
      const header = [
        'Concurso', 'Data', ...dezHeaders,
        ...(this.extraMes ? ['Mes'] : []),
        'SEQ', 'FINAIS', 'Soma', 'Pares', 'Impares', 'Inicial', 'Final', 'Qtde', 'Numeros',
      ];
      const dataRows = rows.map(c => {
        const n = this.numsFor(c);
        const an = calculateCompleteAnalysis(n, c.monthName);
        return [
          c.contest, c.date, ...n.map(fmt2),
          ...(this.extraMes ? [c.monthName || ''] : []),
          an.sequencesInfo.qtde, an.finaisIguais.qtde, an.soma, an.pares, an.impares,
          an.padroes.inicial, an.padroes.final, an.qtdeDigitos, an.digitosUnicos,
        ];
      });
      let xml = '<?xml version="1.0"?><?mso-application progid="Excel.Sheet"?>';
      xml += '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="Tubular"><Table>';
      [header, ...dataRows].forEach(r => {
        xml += '<Row>' + r.map(c => `<Cell><Data ss:Type="String">${String(c).replace(/&/g,'&amp;').replace(/</g,'&lt;')}</Data></Cell>`).join('') + '</Row>';
      });
      xml += '</Table></Worksheet></Workbook>';
      downloadBlob(xml, `${fname}.xls`, 'application/vnd.ms-excel');
    }
  };

  function boot() {
    const root = document.getElementById('ai-tubular-root');
    if (!root) return;
    const app = new TubularApp(root);
    global.AiTubular = app;
    const mode = String(root.dataset.mode || 'analise');

    if (mode === 'elite-gen') {
      const initialSub = root.dataset.initialSub || 's10';
      const start = async () => {
        if (!app.data.length) {
          try { await app.load(); } catch (_) { /* load já alerta */ }
        }
        app.showSub(initialSub);
      };
      start();
      return;
    }

    // auto-load when aba tubular opens or if already active
    const pane = document.getElementById('tab-tubular');
    if (pane && pane.classList.contains('active')) app.load();
    document.querySelectorAll('#aiTabs [data-aba="tubular"]').forEach(btn => {
      btn.addEventListener('shown.bs.tab', () => { if (!app.data.length) app.load(); });
      btn.addEventListener('click', () => { setTimeout(() => { if (!app.data.length) app.load(); }, 50); });
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  global.TubularLib = {
    analyzeSequences, calculateCompleteAnalysis, calculateRepetitions,
    getEmojiByCount, detectAllConditions, createGradientStyle, parseJogosTexto,
  };
})(window);
