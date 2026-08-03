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

  function fmt2(n) { return String(Number(n)).padStart(2, '0'); }
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
        seq.length >= 3 ? `${seq.numbers[0]}-${seq.numbers[seq.numbers.length - 1]}` : seq.numbers.join(',')
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
        quais: finRep.length ? finRep.map(g => g.join(',')).join(' ') : '-',
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
    if (count === 0) title = 'Nenhuma repetição do concurso anterior';
    else if (count <= 2) title = `${count} número(s) repetido(s): ${list.join(', ')}`;
    else if (count <= 4) title = `${count} números repetiram (alta): ${list.join(', ')}`;
    else title = `${count} números repetiram (extrema!): ${list.join(', ')}`;
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
    this.view = 'draw'; // draw | asc
    this.marked = true;
    this.page = 1;
    this.pageSize = 100;
    this.manual10 = [];
    this.manual11 = [];
    this._bind();
  }

  TubularApp.prototype._effectivePageSize = function () {
    const n = Number(this.pageSize);
    if (!n || n <= 0) return Math.max(1, this.data.length || 1);
    return n;
  };

  TubularApp.prototype._visibleRows = function () {
    const sortedAsc = [...this.data].sort((a, b) => a.contest - b.contest);
    const size = this._effectivePageSize();
    const pages = Math.max(1, Math.ceil(sortedAsc.length / size) || 1);
    if (this.page > pages) this.page = pages;
    const start = (this.page - 1) * size;
    return { sortedAsc, size, pages, start, rows: sortedAsc.slice(start, start + size) };
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
    r.querySelector('#tbBtnMark')?.addEventListener('click', () => { this.marked = true; this.renderTable(); });
    r.querySelector('#tbBtnReset')?.addEventListener('click', () => { this.marked = false; this.renderTable(); });
    r.querySelector('#tbCondStatsToggle')?.addEventListener('click', () => this.toggleCondStats());
    r.querySelector('#tbViewDraw')?.addEventListener('click', () => this.setView('draw'));
    r.querySelector('#tbViewAsc')?.addEventListener('click', () => this.setView('asc'));
    r.querySelector('#tbPageSize')?.addEventListener('change', (e) => {
      this.pageSize = +e.target.value || 0;
      this.page = 1;
      this.renderTable();
    });
    r.querySelector('#tbPrint')?.addEventListener('click', () => window.print());
    r.querySelector('#tbPager')?.addEventListener('click', (ev) => {
      const b = ev.target.closest('[data-page]');
      if (!b) return;
      this.page = +b.dataset.page;
      this.renderTable();
    });
    ['txt', 'xlsx', 'html'].forEach(fmt => {
      r.querySelector(`#tbExport${fmt.toUpperCase()}`)?.addEventListener('click', () => this.exportMain(fmt));
    });
    r.querySelector('#tbAdd10')?.addEventListener('click', () => this.addManualRow(10));
    r.querySelector('#tbAdd11')?.addEventListener('click', () => this.addManualRow(11));
    r.querySelector('#tbProcess10')?.addEventListener('click', () => this.processPaste(10));
    r.querySelector('#tbProcess11')?.addEventListener('click', () => this.processPaste(11));
    r.querySelector('#tbClear10')?.addEventListener('click', () => { this.manual10 = []; this.renderManual(10); });
    r.querySelector('#tbClear11')?.addEventListener('click', () => { this.manual11 = []; this.renderManual(11); });
    this._setupDrop(r.querySelector('#tbDrop10'), 10);
    this._setupDrop(r.querySelector('#tbDrop11'), 11);
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
        };
      }).filter(Boolean);
      if (section === 10) this.manual10 = this.manual10.concat(parsed);
      else this.manual11 = this.manual11.concat(parsed);
      this.renderManual(section);
    });
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

  TubularApp.prototype.load = async function () {
    const st = this.root.querySelector('#tbStatus');
    if (st) st.textContent = 'Carregando…';
    try {
      const r = await fetch(`${this.api}/tubular?base=geral`);
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
      this.page = 1;
      this.renderKpis();
      this.renderCondStats();
      this.renderTable();
      if (st) st.textContent = this.data.length
        ? `${this.data[0].contest} → ${this.data[this.data.length - 1].contest} (${this.data.length})`
        : 'Sem dados';
    } catch (e) {
      if (st) st.textContent = 'Erro ao carregar';
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

  TubularApp.prototype._cellNum = function (n, sequences, reps) {
    const cond = this.marked ? detectAllConditions(n, sequences, reps) : [];
    const style = this.marked ? createGradientStyle(cond) : { background: '', title: '' };
    const cls = cond.join(' ');
    const inline = style.background ? `style="${style.background}"` : '';
    return `<span class="number-cell tb-number ${esc(cls)}" ${inline} title="${esc(style.title || fmt2(n))}">${fmt2(n)}</span>`;
  };

  TubularApp.prototype.renderTable = function () {
    const tbody = this.root.querySelector('#tbTabela tbody');
    if (!tbody) return;
    const { sortedAsc, size, pages, start, rows } = this._visibleRows();

    // Ranking sutil dos padrões de dígitos únicos (mais frequente = 1º)
    const freqDig = {};
    sortedAsc.forEach(c => {
      const key = calculateCompleteAnalysis(this.numsFor(c), c.monthName).digitosUnicos;
      freqDig[key] = (freqDig[key] || 0) + 1;
    });
    const ranked = Object.entries(freqDig).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    const rankMap = {};
    ranked.forEach(([key], i) => { rankMap[key] = i + 1; });

    tbody.innerHTML = rows.map(c => {
      const nums = this.numsFor(c);
      const idx = sortedAsc.findIndex(x => x.contest === c.contest);
      const prev = idx > 0 ? this.numsFor(sortedAsc[idx - 1]) : [];
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
      ...cols.num.map(getter),
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
      numbers: Array.from({ length: L.sorteadas }, () => 0),
      month: this.extraMes ? 1 : 0,
      monthName: this.extraMes ? 'Janeiro' : '',
      editable: true,
    };
    if (section === 10) this.manual10.push(row);
    else this.manual11.push(row);
    this.renderManual(section);
  };

  TubularApp.prototype.processPaste = function (section) {
    const ta = this.root.querySelector(section === 10 ? '#tbPaste10' : '#tbPaste11');
    const parsed = parseJogosTexto(ta?.value || '').map(p => ({ ...p, editable: true }));
    if (section === 10) this.manual10 = this.manual10.concat(parsed);
    else this.manual11 = this.manual11.concat(parsed);
    this.renderManual(section);
  };

  TubularApp.prototype.renderManual = function (section) {
    const list = section === 10 ? this.manual10 : this.manual11;
    const tbody = this.root.querySelector(section === 10 ? '#tbManual10 tbody' : '#tbManual11 tbody');
    const statsEl = this.root.querySelector(section === 10 ? '#tbStats10' : '#tbStats11');
    if (!tbody) return;
    const L = limitsFrom(this.root);
    const mode = section === 10 ? 'asc' : 'draw';
    const last = this.data.length
      ? (mode === 'asc' ? this.data[this.data.length - 1].numbersAscending : this.data[this.data.length - 1].numbersDrawOrder)
      : [];

    tbody.innerHTML = list.map((g, i) => {
      let nums = g.numbers.map(Number);
      if (mode === 'asc') nums = [...nums].filter(n => n > 0).sort((a, b) => a - b);
      while (nums.length < L.sorteadas) nums.push(0);
      const valid = nums.filter(n => n >= L.dezenaMin && n <= L.dezenaMax);
      const an = valid.length === L.sorteadas ? calculateCompleteAnalysis(valid, g.monthName) : null;
      const rept = valid.length === L.sorteadas ? calculateRepetitions(valid, last) : { text: '—' };
      const inputs = nums.map((n, k) =>
        `<input class="tb-manual-input" data-sec="${section}" data-row="${i}" data-col="${k}" value="${n || ''}" maxlength="2">`
      ).join(' ');
      return `<tr>
        <td>${i + 1}</td>
        <td class="text-nowrap">${inputs}</td>
        <td>${an ? getEmojiByCount(an.sequencesInfo.qtde).text : '—'}</td>
        <td>${an ? getEmojiByCount(an.finaisIguais.qtde).text : '—'}</td>
        <td>${rept.text}</td>
        <td>${an ? an.soma : '—'}</td>
        <td>${an ? `${an.pares}/${an.impares}` : '—'}</td>
        <td>${an ? esc(an.padroes.inicial) : '—'}</td>
        <td>${an ? esc(an.padroes.final) : '—'}</td>
        <td>${an ? an.qtdeDigitos : '—'}</td>
        <td><button type="button" class="btn btn-sm btn-outline-danger py-0" data-rm="${section}" data-idx="${i}">×</button></td>
      </tr>`;
    }).join('') || `<tr><td colspan="11" class="text-muted">Clique em "+ Adicionar Linha" ou cole jogos acima</td></tr>`;

    tbody.querySelectorAll('.tb-manual-input').forEach(inp => {
      inp.addEventListener('change', () => {
        const sec = +inp.dataset.sec;
        const row = +inp.dataset.row;
        const col = +inp.dataset.col;
        const arr = sec === 10 ? this.manual10 : this.manual11;
        if (!arr[row]) return;
        arr[row].numbers[col] = Math.min(L.dezenaMax, Math.max(0, +inp.value || 0));
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

    // Stats tempo real
    if (statsEl) {
      const validGames = list.map(g => {
        let n = g.numbers.map(Number).filter(x => x >= L.dezenaMin && x <= L.dezenaMax);
        if (mode === 'asc') n = [...n].sort((a, b) => a - b);
        return n.length === L.sorteadas ? n : null;
      }).filter(Boolean);
      let sumSoma = 0, sumP = 0, sumI = 0, sumSeq = 0;
      const freq = {};
      validGames.forEach(nums => {
        const an = calculateCompleteAnalysis(nums, 'Janeiro');
        sumSoma += an.soma; sumP += an.pares; sumI += an.impares;
        sumSeq += an.sequencesInfo.qtde;
        nums.forEach(n => { freq[n] = (freq[n] || 0) + 1; });
      });
      const n = validGames.length || 1;
      const top = Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([k, v]) => `${fmt2(k)}(${v})`).join(' ') || '—';
      statsEl.innerHTML = `
        <div class="tb-stats-item"><strong>Jogos válidos</strong>${validGames.length} / ${list.length}</div>
        <div class="tb-stats-item"><strong>Soma média</strong>${validGames.length ? (sumSoma / n).toFixed(1) : 0}</div>
        <div class="tb-stats-item"><strong>Pares / Ímpares méd.</strong>${validGames.length ? (sumP / n).toFixed(1) : 0} / ${validGames.length ? (sumI / n).toFixed(1) : 0}</div>
        <div class="tb-stats-item"><strong>Média SEQ</strong>${validGames.length ? (sumSeq / n).toFixed(1) : 0}</div>
        <div class="tb-stats-item"><strong>Top dezenas</strong>${top}</div>`;
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
