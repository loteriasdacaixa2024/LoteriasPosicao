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
    const pickDef = parseInt(root && root.dataset.pickDefault, 10);
    const cols = parseInt(root && root.dataset.volanteCols, 10);
    return {
      dezenaMin: Number.isFinite(dmin) ? dmin : 1,
      dezenaMax: Number.isFinite(dmax) ? dmax : 31,
      sorteadas: Number.isFinite(sort) ? sort : 7,
      pickDefault: Number.isFinite(pickDef) ? pickDef : (Number.isFinite(sort) ? sort : 7),
      volanteCols: Number.isFinite(cols) && cols > 0 ? cols : 10,
      extraMes: !!(root && String(root.dataset.extraMes || '') === '1'),
      extraTime: !!(root && String(root.dataset.extraTime || '') === '1'),
      extraTrevo: !!(root && String(root.dataset.extraTrevo || '') === '1'),
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
    this.extraTime = String(root.dataset.extraTime || '') === '1';
    this.extraTrevo = String(root.dataset.extraTrevo || '') === '1';
    this._extraOpcoes = null;
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
    this.selected10 = new Set();
    this.selected11 = new Set();
    this._manualUid = 0;
    this.manual10SortKey = null;
    this.manual10SortDir = 'asc';
    this.manual11SortKey = null;
    this.manual11SortDir = 'asc';
    this.stats11Open = false;
    this.conferencia11 = null; // { contest, nums: number[] }
    this.jaSaiuAtivo = { 10: false, 11: false };
    this._histMap = null;
    this._histMapN = -1;
    this.faltantesCiclo = new Set(); // dezenas pendentes do ciclo atual
    this.manual10BlockMsg = '';
    this.auto11Janela = 10;
    this.auto11SomaModo = 'padrao';
    this.auto11ParesModo = 'fix_4';
    this._cmpUid = 0;
    this.cmpVolantes = [];
    this.cmpOficialContest = null;
    this.cmpActiveId = null;
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
    r.querySelector('#tbAddLinha10')?.addEventListener('click', () => this.addManualRow(10));
    r.querySelector('#tbAddLinha10Qtd')?.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Enter') return;
      ev.preventDefault();
      this.addManualRow(10);
    });
    r.querySelector('#tbSelAll10')?.addEventListener('click', () => this.setSelAll(10, true));
    r.querySelector('#tbSelNone10')?.addEventListener('click', () => this.setSelAll(10, false));
    r.querySelector('#tbSelDel10')?.addEventListener('click', () => this.excluirSelecionados(10));
    r.querySelector('#tbSelHead10')?.addEventListener('change', (ev) => this.setSelAll(10, !!ev.target.checked));
    r.querySelector('#tbSelAll11')?.addEventListener('click', () => this.setSelAll(11, true));
    r.querySelector('#tbSelNone11')?.addEventListener('click', () => this.setSelAll(11, false));
    r.querySelector('#tbSelDel11')?.addEventListener('click', () => this.excluirSelecionados(11));
    r.querySelector('#tbSelHead11')?.addEventListener('change', (ev) => this.setSelAll(11, !!ev.target.checked));
    r.querySelector('#tbProcess10')?.addEventListener('click', () => this.processPaste(10));
    r.querySelector('#tbExport10')?.addEventListener('click', () => this.exportManualApostas(10));
    r.querySelector('#tbExport11')?.addEventListener('click', () => this.exportManualApostas(11));
    r.querySelector('#tbJaSaiu10')?.addEventListener('click', () => this.verificarJaSaiu(10));
    r.querySelector('#tbJaSaiu11')?.addEventListener('click', () => this.verificarJaSaiu(11));
    r.querySelector('#tbJaSaiu10Clear')?.addEventListener('click', () => this.limparJaSaiu(10));
    r.querySelector('#tbJaSaiu11Clear')?.addEventListener('click', () => this.limparJaSaiu(11));
    r.querySelector('#tbGerar11')?.addEventListener('click', () => this.gerarAutomatico11(10));
    r.querySelector('#tbGerarMais11')?.addEventListener('click', () => this.gerarMaisAutomatico11());
    r.querySelector('#tbClear10')?.addEventListener('click', () => {
      this.manual10 = [];
      this.manual10BlockMsg = '';
      this.manual10SortKey = null;
      this.manual10SortDir = 'asc';
      this._manualUid = 0;
      this.selected10 = new Set();
      this.jaSaiuAtivo[10] = false;
      this._hideJaSaiuBox(10);
      const ta = this.root.querySelector('#tbPaste10');
      if (ta) ta.value = '';
      const drop = this.root.querySelector('#tbDrop10');
      if (drop) drop.classList.remove('dragover');
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
      this.selected11 = new Set();
      this.jaSaiuAtivo[11] = false;
      this._hideJaSaiuBox(11);
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
    // Futuro: apostas do Elite / Construtor
    r.addEventListener('ai-elite-compare', (ev) => {
      const jogos = (ev.detail && ev.detail.jogos) || [];
      const section = (ev.detail && ev.detail.section) === 11 ? 11 : 10;
      const replace = !!(ev.detail && ev.detail.replace);
      const L = limitsFrom(this.root);
      const parsed = jogos.map(j => {
        let numbers = null;
        let month = this.extraMes ? 1 : 0;
        let monthName = this.extraMes ? 'Janeiro' : '';
        if (j && typeof j === 'object' && !Array.isArray(j)) {
          const raw = j.dezenas || j.numbers || j.nums;
          numbers = Array.isArray(raw) ? raw.map(Number).slice(0, L.sorteadas) : null;
          if (this.extraMes) {
            const mn = parseInt(j.mes_num != null ? j.mes_num : j.month, 10);
            if (Number.isFinite(mn) && mn >= 1 && mn <= 12) {
              month = mn;
              monthName = j.mes_nome || j.monthName || MESES[mn - 1] || '';
            } else if (j.mes_nome || j.monthName) {
              monthName = j.mes_nome || j.monthName;
              const idx = MESES.findIndex(m => m === monthName);
              if (idx >= 0) month = idx + 1;
            }
          }
        } else {
          numbers = Array.isArray(j) ? j.map(Number).slice(0, L.sorteadas) : parseJogosTexto(String(j), L)[0]?.numbers;
        }
        if (!numbers || numbers.length < L.sorteadas) return null;
        return {
          numbers,
          month,
          monthName,
          editable: true,
          _uid: ++this._manualUid,
        };
      }).filter(Boolean);
      if (!parsed.length) return;
      if (section === 10) {
        this.manual10 = replace ? parsed : this.manual10.concat(parsed);
      } else {
        this.manual11 = replace ? parsed : this.manual11.concat(parsed);
      }
      this.renderManual(section);
      if (ev.detail && ev.detail.aviso) {
        const hint = this.root.querySelector(section === 10 ? '#tbFaltantesHint10' : '#tbFaltantesHint11');
        if (hint) {
          hint.textContent = ev.detail.aviso;
          hint.classList.remove('d-none');
        }
      }
    });
    this._syncStats11Collapse();
    this._updateAuto11Hints();
    r.querySelector('#tbCmpAdd1')?.addEventListener('click', () => this.addCmpVolantes(1));
    r.querySelector('#tbCmpAdd5')?.addEventListener('click', () => this.addCmpVolantes(5));
    r.querySelector('#tbCmpAdd10')?.addEventListener('click', () => this.addCmpVolantes(10));
    r.querySelector('#tbCmpAddN')?.addEventListener('click', () => {
      const el = r.querySelector('#tbCmpAddQtd');
      const n = el ? parseInt(el.value, 10) : 1;
      this.addCmpVolantes(Number.isFinite(n) && n > 0 ? n : 1);
    });
    r.querySelector('#tbCmpAddQtd')?.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Enter') return;
      ev.preventDefault();
      r.querySelector('#tbCmpAddN')?.click();
    });
    r.querySelector('#tbCmpExport')?.addEventListener('click', () => this.exportComparador());
    r.querySelector('#tbCmpConcSelect')?.addEventListener('change', () => {
      const v = r.querySelector('#tbCmpConcSelect')?.value;
      this.cmpOficialContest = v ? parseInt(v, 10) : null;
      this.renderComparador();
    });
    r.querySelector('#tbSecao12')?.addEventListener('click', (ev) => this._onCmpVolanteClick(ev));
    r.querySelector('#tbCmpMesCancel')?.addEventListener('click', () => this._closeCmpMesModal());
    r.querySelector('#tbCmpMesOk')?.addEventListener('click', () => this._confirmCmpExport());
    r.querySelector('#tbCmpMesOverlay')?.addEventListener('click', (ev) => {
      if (ev.target === ev.currentTarget) this._closeCmpMesModal();
    });
  };

  TubularApp.prototype.consumeManualImport = function () {
    const KEY = 'tb_manual10_import';
    let raw;
    try { raw = sessionStorage.getItem(KEY); } catch (_) { return false; }
    if (!raw) return false;
    try { sessionStorage.removeItem(KEY); } catch (_) { /* ignore */ }
    let payload;
    try { payload = JSON.parse(raw); } catch (_) { return false; }
    const jogos = (payload && payload.jogos) || [];
    if (!jogos.length) return false;
    this.root.dispatchEvent(new CustomEvent('ai-elite-compare', {
      detail: {
        section: 10,
        jogos,
        replace: !!(payload && payload.replace),
        aviso: (payload && payload.aviso) || `Importado (${jogos.length} apostas).`,
      },
    }));
    return true;
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
    if ((key === 's10' || key === 's11' || key === 's12') && !this.data.length) this.load();
    else if (key === 's10' || key === 's11') this.renderUltimo10();
    if (key === 's10') this.renderManual(10);
    if (key === 's11') {
      this._updateAuto11Hints();
      this._fillConferir11Select();
      this.renderManual(11);
    }
    if (key === 's12') this.renderComparador();
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
        const trevos = Array.isArray(s.trevos) ? s.trevos.map(Number).filter(Number.isFinite) : [];
        return {
          contest: s.concurso || s.numero,
          date: s.data || s.dataApuracao || '',
          numbersAscending: asc,
          numbersDrawOrder: draw,
          month: mesNum,
          monthName: mesNome,
          timeNum: Number(s.time_num) || 0,
          timeNome: s.time_nome || '',
          trevos,
        };
      });
      this._histMap = null;
      this._histMapN = -1;
      this._goLastPage();
      this.renderKpis();
      this.renderCondStats();
      this.renderTable();
      this.renderUltimo10();
      this.renderManual(10);
      this._fillConferir11Select();
      this.renderComparador();
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

  /** HTML da coluna Mês — spinner ▲/▼ ciclando Jan–Dez (mesmo padrão das dezenas). */
  TubularApp.prototype._manualMesControlHtml = function (section, rowIdx, g) {
    let m = parseInt(g && g.month, 10);
    if (!Number.isFinite(m) || m < 1 || m > 12) {
      const idx = MESES.indexOf(g && g.monthName);
      m = idx >= 0 ? idx + 1 : 1;
    }
    const nome = MESES[m - 1] || '';
    const abrev = MESES_ABREV[m - 1] || '—';
    return `<td class="tb-mes-td">
      <div class="tb-mes-ctrl" title="${esc(nome || 'Mês da Sorte')}">
        <div class="tb-pos-box tb-mes-box mes-cor ${esc(this.mesClass(nome))}" style="${this.mesStyle(nome)}">
          <span class="tb-mes-label" aria-label="Mês ${esc(nome)}">${esc(abrev)}</span>
          <span class="tb-pos-spin" aria-hidden="true">
            <button type="button" class="tb-pos-btn tb-mes-btn" data-sec="${section}" data-row="${rowIdx}" data-mes-delta="1" tabindex="-1" aria-label="Mês seguinte">▲</button>
            <button type="button" class="tb-pos-btn tb-mes-btn" data-sec="${section}" data-row="${rowIdx}" data-mes-delta="-1" tabindex="-1" aria-label="Mês anterior">▼</button>
          </span>
        </div>
      </div>
    </td>`;
  };

  TubularApp.prototype._setManualMes = function (sec, row, monthNum) {
    const arr = sec === 10 ? this.manual10 : this.manual11;
    if (!arr[row]) return false;
    let m = parseInt(monthNum, 10);
    if (!Number.isFinite(m)) m = 1;
    // ciclo 1–12
    m = ((m - 1) % 12 + 12) % 12 + 1;
    arr[row].month = m;
    arr[row].monthName = MESES[m - 1] || '';
    return true;
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
    return this._orderedManualList(list, L, last, this.manual10SortKey, this.manual10SortDir, null);
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

  /** Chave da combinação (ordem irrelevante) — só apostas completas. */
  TubularApp.prototype._comboKey = function (nums) {
    const L = limitsFrom(this.root);
    const clean = [...new Set((nums || []).map(Number).filter(n => Number.isFinite(n)))]
      .sort((a, b) => a - b);
    if (clean.length !== L.sorteadas) return '';
    return clean.join('-');
  };

  /** Mapa combinação → ocorrências oficiais (concurso 1 até o atual). */
  TubularApp.prototype._histComboMap = function () {
    if (this._histMap && this._histMapN === this.data.length) return this._histMap;
    const map = new Map();
    (this.data || []).forEach((c) => {
      const nums = c.numbersAscending || c.numbersDrawOrder || [];
      const key = this._comboKey(nums);
      if (!key) return;
      const arr = map.get(key) || [];
      arr.push({
        contest: c.contest,
        date: c.date || '',
        monthName: c.monthName || '',
      });
      map.set(key, arr);
    });
    this._histMap = map;
    this._histMapN = this.data.length;
    return map;
  };

  TubularApp.prototype._hideJaSaiuBox = function (section) {
    const box = this.root.querySelector(section === 10 ? '#tbJaSaiu10Box' : '#tbJaSaiu11Box');
    const info = this.root.querySelector(section === 10 ? '#tbJaSaiu10Info' : '#tbJaSaiu11Info');
    if (box) {
      box.classList.add('d-none');
      box.classList.remove('tb-jasaiu-hit', 'tb-jasaiu-ok');
      box.innerHTML = '';
    }
    if (info) {
      info.textContent = 'Verifica se alguma aposta já foi o resultado oficial (concurso 1 até o atual)';
    }
  };

  TubularApp.prototype.limparJaSaiu = function (section) {
    this.jaSaiuAtivo[section] = false;
    this._hideJaSaiuBox(section);
    this.renderManual(section);
  };

  TubularApp.prototype.verificarJaSaiu = async function (section) {
    const list = section === 10 ? this.manual10 : this.manual11;
    const valid = (list || []).filter((g) => this._comboKey(g && g.numbers)).length;
    if (!valid) {
      alert(section === 11
        ? 'Gere ou carregue apostas na Seção 11 antes de verificar.'
        : 'Adicione apostas na Seção 10 antes de verificar.');
      return;
    }
    if (!this.data.length) {
      await this.load();
    }
    if (!this.data.length) {
      alert('Não foi possível carregar o histórico de concursos.');
      return;
    }
    this.jaSaiuAtivo[section] = true;
    this.renderManual(section);
  };

  TubularApp.prototype._paintJaSaiuBox = function (section, hits, totalValid) {
    const box = this.root.querySelector(section === 10 ? '#tbJaSaiu10Box' : '#tbJaSaiu11Box');
    const info = this.root.querySelector(section === 10 ? '#tbJaSaiu10Info' : '#tbJaSaiu11Info');
    if (!this.jaSaiuAtivo || !this.jaSaiuAtivo[section] || !box) return;
    const chrono = this.data.slice().sort((a, b) => (+a.contest || 0) - (+b.contest || 0));
    const de = chrono.length ? chrono[0].contest : '—';
    const ate = chrono.length ? chrono[chrono.length - 1].contest : '—';
    const faixa = `concursos ${de}–${ate} (${chrono.length})`;
    box.classList.remove('d-none', 'tb-jasaiu-hit', 'tb-jasaiu-ok');
    if (!hits.length) {
      box.classList.add('tb-jasaiu-ok');
      box.innerHTML = `<strong>Nenhuma aposta saiu como resultado oficial</strong> — conferido em ${esc(faixa)}.`;
      if (info) info.textContent = `Nenhuma das ${totalValid} aposta(s) saiu · ${faixa}`;
      return;
    }
    box.classList.add('tb-jasaiu-hit');
    const items = hits.map((h) => {
      const dez = (h.nums || []).map(fmt2).join(' ');
      const oc = (h.ocorrencias || []).map((o) => {
        const mes = o.monthName ? ` · ${o.monthName}` : '';
        return `<strong>#${esc(String(o.contest))}</strong>${o.date ? ` (${esc(o.date)})` : ''}${esc(mes)}`;
      }).join(', ');
      return `<li>Aposta ${esc(String(h.apostaNum))} — <span class="font-monospace">${esc(dez)}</span> → ${oc}</li>`;
    }).join('');
    box.innerHTML = `<div class="fw-bold mb-1">${hits.length} de ${totalValid} aposta(s) já foram sorteadas (${esc(faixa)})</div><ul class="mb-0 ps-3">${items}</ul>`;
    if (info) info.textContent = `${hits.length} de ${totalValid} aposta(s) já saíram · ${faixa}`;
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
      ? `Seleção (laranja): <strong>${n} faltantes do ciclo</strong> · ${esc(sample)}${n > 16 ? '…' : ''}`
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
        <td class="tb-col-soma"><span class="tb-mono tb-mono-soma">${esc(an.soma)}</span></td>
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

  TubularApp.prototype._blankManualRow = function () {
    const L = limitsFrom(this.root);
    return {
      numbers: Array.from({ length: L.sorteadas }, () => null),
      month: this.extraMes ? 1 : 0,
      monthName: this.extraMes ? 'Janeiro' : '',
      editable: true,
      _uid: ++this._manualUid,
    };
  };

  TubularApp.prototype._addLinhaQtd = function (section) {
    const el = this.root.querySelector(section === 10 ? '#tbAddLinha10Qtd' : '#tbAddLinha11Qtd');
    const v = el ? parseInt(el.value, 10) : 1;
    if (!Number.isFinite(v) || v < 1) return 1;
    return Math.min(500, v);
  };

  TubularApp.prototype._focusNewManualRow = function (section, rowIdx) {
    const table = this.root.querySelector(section === 10 ? '#tbManual10' : '#tbManual11');
    const inp = table && table.querySelector(`.tb-manual-input[data-row="${rowIdx}"][data-col="0"]`);
    if (!inp) return;
    try { inp.closest('tr')?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); } catch (_) {}
    inp.focus();
    if (typeof inp.select === 'function') inp.select();
  };

  /**
   * Inclui linhas em branco para preencher à mão.
   * count: qtd (padrão = campo Qtd). afterIdx: insere abaixo dessa linha (array).
   */
  TubularApp.prototype.addManualRow = function (section, count, afterIdx) {
    const n = (count != null && Number.isFinite(+count) && +count > 0)
      ? Math.min(500, Math.max(1, parseInt(count, 10)))
      : this._addLinhaQtd(section);
    const rows = Array.from({ length: n }, () => this._blankManualRow());
    const arr = section === 10 ? this.manual10 : this.manual11;
    const at = Number.isFinite(afterIdx) ? Math.max(0, Math.min(arr.length, afterIdx + 1)) : arr.length;
    arr.splice(at, 0, ...rows);
    this.renderManual(section);
    this._focusNewManualRow(section, at);
  };

  TubularApp.prototype._selSet = function (section) {
    if (section === 10) {
      if (!this.selected10) this.selected10 = new Set();
      return this.selected10;
    }
    if (!this.selected11) this.selected11 = new Set();
    return this.selected11;
  };

  TubularApp.prototype._ensureRowUid = function (g) {
    if (!g) return 0;
    if (g._uid == null) g._uid = ++this._manualUid;
    return g._uid;
  };

  TubularApp.prototype._pruneSel = function (section) {
    const list = section === 10 ? this.manual10 : this.manual11;
    const set = this._selSet(section);
    const live = new Set((list || []).map((g) => g && g._uid).filter((u) => u != null));
    [...set].forEach((u) => { if (!live.has(u)) set.delete(u); });
  };

  TubularApp.prototype._syncSelBar = function (section) {
    this._pruneSel(section);
    const list = section === 10 ? this.manual10 : this.manual11;
    const set = this._selSet(section);
    const n = set.size;
    const total = (list || []).length;
    const bar = this.root.querySelector(section === 10 ? '#tbSelBar10' : '#tbSelBar11');
    const countEl = this.root.querySelector(section === 10 ? '#tbSelCount10' : '#tbSelCount11');
    const btnAll = this.root.querySelector(section === 10 ? '#tbSelAll10' : '#tbSelAll11');
    const btnNone = this.root.querySelector(section === 10 ? '#tbSelNone10' : '#tbSelNone11');
    const btnDel = this.root.querySelector(section === 10 ? '#tbSelDel10' : '#tbSelDel11');
    const headCb = this.root.querySelector(section === 10 ? '#tbSelHead10' : '#tbSelHead11');
    if (bar) bar.classList.toggle('d-none', total === 0);
    if (countEl) {
      countEl.classList.toggle('d-none', n === 0);
      countEl.textContent = n === 1 ? '1 selecionada' : `${n} selecionadas`;
    }
    if (btnAll) {
      btnAll.disabled = total === 0;
      btnAll.classList.toggle('active', total > 0 && n === total);
    }
    if (btnNone) btnNone.disabled = n === 0;
    if (btnDel) {
      btnDel.disabled = n === 0;
      const lab = btnDel.querySelector('.tb-act-label');
      if (lab) lab.textContent = n > 0 ? `Excluir (${n})` : 'Excluir';
      const tip = n > 0 ? `Excluir selecionadas (${n})` : 'Excluir selecionadas';
      btnDel.setAttribute('title', tip);
      btnDel.setAttribute('aria-label', tip);
    }
    if (headCb) {
      headCb.disabled = total === 0;
      headCb.checked = total > 0 && n === total;
      headCb.indeterminate = n > 0 && n < total;
    }
  };

  TubularApp.prototype.setSelAll = function (section, on) {
    const list = section === 10 ? this.manual10 : this.manual11;
    const set = this._selSet(section);
    if (on) (list || []).forEach((g) => { if (g) set.add(this._ensureRowUid(g)); });
    else set.clear();
    const table = this.root.querySelector(section === 10 ? '#tbManual10' : '#tbManual11');
    if (table) {
      table.querySelectorAll('tbody .tb-sel-cb').forEach((cb) => { cb.checked = !!on; });
      table.querySelectorAll('tbody tr[data-uid]').forEach((tr) => tr.classList.toggle('tb-row-sel', !!on));
    }
    this._syncSelBar(section);
  };

  TubularApp.prototype.toggleSel = function (section, uid, on) {
    const set = this._selSet(section);
    if (on) set.add(uid);
    else set.delete(uid);
    const table = this.root.querySelector(section === 10 ? '#tbManual10' : '#tbManual11');
    const tr = table && table.querySelector(`tr[data-uid="${uid}"]`);
    if (tr) tr.classList.toggle('tb-row-sel', !!on);
    this._syncSelBar(section);
  };

  TubularApp.prototype.excluirSelecionados = function (section) {
    this._pruneSel(section);
    const set = this._selSet(section);
    const n = set.size;
    if (!n) return;
    if (n >= 2 && !window.confirm(`Excluir ${n} apostas selecionadas?`)) return;
    const arr = section === 10 ? this.manual10 : this.manual11;
    const kept = arr.filter((g) => !set.has(g && g._uid));
    if (section === 10) this.manual10 = kept;
    else this.manual11 = kept;
    set.clear();
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

  /** Dezenas do último resultado no mesmo layout P1–P7 das apostas (caixa 2.55rem). */
  TubularApp.prototype._ultimoDezenasHtml = function (nums, sequences, reps) {
    const L = limitsFrom(this.root);
    const padded = (nums || []).slice();
    while (padded.length < L.sorteadas) padded.push(null);
    return `<div class="tb-pos-row">${padded.slice(0, L.sorteadas).map((n) => {
      if (n == null || n === '') {
        return `<div class="tb-pos-ctrl"><div class="tb-pos-box tb-pos-box-ro">—</div></div>`;
      }
      const cond = this.marked ? detectAllConditions(n, sequences || [], reps || []) : [];
      const style = this.marked ? createGradientStyle(cond) : { background: '', title: '' };
      const cls = cond.join(' ');
      const inline = style.background ? `style="${style.background}"` : '';
      const title = style.title || fmt2(n);
      return `<div class="tb-pos-ctrl" title="${esc(title)}">
        <div class="tb-pos-box tb-pos-box-ro ${esc(cls)}" ${inline}>
          <span class="tb-pos-ro">${fmt2(n)}</span>
        </div>
      </div>`;
    }).join('')}</div>`;
  };

  TubularApp.prototype.renderUltimo10 = function () {
    this._fillUltimoPreviewAligned();
    this._fillUltimoPreview('#tbUltimo11', '#tbUltimo11Lbl');
  };

  TubularApp.prototype._fillUltimoPreviewAligned = function () {
    const tbody = this.root.querySelector('#tbUltimo10');
    const lbl = this.root.querySelector('#tbUltimo10Lbl');
    if (!tbody) return;
    const nCols = 14 + (this.extraMes ? 1 : 0);
    if (!this.data.length) {
      tbody.innerHTML = `<tr><td colspan="${nCols}" class="text-muted">Carregando histórico tubular…</td></tr>`;
      if (lbl) lbl.textContent = 'Último resultado (referência — histórico tubular)';
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
    const mesTd = this.extraMes
      ? `<td class="tb-mes-td"><span class="mes-cor ${esc(this.mesClass(c.monthName))}" style="${this.mesStyle(c.monthName)}">${esc((c.monthName || '—').slice(0, 3).toUpperCase())}</span></td>`
      : '';
    if (lbl) {
      lbl.textContent = `Último resultado — concurso ${c.contest} (ordem crescente · histórico tubular)`;
    }
    tbody.innerHTML = `<tr class="tb-row-ultimo" title="Resultado oficial do concurso ${esc(c.contest)} — dezenas alinhadas às apostas">
      <td class="tb-sel-td" aria-hidden="true"></td>
      <td class="tb-ultimo-ref">
        <strong>${esc(c.contest)}</strong>
        <div class="small text-muted">${esc(c.date)}</div>
      </td>
      <td class="text-nowrap">${this._ultimoDezenasHtml(nums, an.sequences, rept.list)}</td>
      ${mesTd}
      <td title="${esc(an.sequencesInfo.quais)}">${seqEmoji.text}</td>
      <td title="${esc(an.finaisIguais.quais)}">${finEmoji.text}</td>
      <td title="${esc(rept.title)}">${rept.text}</td>
      <td>${an.soma}</td>
      <td>${an.pares}</td>
      <td>${an.impares}</td>
      <td>${esc(an.padroes.inicial)}</td>
      <td>${esc(an.padroes.final)}</td>
      <td><span class="${qCls}" title="Dígitos únicos: ${an.qtdeDigitos}">${an.qtdeDigitos}</span></td>
      <td class="tb-align-mono"><span class="tb-mono tb-mono-digs">${esc(an.digitosUnicos)}</span></td>
      <td class="tb-row-actions"></td>
    </tr>`;
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
      <td class="tb-col-soma"><span class="tb-mono tb-mono-soma">${esc(an.soma)}</span></td>
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
    const tbody = this.root.querySelector(section === 10 ? '#tbManual10Body' : '#tbManual11 tbody');
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
      : null;

    const order = section === 10
      ? this._orderedManual10(list, L, last)
      : this._orderedManual11(list, L, last);

    const alertMsgs = [];
    let sumAcertos = 0;
    let nComAcertos = 0;
    const jaAtivo = !!(this.jaSaiuAtivo && this.jaSaiuAtivo[section]);
    const histMap = jaAtivo ? this._histComboMap() : null;
    const jaHits = [];
    let nValidJa = 0;
    const emptyCols = 14 + (this.extraMes ? 1 : 0);
    const selSet = this._selSet(section);
    tbody.innerHTML = order.map((origIdx) => {
      const g = list[origIdx];
      const i = origIdx;
      const uid = this._ensureRowUid(g);
      const apostaNum = uid;
      const selected = selSet.has(uid);
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
      let ocorrencias = [];
      if (completeOk) {
        nValidJa += 1;
        const ck = histMap ? this._comboKey(valid) : '';
        ocorrencias = (ck && histMap) ? (histMap.get(ck) || []) : [];
        if (ocorrencias.length) {
          jaHits.push({ apostaNum, nums: valid, ocorrencias });
        }
      }
      const jaSaiu = ocorrencias.length > 0;
      const dezenasTd = section === 10
        ? this._manualPosControlsHtml(section, i, nums, sequences, repsList, L, dup.dupCols, null)
        : nums.map((n) => (n == null ? '—' : this._cellNum(n, sequences, repsList, hitSet))).join(' ');
      const mesTd = (section === 10 && this.extraMes)
        ? this._manualMesControlHtml(section, i, g)
        : '';
      const rowClsParts = [];
      if (dup.hasDup) rowClsParts.push('tb-row-dup');
      if (jaSaiu) rowClsParts.push('tb-row-ja-saiu');
      if (selected) rowClsParts.push('tb-row-sel');
      const rowCls = rowClsParts.length ? ` class="${rowClsParts.join(' ')}"` : '';
      const jaTitle = jaSaiu
        ? ocorrencias.map(o => `#${o.contest}${o.date ? ' · ' + o.date : ''}${o.monthName ? ' · ' + o.monthName : ''}`).join(' · ')
        : '';
      const jaBadge = jaSaiu
        ? ` <span class="tb-badge-ja-saiu" title="${esc(jaTitle)}">já saiu #${esc(String(ocorrencias[0].contest))}${ocorrencias.length > 1 ? ` +${ocorrencias.length - 1}` : ''}</span>`
        : '';
      const selTd = `<td class="tb-sel-td">
        <input type="checkbox" class="tb-sel-cb" data-sel-sec="${section}" data-uid="${uid}"
               ${selected ? 'checked' : ''} aria-label="Selecionar aposta ${apostaNum}">
      </td>`;
      if (section === 10) {
        return `<tr${rowCls} data-uid="${uid}">
          ${selTd}
          <td>${apostaNum}${jaBadge}</td>
          <td class="text-nowrap">${dezenasTd}</td>
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
          <td class="text-nowrap tb-row-actions">
            <button type="button" class="btn btn-sm btn-outline-success py-0 tb-act" data-add-row="${section}" data-idx="${i}" title="Adicionar linha abaixo" aria-label="Adicionar linha abaixo">+</button>
            <button type="button" class="btn btn-sm btn-outline-danger py-0 tb-act" data-rm="${section}" data-idx="${i}" data-uid="${uid}" title="Remover linha" aria-label="Remover linha">×</button>
          </td>
        </tr>`;
      }
      const mesTd11 = this.extraMes
        ? this._manualMesControlHtml(section, i, g)
        : '';
      const acertosTd = `<td class="tb-acertos-td">${this._acertosSpan(
        acertos,
        this.conferencia11 ? `Acertos no concurso ${this.conferencia11.contest}` : 'Conferir um concurso'
      )}</td>`;
      return `<tr${rowCls} data-uid="${uid}">
        ${selTd}
        <td>${apostaNum}${jaBadge}</td>
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
        <td class="text-nowrap tb-row-actions">
          <button type="button" class="btn btn-sm btn-outline-danger py-0 tb-act" data-rm="${section}" data-idx="${i}" data-uid="${uid}" title="Remover linha" aria-label="Remover linha">×</button>
        </td>
      </tr>`;
    }).join('') || `<tr><td colspan="${emptyCols}" class="text-muted">${section === 11 ? 'Clique em «GERAR 10 APOSTAS»' : 'Clique em «+» para incluir apostas em branco, ou cole / arraste um arquivo'}</td></tr>`;

    if (section === 11 && hitSet) {
      const info = this.root.querySelector('#tbConferir11Info');
      if (info && this.conferencia11) {
        const nums = this.conferencia11.nums.map(fmt2).join(' ');
        const tot = sumAcertos;
        const med = nComAcertos ? (sumAcertos / nComAcertos).toFixed(2) : '0';
        info.textContent = `Conc. ${this.conferencia11.contest}: ${nums} · Σ acertos ${tot} · média ${med}`;
      }
    }
    if (jaAtivo) this._paintJaSaiuBox(section, jaHits, nValidJa);
    this._syncSelBar(section);
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
        if (btn.dataset.mesDelta != null) {
          const delta = +btn.dataset.mesDelta || 0;
          const arr = sec === 10 ? this.manual10 : this.manual11;
          if (!arr[row]) return;
          let cur = parseInt(arr[row].month, 10);
          if (!Number.isFinite(cur) || cur < 1 || cur > 12) {
            const idx = MESES.indexOf(arr[row].monthName);
            cur = idx >= 0 ? idx + 1 : 1;
          }
          this._setManualMes(sec, row, cur + delta);
          this.renderManual(sec);
          return;
        }
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
    tbody.querySelectorAll('[data-add-row]').forEach(btn => {
      btn.addEventListener('click', () => {
        const sec = +btn.dataset.addRow;
        const idx = +btn.dataset.idx;
        this.addManualRow(sec, 1, idx);
      });
    });
    tbody.querySelectorAll('.tb-sel-cb').forEach((cb) => {
      cb.addEventListener('click', (ev) => ev.stopPropagation());
      cb.addEventListener('change', (ev) => {
        const sec = +cb.dataset.selSec;
        const uid = +cb.dataset.uid;
        this.toggleSel(sec, uid, !!ev.target.checked);
      });
    });
    tbody.querySelectorAll('[data-rm]').forEach(btn => {
      btn.addEventListener('click', () => {
        const sec = +btn.dataset.rm;
        const idx = +btn.dataset.idx;
        const uid = +btn.dataset.uid;
        const arr = sec === 10 ? this.manual10 : this.manual11;
        const row = arr[idx];
        const id = Number.isFinite(uid) ? uid : (row && row._uid);
        if (id != null) this._selSet(sec).delete(id);
        arr.splice(idx, 1);
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

  TubularApp.prototype._cmpPickMax = function () {
    const L = limitsFrom(this.root);
    return L.pickDefault || L.sorteadas || 7;
  };

  TubularApp.prototype._cmpExtraKind = function () {
    if (this.extraMes) return 'mes';
    if (this.extraTime) return 'time';
    if (this.extraTrevo) return 'trevo';
    return '';
  };

  TubularApp.prototype._cmpExtraLabel = function (c) {
    if (!c) return '';
    if (this.extraMes && c.monthName) return c.monthName;
    if (this.extraTime && (c.timeNome || c.time_nome)) return c.timeNome || c.time_nome;
    const trevos = c.trevos || [];
    if (this.extraTrevo && trevos.length) return 'T ' + trevos.map(fmt2).join(' ');
    return '';
  };

  TubularApp.prototype._applyCmpLayout = function () {
    const pair = this.root.querySelector('#tbCmpPair');
    if (!pair) return;
    const L = limitsFrom(this.root);
    const cols = L.volanteCols || 10;
    const span = (L.dezenaMax - L.dezenaMin) + 1;
    pair.style.setProperty('--tb-cmp-cols', String(cols));
    pair.classList.toggle('tb-cmp-lg', span >= 80);
    pair.classList.toggle('tb-cmp-md', span >= 50 && span < 80);
    const cellW = span >= 80 ? 22 : (span >= 50 ? 26 : 28);
    const gap = 2;
    const volW = cols * cellW + (cols - 1) * gap;
    pair.style.width = `min(${Math.max(volW * 2 + 48, 320)}px, 100%)`;
  };

  TubularApp.prototype._blankCmpVolante = function () {
    return {
      id: ++this._cmpUid,
      nums: [],
      month: this.extraMes ? 0 : 0,
      monthName: '',
    };
  };

  TubularApp.prototype._cmpActive = function () {
    if (!this.cmpVolantes.length) this.initComparador();
    let v = this.cmpVolantes.find(x => x.id === this.cmpActiveId);
    if (!v) {
      v = this.cmpVolantes[0];
      this.cmpActiveId = v ? v.id : null;
    }
    return v || null;
  };

  TubularApp.prototype.initComparador = function () {
    if (!this.root.querySelector('#tbSecao12')) return;
    if (this.cmpVolantes.length) return;
    this.cmpVolantes = Array.from({ length: 10 }, () => this._blankCmpVolante());
    this.cmpActiveId = this.cmpVolantes[0].id;
  };

  TubularApp.prototype._cmpOficialEntry = function () {
    if (!this.data.length) return null;
    const chrono = this.data.slice().sort((a, b) => (+a.contest || 0) - (+b.contest || 0));
    let c = null;
    if (this.cmpOficialContest) {
      c = this.data.find(x => Number(x.contest) === Number(this.cmpOficialContest));
    }
    if (!c) c = chrono[chrono.length - 1];
    if (!c) return null;
    const nums = (c.numbersAscending || c.numbersDrawOrder || []).map(Number).filter(Number.isFinite);
    return {
      contest: c.contest,
      date: c.date || '',
      nums,
      monthName: c.monthName || '',
      timeNum: c.timeNum || 0,
      timeNome: c.timeNome || '',
      trevos: Array.isArray(c.trevos) ? c.trevos.slice() : [],
    };
  };

  TubularApp.prototype._fillCmpConcSelect = function () {
    const sel = this.root.querySelector('#tbCmpConcSelect');
    if (!sel) return;
    const chrono = this.data.slice().sort((a, b) => (+b.contest || 0) - (+a.contest || 0));
    const last = chrono.length ? String(chrono[0].contest) : '';
    const prev = sel.value || (this.cmpOficialContest != null ? String(this.cmpOficialContest) : '');
    const opts = chrono.map((c) => {
      const extra = this._cmpExtraLabel(c);
      const label = `#${c.contest}${c.date ? ' — ' + c.date : ''}${extra ? ' · ' + extra : ''}`;
      return `<option value="${esc(String(c.contest))}">${esc(label)}</option>`;
    });
    sel.innerHTML = opts.length ? opts.join('') : '<option value="">— sem concursos —</option>';
    if (prev && [...sel.options].some(o => o.value === prev)) sel.value = prev;
    else if (last) sel.value = last;
    const v = parseInt(sel.value, 10);
    this.cmpOficialContest = Number.isFinite(v) ? v : null;
  };

  TubularApp.prototype._cmpVolanteHtml = function (selectedArr, opts) {
    opts = opts || {};
    const L = limitsFrom(this.root);
    const sel = new Set((selectedArr || []).map(Number));
    const oficial = opts.oficialSet || null;
    const interactive = !!opts.interactive;
    const vid = opts.vid;
    const cols = L.volanteCols || 10;
    const rows = (L.dezenaMin === 1 && L.dezenaMax === 31)
      ? [[1, 10], [11, 20], [21, 30], [31, 31]]
      : (function () {
          const out = [];
          for (let d = L.dezenaMin; d <= L.dezenaMax; d += cols) {
            out.push([d, Math.min(L.dezenaMax, d + cols - 1)]);
          }
          return out;
        })();
    let html = '<div class="tb-cmp-volante" role="' + (interactive ? 'group' : 'img') + '">';
    rows.forEach(([a, b]) => {
      const count = b - a + 1;
      const partial = count < cols;
      const style = partial ? ` style="grid-template-columns: repeat(${count}, var(--tb-cmp-cell-w))"` : '';
      html += `<div class="tb-cmp-row"${style}>`;
      for (let d = a; d <= b; d++) {
        const on = sel.has(d);
        const inOficial = !!(oficial && oficial.has(d));
        let cls = 'tb-cmp-cell';
        if (interactive) {
          if (on && inOficial) cls += ' rept';
          else if (on) cls += ' na-aposta';
        } else if (inOficial) {
          cls += ' oficial';
        }
        const label = `[${fmt2(d)}]`;
        if (interactive) {
          html += `<button type="button" class="${cls}" data-cmp-dez="${d}" data-cmp-vid="${vid}" aria-pressed="${on ? 'true' : 'false'}">${label}</button>`;
        } else {
          html += `<span class="${cls}">${label}</span>`;
        }
      }
      html += '</div>';
    });
    html += '</div>';
    return html;
  };

  TubularApp.prototype.renderComparador = function (skipSelect) {
    const root12 = this.root.querySelector('#tbSecao12');
    if (!root12) return;
    if (!this.cmpVolantes.length) this.initComparador();
    this._applyCmpLayout();
    if (!skipSelect) this._fillCmpConcSelect();
    const ofc = this._cmpOficialEntry();
    const ofcSet = ofc ? new Set(ofc.nums) : null;
    const L = limitsFrom(this.root);
    const pick = this._cmpPickMax();
    const extraLbl = this._cmpExtraLabel(ofc);
    const lbl = this.root.querySelector('#tbCmpConcLbl');
    const numsEl = this.root.querySelector('#tbCmpOficialNums');
    const volEl = this.root.querySelector('#tbCmpOficialVolante');
    if (lbl) lbl.textContent = ofc ? `CONCURSO ${ofc.contest}` : 'CONCURSO —';
    if (numsEl) {
      numsEl.textContent = ofc
        ? ofc.nums.map(fmt2).join(' ') + (extraLbl ? ' · ' + extraLbl : '')
        : 'Sem resultado.';
    }
    if (volEl) volEl.innerHTML = this._cmpVolanteHtml(ofc ? ofc.nums : [], { oficialSet: ofcSet, interactive: false });

    const active = this._cmpActive();
    const idx = Math.max(0, this.cmpVolantes.findIndex(x => x.id === (active && active.id)));
    const n = ((active && active.nums) || []).slice().sort((a, b) => a - b);
    const manEl = this.root.querySelector('#tbCmpManualVolante');
    if (manEl && active) {
      manEl.innerHTML = this._cmpVolanteHtml(n, { oficialSet: ofcSet, interactive: true, vid: active.id });
    }
    const tit = this.root.querySelector('#tbCmpManualTitulo');
    if (tit) tit.textContent = `Volante ${idx + 1}`;
    const infoMan = this.root.querySelector('#tbCmpManualInfo');
    if (infoMan) infoMan.textContent = `${n.length} / ${pick}`;
    const numsMan = this.root.querySelector('#tbCmpManualNums');
    if (numsMan) {
      numsMan.textContent = n.length
        ? n.map(fmt2).join(' ')
        : `Clique para marcar ${pick} dezenas`;
    }
    const del = this.root.querySelector('#tbCmpDelAtivo');
    if (del && active) del.setAttribute('data-cmp-del', String(active.id));

    const info = this.root.querySelector('#tbCmpInfo');
    if (info) info.textContent = `${this.cmpVolantes.length} volante${this.cmpVolantes.length === 1 ? '' : 's'}`;
    const tabs = this.root.querySelector('#tbCmpVolantes');
    if (tabs) {
      tabs.innerHTML = this.cmpVolantes.map((v, i) => {
        const q = (v.nums || []).length;
        const on = active && v.id === active.id;
        return `<button type="button" class="tb-cmp-tab${on ? ' active' : ''}" data-cmp-tab="${v.id}" aria-pressed="${on ? 'true' : 'false'}">${i + 1}${q ? ` · ${q}` : ''}</button>`;
      }).join('');
    }
  };

  TubularApp.prototype._onCmpVolanteClick = function (ev) {
    const tab = ev.target.closest('[data-cmp-tab]');
    if (tab) {
      const id = parseInt(tab.getAttribute('data-cmp-tab'), 10);
      if (Number.isFinite(id)) {
        this.cmpActiveId = id;
        this.renderComparador(true);
      }
      return;
    }
    const del = ev.target.closest('[data-cmp-del]');
    if (del) {
      const id = parseInt(del.getAttribute('data-cmp-del'), 10);
      this.removeCmpVolante(id);
      return;
    }
    const cell = ev.target.closest('[data-cmp-dez]');
    if (!cell) return;
    const dez = parseInt(cell.getAttribute('data-cmp-dez'), 10);
    const vid = parseInt(cell.getAttribute('data-cmp-vid'), 10);
    if (!Number.isFinite(dez) || !Number.isFinite(vid)) return;
    this.toggleCmpDezena(vid, dez);
  };

  TubularApp.prototype.toggleCmpDezena = function (vid, dez) {
    const v = this.cmpVolantes.find(x => x.id === vid);
    if (!v) return;
    const L = limitsFrom(this.root);
    if (dez < L.dezenaMin || dez > L.dezenaMax) return;
    const set = new Set(v.nums || []);
    if (set.has(dez)) set.delete(dez);
    else {
      if (set.size >= this._cmpPickMax()) return;
      set.add(dez);
    }
    v.nums = [...set].sort((a, b) => a - b);
    this.renderComparador(true);
  };

  TubularApp.prototype.addCmpVolantes = function (count) {
    const n = Math.min(200, Math.max(1, parseInt(count, 10) || 1));
    for (let i = 0; i < n; i++) this.cmpVolantes.push(this._blankCmpVolante());
    this.cmpActiveId = this.cmpVolantes[this.cmpVolantes.length - 1].id;
    this.renderComparador(true);
  };

  TubularApp.prototype.removeCmpVolante = function (id) {
    if (this.cmpVolantes.length <= 1) {
      this.cmpVolantes = [this._blankCmpVolante()];
      this.cmpActiveId = this.cmpVolantes[0].id;
      this.renderComparador(true);
      return;
    }
    this.cmpVolantes = this.cmpVolantes.filter(v => v.id !== id);
    if (!this.cmpVolantes.some(v => v.id === this.cmpActiveId)) {
      this.cmpActiveId = this.cmpVolantes[0].id;
    }
    this.renderComparador(true);
  };

  TubularApp.prototype._shuffleCopy = function (arr) {
    const out = arr.slice();
    for (let i = out.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const t = out[i];
      out[i] = out[j];
      out[j] = t;
    }
    return out;
  };

  TubularApp.prototype._distribuirBloco = function (universo, n) {
    const out = [];
    if (!universo.length || n <= 0) return out;
    while (out.length < n) out.push.apply(out, this._shuffleCopy(universo));
    return out.slice(0, n);
  };

  TubularApp.prototype._paresTrevos = function () {
    const out = [];
    for (let a = 1; a <= 6; a++) {
      for (let b = a + 1; b <= 6; b++) out.push([a, b]);
    }
    return out;
  };

  TubularApp.prototype._resolveTimeLote = function (value, n) {
    const data = this._extraOpcoes || {};
    const times = data.times || [];
    const byNum = {};
    times.forEach((t) => { byNum[Number(t.time_num)] = t; });
    const universo = Object.keys(byNum).map(Number).sort((a, b) => a - b);
    const pool = universo.length ? universo : Array.from({ length: 80 }, (_, i) => i + 1);
    const item = (tn) => ({
      time_num: Number(tn),
      time_nome: (byNum[Number(tn)] && byNum[Number(tn)].time_nome) || ('Time ' + tn),
    });
    const v = String(value || '').trim().toLowerCase();
    if (v === 'aleatorio' || v === 'aleatório' || v === 'random') {
      return this._distribuirBloco(pool, n).map(item);
    }
    let tn = null;
    if (v === 'atrasado') tn = Number((data.atrasado && data.atrasado.time_num) || pool[0]);
    else if (v === 'frequente') tn = Number((data.frequente && data.frequente.time_num) || pool[0]);
    else {
      const num = parseInt(value, 10);
      if (Number.isFinite(num)) tn = num;
    }
    if (tn == null) return [];
    return Array.from({ length: n }, () => item(tn));
  };

  TubularApp.prototype._resolveTrevoLote = function (value, n) {
    const data = this._extraOpcoes || {};
    const pares = this._paresTrevos();
    const v = String(value || '').trim().toLowerCase();
    if (v === 'aleatorio' || v === 'aleatório' || v === 'random') {
      return this._distribuirBloco(pares, n).map(p => p.slice().sort((a, b) => a - b));
    }
    let par = null;
    if (v === 'atrasado') par = (data.atrasado && data.atrasado.trevos) || pares[0];
    else if (v === 'frequente') par = (data.frequente && data.frequente.trevos) || pares[0];
    else {
      const parts = String(value || '').replace(/[,-]/g, ' ').split(/\s+/).filter(Boolean);
      const nums = [];
      parts.forEach((p) => {
        const x = parseInt(p, 10);
        if (x >= 1 && x <= 6 && !nums.includes(x)) nums.push(x);
      });
      if (nums.length >= 2) par = nums.slice(0, 2);
    }
    if (!par) return [];
    const sorted = [Number(par[0]), Number(par[1])].sort((a, b) => a - b);
    return Array.from({ length: n }, () => sorted.slice());
  };

  TubularApp.prototype._fillExtraSelect = function (sel, data) {
    if (!sel || !data || !data.opcoes) return;
    const prev = sel.value;
    sel.innerHTML = '';
    data.opcoes.forEach((o) => {
      const opt = document.createElement('option');
      opt.value = o.value;
      opt.textContent = o.label;
      sel.appendChild(opt);
    });
    const prefer = data.default || 'atrasado';
    const candidates = [prefer, prev];
    for (let i = 0; i < candidates.length; i++) {
      const vs = String(candidates[i] || '');
      if (vs && [...sel.options].some(o => o.value === vs)) {
        sel.value = vs;
        return;
      }
    }
    if (sel.options.length) sel.selectedIndex = 0;
  };

  TubularApp.prototype._cmpExportLines = function (extraLote) {
    const lines = [];
    let mi = 0;
    const kind = this._cmpExtraKind();
    this.cmpVolantes.forEach((v) => {
      const nums = [...new Set((v.nums || []).map(Number).filter(n => Number.isFinite(n)))]
        .sort((a, b) => a - b);
      if (!nums.length) return;
      let line = nums.map(fmt2).join(' ');
      if (kind === 'mes') {
        let pretty = '';
        if (extraLote && extraLote[mi] != null) {
          const mn = Number(extraLote[mi]);
          if (mn >= 1 && mn <= 12) {
            const ab = MESES_ABREV[mn - 1] || '';
            pretty = ab ? (ab.charAt(0) + ab.slice(1).toLowerCase()) : '';
          }
        }
        if (!pretty) pretty = this._mesAbrevExport(v);
        if (pretty) line += ` ${pretty}`;
        mi += 1;
      } else if (kind === 'time' && extraLote && extraLote[mi]) {
        const t = extraLote[mi];
        const nome = (t && t.time_nome) || '';
        if (nome) line += ` ${nome}`;
        mi += 1;
      } else if (kind === 'trevo' && extraLote && extraLote[mi]) {
        const par = extraLote[mi] || [];
        if (par.length) line += ` T${par.map(String).join('-')}`;
        mi += 1;
      }
      lines.push(line);
    });
    return lines;
  };

  TubularApp.prototype._closeCmpMesModal = function () {
    const ov = this.root.querySelector('#tbCmpMesOverlay');
    if (ov) ov.classList.add('d-none');
  };

  TubularApp.prototype._setCmpExtraCopy = function (kind) {
    const tit = this.root.querySelector('#tbCmpMesTitulo');
    const hint = this.root.querySelector('#tbCmpMesHint');
    const lab = this.root.querySelector('#tbCmpMesLabel');
    if (kind === 'time') {
      if (tit) tit.textContent = 'Time do Coração';
      if (hint) hint.textContent = 'Escolha o Time do Coração pela análise (atrasado, mais frequente ou aleatório) para a exportação das apostas.';
      if (lab) lab.textContent = 'Time do Coração';
    } else if (kind === 'trevo') {
      if (tit) tit.textContent = 'Trevos';
      if (hint) hint.textContent = 'Escolha o par de trevos pela análise (atrasado, mais frequente ou aleatório) para a exportação das apostas.';
      if (lab) lab.textContent = 'Trevos';
    } else {
      if (tit) tit.textContent = 'Mês da Sorte';
      if (hint) hint.textContent = 'Escolha o Mês da Sorte para a exportação das apostas dos volantes.';
      if (lab) lab.textContent = 'Mês da Sorte';
    }
  };

  TubularApp.prototype._openCmpMesModal = async function () {
    const ov = this.root.querySelector('#tbCmpMesOverlay');
    const sel = this.root.querySelector('#tbCmpMesSelect');
    if (!ov || !sel) return false;
    const kind = this._cmpExtraKind();
    this._setCmpExtraCopy(kind);
    ov.classList.remove('d-none');

    if (kind === 'time') {
      try {
        const r = await fetch('/geradores-elite/api/time-coracao-opcoes');
        const j = await r.json();
        if (!j || !j.sucesso) throw new Error((j && j.erro) || 'Falha');
        this._extraOpcoes = j;
        this._fillExtraSelect(sel, j);
      } catch (_) {
        sel.innerHTML = '<option value="atrasado">+ Atrasado</option><option value="frequente">+ Frequente</option><option value="aleatorio">+ Aleatório</option>';
        sel.value = 'atrasado';
      }
    } else if (kind === 'trevo') {
      try {
        const r = await fetch('/geradores-elite/api/trevos-opcoes');
        const j = await r.json();
        if (!j || !j.sucesso) throw new Error((j && j.erro) || 'Falha');
        this._extraOpcoes = j;
        this._fillExtraSelect(sel, j);
      } catch (_) {
        sel.innerHTML = '<option value="atrasado">+ Atrasado</option><option value="frequente">+ Frequente</option><option value="aleatorio">+ Aleatório</option>';
        sel.value = 'atrasado';
      }
    } else if (window.MesSorteSelect) {
      try {
        await MesSorteSelect.fillFromApi(sel, '/geradores-elite/api/escolha-tubular', { defaultPrefer: 'atrasado' });
      } catch (_) {
        sel.innerHTML = '<option value="atrasado">+ Atrasado</option><option value="frequente">+ Frequente</option><option value="aleatorio">+ Aleatório</option>'
          + MESES.map((m, i) => `<option value="${i + 1}">${m}</option>`).join('');
        sel.value = 'atrasado';
      }
    } else {
      sel.innerHTML = MESES.map((m, i) => `<option value="${i + 1}">${m}</option>`).join('');
    }
    try { sel.focus(); } catch (_) {}
    return true;
  };

  TubularApp.prototype._confirmCmpExport = function () {
    const sel = this.root.querySelector('#tbCmpMesSelect');
    const filled = (this.cmpVolantes || []).filter(v => (v.nums || []).length);
    const n = filled.length;
    const kind = this._cmpExtraKind();
    let extraLote = null;
    if (kind === 'mes' && sel) {
      if (window.MesSorteSelect) {
        extraLote = MesSorteSelect.resolveLote(sel.value, n, MesSorteSelect.cached);
      } else {
        const mn = parseInt(sel.value, 10);
        extraLote = Number.isFinite(mn) ? Array(n).fill(mn) : null;
      }
    } else if (kind === 'time' && sel) {
      extraLote = this._resolveTimeLote(sel.value, n);
    } else if (kind === 'trevo' && sel) {
      extraLote = this._resolveTrevoLote(sel.value, n);
    }
    const lines = this._cmpExportLines(extraLote);
    this._closeCmpMesModal();
    if (!lines.length) {
      alert('Nenhuma aposta nos volantes para exportar.');
      return;
    }
    downloadBlob(lines.join('\n') + '\n', 'secao12_volantes.txt', 'text/plain');
  };

  TubularApp.prototype.exportComparador = async function () {
    const tem = (this.cmpVolantes || []).some(v => (v.nums || []).length);
    if (!tem) {
      alert('Nenhuma aposta nos volantes para exportar.');
      return;
    }
    if (this._cmpExtraKind() && this.root.querySelector('#tbCmpMesOverlay')) {
      await this._openCmpMesModal();
      return;
    }
    const lines = this._cmpExportLines(null);
    if (!lines.length) {
      alert('Nenhuma aposta nos volantes para exportar.');
      return;
    }
    downloadBlob(lines.join('\n') + '\n', 'secao12_volantes.txt', 'text/plain');
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
        app.showSub(initialSub);
        if (!app.consumeManualImport()) {
          // retry curto se o hub/aba ainda estiver montando
          setTimeout(() => app.consumeManualImport(), 200);
        }
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
