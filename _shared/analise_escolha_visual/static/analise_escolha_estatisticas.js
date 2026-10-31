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
  const MODALIDADE = (root.dataset.modalityNome || 'Modalidade').trim();
  const PASTA_MODALIDADE = {
    'Dia de Sorte': 'dia-de-sorte',
    'Mega-Sena': 'megasena',
    'Lotofácil': 'lotofacil',
    'Quina': 'quina',
    'Lotomania': 'lotomania',
    'Timemania': 'timemania',
    'Dupla Sena': 'duplasena',
    'Super Sete': 'supersete',
    '+Milionária': 'mais-milionaria',
  };

  function caminhoPadrao() {
    const pasta = PASTA_MODALIDADE[MODALIDADE];
    if (!pasta) return '';
    return `conferencia_apostas/${pasta}/Estatisticas_Basicas.xlsx`;
  }

  let payload = null;
  let charts = { paridade: null, grupos: null, cruz: null };
  let dirty = true;
  let linhasCache = { ordem: '', rows: [] };

  const DMIN = parseInt(root.dataset.dezenaMin || '1', 10);
  const DMAX = parseInt(root.dataset.dezenaMax || '31', 10);
  const VCOLS = parseInt(root.dataset.volanteCols || '10', 10) || 10;
  const VROWS = parseInt(root.dataset.volanteRows || '1', 10) || 1;
  const PICK = parseInt(root.dataset.sorteadas || '7', 10) || 7;
  const COM_DIAG = VROWS > 1;
  const MAX_APOSTAS = 500;
  const EXTRA_MES = root.dataset.extraMes === '1';
  const MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
  const MESES_ABREV = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ'];
  let mesesCores = {};
  try { mesesCores = JSON.parse(root.dataset.mesesCores || '{}'); } catch (e) { mesesCores = {}; }

  const CORES = {
    pares: '#28a745',
    impares: '#17a2b8',
    repetidos: '#9b59b6',
    sequencias: '#4ade80',
    finais: '#ffc107',
    diagonais: '#1e4b7b',
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

  function criarDiag(dmin, dmax, cols) {
    const lo = Number(dmin) || 1;
    const hi = Number(dmax) || 31;
    const step = Math.max(1, Number(cols) || 10);
    const rows = [];
    if (lo === 1 && hi === 31 && step === 10) {
      rows.push([1, 10], [11, 20], [21, 30], [31, 31]);
    } else {
      for (let n = lo; n <= hi; n += step) rows.push([n, Math.min(hi, n + step - 1)]);
    }
    const pmap = {};
    rows.forEach((ab, r) => {
      for (let n = ab[0]; n <= ab[1]; n += 1) pmap[n] = [r, n - ab[0]];
    });
    function geomDir(nums) {
      const cells = nums.map((n) => pmap[n]).filter(Boolean)
        .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
      if (cells.length < 2) return 'down';
      const first = cells[0];
      const last = cells[cells.length - 1];
      if (last[1] > first[1]) return 'down';
      if (last[1] < first[1]) return 'up';
      return 'down';
    }
    function orderGeom(nums) {
      return [...nums].filter((n) => pmap[n]).sort((a, b) => {
        const pa = pmap[a];
        const pb = pmap[b];
        return pa[0] - pb[0] || pa[1] - pb[1] || a - b;
      });
    }
    const down = {};
    const up = {};
    rows.forEach((ab, r) => {
      for (let n = ab[0]; n <= ab[1]; n += 1) {
        const c = n - ab[0];
        (down[c - r] || (down[c - r] = [])).push({ n, r, c });
        (up[c + r] || (up[c + r] = [])).push({ n, r, c });
      }
    });
    const lines = [];
    function flush(mapa) {
      Object.keys(mapa).forEach((key) => {
        const arr = mapa[key];
        arr.sort((a, b) => a.r - b.r || a.c - b.c);
        let run = [];
        const close = () => {
          if (run.length >= 2) lines.push(run.map((x) => x.n));
        };
        arr.forEach((cell) => {
          if (!run.length || cell.r === run[run.length - 1].r + 1) run.push(cell);
          else {
            close();
            run = [cell];
          }
        });
        close();
      });
    }
    flush(down);
    flush(up);
    return function runsInDraw(dezenas) {
      const chosen = new Set((dezenas || []).map(Number).filter((n) => pmap[n]));
      const runs = [];
      const seen = new Set();
      lines.forEach((line) => {
        let cur = [];
        const push = () => {
          if (cur.length < 2) return;
          const nums = orderGeom(cur);
          if (nums.length < 2) return;
          const dir = geomDir(nums);
          const chave = `${dir}:${nums.join('-')}`;
          if (seen.has(chave)) return;
          seen.add(chave);
          runs.push({
            dir,
            dir_sym: dir === 'down' ? '↘' : '↗',
            nums,
            len: nums.length,
          });
        };
        line.forEach((n) => {
          if (chosen.has(n)) cur.push(n);
          else {
            push();
            cur = [];
          }
        });
        push();
      });
      runs.sort((a, b) => b.len - a.len || `${a.dir}:${a.nums.join('-')}`.localeCompare(`${b.dir}:${b.nums.join('-')}`));
      return runs;
    };
  }

  const diagRuns = COM_DIAG ? criarDiag(DMIN, DMAX, VCOLS) : (() => []);

  function blocoDiag(nums) {
    const runs = diagRuns(nums);
    const grupos = runs.map((d) => ({ dir_sym: d.dir_sym, nums: d.nums.slice() }));
    const flat = [...new Set(grupos.flatMap((g) => g.nums))].sort((a, b) => a - b);
    const bloco = blocoGrupo('Diagonais', flat, { grupos, qtd_grupos: grupos.length });
    bloco.quantidade = grupos.length;
    return bloco;
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
      mes_num: s.mes_num || null,
      mes_nome: s.mes_nome || '',
      numeros: nums,
      pares: blocoGrupo('Pares', pares),
      impares: blocoGrupo('Ímpares', impares),
      repetidos: blocoGrupo('Repetidos', repetidos),
      sequencias: blocoGrupo('Sequências', seqFlat, { grupos: seqG, qtd_grupos: seqG.length }),
      finais: blocoGrupo('Finais Iguais', finFlat, { grupos: finG, qtd_grupos: finG.length }),
      diagonais: blocoDiag(nums),
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
    if (k === 'diagonais') return celulaGrupo('diagonais', b) === '—' ? '' : celulaGrupo('diagonais', b);
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
    if (k === 'diagonais') {
      const grupos = bloco.detalhe?.grupos || [];
      if (!grupos.length) return '—';
      return grupos.map((g) => {
        const nums = (g.nums || g).map(fmt).join('-');
        return g.dir_sym ? `${g.dir_sym} | ${nums}` : nums;
      }).join(' · ');
    }
    return numsLinha(bloco.dezenas);
  }

  function hexDe(color, fallback) {
    const c = String(color || '').trim();
    const short = c.match(/^#([0-9a-fA-F]{3})$/);
    if (short) {
      const h = short[1];
      return (`#${h[0]}${h[0]}${h[1]}${h[1]}${h[2]}${h[2]}`).toUpperCase();
    }
    if (/^#[0-9a-fA-F]{6}$/.test(c)) return c.toUpperCase();
    const rgb = c.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
    if (rgb) {
      const p = (n) => Number(n).toString(16).padStart(2, '0');
      return (`#${p(rgb[1])}${p(rgb[2])}${p(rgb[3])}`).toUpperCase();
    }
    return fallback;
  }

  function corVar(name, fallback) {
    const raw = getComputedStyle(root).getPropertyValue(name);
    return hexDe(raw, fallback);
  }

  function rgbDe(hex) {
    const n = parseInt(String(hex).replace('#', ''), 16);
    return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
  }

  function hexRgb(r, g, b) {
    const p = (n) => Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, '0');
    return (`#${p(r)}${p(g)}${p(b)}`).toUpperCase();
  }

  function misturarBranco(hex, qtd) {
    const { r, g, b } = rgbDe(hex);
    const m = (ch) => ch + (255 - ch) * qtd;
    return hexRgb(m(r), m(g), m(b));
  }

  function fonteLegivel(hex) {
    let { r, g, b } = rgbDe(hex);
    let y = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    let guard = 0;
    while (y > 0.46 && guard < 6) {
      r *= 0.72;
      g *= 0.72;
      b *= 0.72;
      y = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
      guard += 1;
    }
    return hexRgb(r, g, b);
  }

  function textoSobre(hex) {
    const { r, g, b } = rgbDe(hex);
    const y = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return y > 0.62 ? '#1A0A00' : '#FFFFFF';
  }

  function xmlEsc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function atualizarBotaoXls(qtd) {
    const btn = document.getElementById('evStatBasicosXls');
    if (!btn) return;
    const n = Number(qtd) || 0;
    btn.disabled = n < 1;
    btn.title = n
      ? `Baixar ${n.toLocaleString('pt-BR')} linha(s) em Excel (.xlsx), com as colunas formatadas`
      : 'Sem sorteios para exportar';
  }

  function nomeArquivoXls(nome) {
    const base = String(nome || 'Modalidade')
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/\+/g, 'Mais ')
      .replace(/[^\w\s-]/g, '')
      .trim()
      .replace(/[\s-]+/g, '_');
    return `${base || 'Modalidade'}_Estatisticas_Basicas.xls`;
  }

  function baixarBasicosXls() {
    const linhas = (payload && payload.linhas_basicas) || [];
    if (!linhas.length) return;
    const primary = corVar('--primary', '#C08B00');
    const primaryDark = corVar('--primary-dark', '#996E00');
    const primaryX = corVar('--primary-xdark', '#664A00');
    const pares = corVar('--cor-pares', CORES.pares);
    const impares = corVar('--cor-impares', CORES.impares);
    const repetidos = corVar('--cor-repetidos', CORES.repetidos);
    const sequencias = corVar('--cor-sequencia-1', CORES.sequencias);
    const finais = corVar('--cor-finais-iguais', CORES.finais);
    const cols = [
      { id: 'conc', titulo: 'Conc.', fundo: primary, fonte: '#1A0A00', negrito: true },
      { id: 'data', titulo: 'Data', fundo: primaryDark, fonte: '#5C5346' },
      { id: 'sorteio', titulo: 'Sorteio', fundo: primaryX, fonte: '#1A0A00' },
      { id: 'pares', titulo: 'Pares', fundo: pares, fonte: fonteLegivel(pares) },
      { id: 'impares', titulo: 'Ímpares', fundo: impares, fonte: fonteLegivel(impares) },
      { id: 'repetidos', titulo: 'Repetidos', fundo: repetidos, fonte: fonteLegivel(repetidos) },
      { id: 'sequencias', titulo: 'Sequências', fundo: sequencias, fonte: fonteLegivel(sequencias) },
      { id: 'finais', titulo: 'Finais Iguais', fundo: finais, fonte: fonteLegivel(finais) },
      { id: 'diagonais', titulo: 'Diagonais', fundo: CORES.diagonais, fonte: '#FFFFFF' },
    ];
    const valores = linhas.map((ln) => [
      ln.concurso,
      ln.data || '—',
      numsLinha(ln.numeros),
      celulaGrupo('pares', ln.pares),
      celulaGrupo('impares', ln.impares),
      celulaGrupo('repetidos', ln.repetidos),
      celulaGrupo('sequencias', ln.sequencias),
      celulaGrupo('finais', ln.finais),
      celulaGrupo('diagonais', ln.diagonais),
    ]);
    const larguras = cols.map((col, i) => {
      let max = col.titulo.length;
      valores.forEach((row) => { max = Math.max(max, String(row[i] == null ? '' : row[i]).length); });
      return Math.min(420, Math.max(62, Math.ceil(max * 6.5 + 18)));
    });
    const borda = misturarBranco(primary, 0.62);
    let styles = '<Style ss:ID="Default" ss:Name="Normal"><Alignment ss:Vertical="Center"/><Font ss:FontName="Calibri" ss:Size="11"/></Style>';
    cols.forEach((col, i) => {
      const cab = textoSobre(col.fundo);
      styles += `<Style ss:ID="h${i}"><Alignment ss:Horizontal="Center" ss:Vertical="Center"/>`
        + `<Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="${cab}"/>`
        + `<Interior ss:Color="${col.fundo}" ss:Pattern="Solid"/>`
        + `<Borders>`
        + `<Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="${borda}"/>`
        + `<Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="${borda}"/>`
        + `<Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="${borda}"/>`
        + `<Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="${borda}"/>`
        + `</Borders></Style>`;
      styles += `<Style ss:ID="c${i}"><Alignment ss:Horizontal="${i < 2 ? 'Center' : 'Left'}" ss:Vertical="Center"/>`
        + `<Font ss:FontName="${i >= 2 ? 'Consolas' : 'Calibri'}" ss:Size="10" ss:Bold="${col.negrito ? '1' : '0'}" ss:Color="${col.fonte}"/>`
        + `<Interior ss:Color="${misturarBranco(col.fundo, 0.86)}" ss:Pattern="Solid"/>`
        + `<Borders>`
        + `<Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="${borda}"/>`
        + `<Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="${borda}"/>`
        + `<Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="${borda}"/>`
        + `<Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="${borda}"/>`
        + `</Borders></Style>`;
    });
    const header = `<Row ss:Height="22">${cols.map((col, i) =>
      `<Cell ss:StyleID="h${i}"><Data ss:Type="String">${xmlEsc(col.titulo)}</Data></Cell>`
    ).join('')}</Row>`;
    const body = valores.map((row) => {
      const cells = row.map((val, i) => {
        const num = i === 0 && Number.isFinite(Number(val));
        const tipo = num ? 'Number' : 'String';
        const texto = num ? String(Number(val)) : (val == null || val === '' ? '—' : val);
        return `<Cell ss:StyleID="c${i}"><Data ss:Type="${tipo}">${xmlEsc(texto)}</Data></Cell>`;
      }).join('');
      return `<Row>${cells}</Row>`;
    }).join('');
    const ultima = valores.length + 1;
    const xml = '<?xml version="1.0" encoding="UTF-8"?>'
      + '<?mso-application progid="Excel.Sheet"?>'
      + '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"'
      + ' xmlns:o="urn:schemas-microsoft-com:office:office"'
      + ' xmlns:x="urn:schemas-microsoft-com:office:excel"'
      + ' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'
      + '<DocumentProperties xmlns="urn:schemas-microsoft-com:office:office">'
      + `<Title>${xmlEsc('Estatísticas Básicas — ' + MODALIDADE)}</Title>`
      + '</DocumentProperties>'
      + `<Styles>${styles}</Styles>`
      + '<Worksheet ss:Name="Estatisticas Basicas"><Table>'
      + larguras.map((w) => `<Column ss:AutoFitWidth="0" ss:Width="${w}"/>`).join('')
      + header + body
      + '</Table>'
      + `<AutoFilter x:Range="R1C1:R${ultima}C9" xmlns="urn:schemas-microsoft-com:office:excel"></AutoFilter>`
      + '<WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel">'
      + '<FreezePanes/><FrozenNoSplit/>'
      + '<SplitHorizontal>1</SplitHorizontal><TopRowBottomPane>1</TopRowBottomPane><ActivePane>2</ActivePane>'
      + '</WorksheetOptions></Worksheet></Workbook>';
    const blob = new Blob(['\uFEFF', xml], { type: 'application/vnd.ms-excel;charset=utf-8' });
    const a = document.createElement('a');
    const url = URL.createObjectURL(blob);
    a.href = url;
    a.download = nomeArquivoXls(MODALIDADE);
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  function nomeDoAnexo(header, fallback) {
    const m = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(header || '');
    if (!m) return fallback;
    try { return decodeURIComponent((m[1] || m[2] || '').trim()); }
    catch (_) { return (m[2] || fallback).trim(); }
  }

  function baixarBlob(blob, nome) {
    const a = document.createElement('a');
    const url = URL.createObjectURL(blob);
    a.href = url;
    a.download = nome;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  async function baixarBasicosServidor() {
    const linhas = (payload && payload.linhas_basicas) || [];
    if (!linhas.length) return;
    const btn = document.getElementById('evStatBasicosXls');
    const original = btn ? btn.innerHTML : '';
    const f = filtros();
    const qs = new URLSearchParams({
      ordem: f.ordem || 'desc',
      limite: '0',
      base: 'geral',
    });
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> Gerando…';
    }
    try {
      const r = await fetch(`${API}/basicas.xlsx?${qs}`);
      const ctype = r.headers.get('content-type') || '';
      if (!r.ok) {
        let msg = '';
        if (ctype.includes('json')) {
          try {
            const data = await r.json();
            msg = data.mensagem || '';
          } catch (_) { /* mantém o download local */ }
        }
        if (msg) window.alert(msg);
        if (!msg || r.status >= 500) baixarBasicosXls();
        return;
      }
      if (!ctype.includes('spreadsheet') && !ctype.includes('octet-stream')) {
        baixarBasicosXls();
        return;
      }
      const blob = await r.blob();
      baixarBlob(blob, nomeDoAnexo(r.headers.get('content-disposition'), nomeArquivoXls(MODALIDADE).replace(/\.xls$/, '.xlsx')));
      const caminho = r.headers.get('X-Estatisticas-Caminho');
      const pathEl = document.getElementById('evStatBasicosPath');
      if (caminho && pathEl) {
        try { pathEl.textContent = decodeURIComponent(caminho); } catch (_) { /* ignora */ }
      }
      const aviso = r.headers.get('X-Estatisticas-Aviso');
      if (aviso) {
        try { window.alert(decodeURIComponent(aviso)); } catch (_) { window.alert(aviso); }
      }
    } catch (_) {
      baixarBasicosXls();
    } finally {
      if (btn) {
        btn.innerHTML = original;
        atualizarBotaoXls((payload && payload.linhas_basicas || []).length);
      }
    }
  }

  function renderBasicos() {
    const foco = payload.concurso_foco || {};
    const basicos = foco.basicos || {};
    const titulo = document.getElementById('evStatConcTitulo');
    if (titulo) titulo.textContent = String(foco.concurso || '—');
    if (COM_DIAG && Array.isArray(foco.numeros) && !basicos.diagonais) {
      basicos.diagonais = blocoDiag(foco.numeros);
    }
    const order = ['pares', 'impares', 'repetidos', 'sequencias', 'finais'];
    if (COM_DIAG) order.push('diagonais');
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
            ${k === 'diagonais'
              ? `<div class="mt-1 ev-basic-nums" style="color:${CORES.diagonais}">${celulaGrupo('diagonais', b)}</div>`
              : `<div class="mt-1">${chips(b.dezenas)}</div>${extra ? `<div class="small text-muted mt-1">${extra}</div>` : ''}`}
          </div>
        </div>`).join('');
    }
    renderBasicosTabela();
    renderApostas();
  }

  function renderBasicosTabela() {
    const tbody = document.getElementById('evStatBasicosTabela');
    const nEl = document.getElementById('evStatBasicosN');
    const linhas = payload.linhas_basicas || [];
    const focoN = Number(payload.concurso_foco?.concurso);
    atualizarBotaoXls(linhas.length);
    if (nEl) {
      nEl.textContent = linhas.length
        ? `(${linhas.length.toLocaleString('pt-BR')} sorteio${linhas.length === 1 ? '' : 's'})`
        : '';
    }
    if (!tbody) return;
    if (!linhas.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="text-muted">Sem sorteios na janela.</td></tr>';
      return;
    }
    tbody.innerHTML = linhas.map((ln) => {
      if (COM_DIAG && ln.numeros && !ln.diagonais) ln.diagonais = blocoDiag(ln.numeros);
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
        <td class="ev-basic-nums" style="color:${CORES.diagonais}" title="${celulaGrupo('diagonais', ln.diagonais)}">${celulaGrupo('diagonais', ln.diagonais)}</td>
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

  const CHAVES_APOSTA = ['pares', 'impares', 'repetidos', 'sequencias', 'finais', 'diagonais'];
  let apostas = [];
  let apostaSeq = 0;

  function escHtml(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function avisoAposta(msg) {
    const el = document.getElementById('evApostasAviso');
    if (!el) return;
    el.textContent = msg || '';
    el.classList.toggle('d-none', !msg);
  }

  function referenciaReal() {
    const foco = payload && payload.concurso_foco;
    if (!foco || !Array.isArray(foco.numeros)) return null;
    const linhas = (payload && payload.linhas_basicas) || [];
    const pronta = linhas.find((ln) => Number(ln.concurso) === Number(foco.concurso));
    if (pronta) {
      if (COM_DIAG && !pronta.diagonais) pronta.diagonais = blocoDiag(pronta.numeros);
      return pronta;
    }
    const b = foco.basicos || {};
    return {
      concurso: foco.concurso,
      data: foco.data || '',
      mes_num: foco.mes_num || null,
      mes_nome: foco.mes_nome || '',
      numeros: foco.numeros.map(Number),
      pares: b.pares,
      impares: b.impares,
      repetidos: b.repetidos,
      sequencias: b.sequencias,
      finais: b.finais,
      diagonais: b.diagonais || blocoDiag(foco.numeros),
    };
  }

  function analiseAposta(nums) {
    const lista = (nums || []).map((n) => (n == null || n === '' ? null : Number(n)));
    const ok = lista.filter((n) => Number.isFinite(n));
    if (ok.length !== PICK || new Set(ok).size !== PICK) return null;
    if (ok.some((n) => n < DMIN || n > DMAX)) return null;
    const ref = referenciaReal();
    return linhaDeSorteio({ numeros: ok }, (ref && ref.numeros) || []);
  }

  function mesmoPatamar(ap, ref, k) {
    if (!ap || !ref || !ap[k] || !ref[k]) return false;
    return Number(ap[k].quantidade) === Number(ref[k].quantidade);
  }

  function mesDeTexto(linha) {
    const mName = String(linha || '').match(/(Janeiro|Fevereiro|Março|Marco|Abril|Maio|Junho|Julho|Agosto|Setembro|Outubro|Novembro|Dezembro|JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)/i);
    if (!mName) return null;
    const raw = mName[1].toUpperCase().normalize('NFD').replace(/\p{M}/gu, '');
    const idx = MESES_ABREV.findIndex((a) => a === raw.slice(0, 3));
    return idx >= 0 ? idx + 1 : null;
  }

  function mesPadrao() {
    const ref = referenciaReal();
    const m = ref && Number(ref.mes_num);
    return m >= 1 && m <= 12 ? m : 1;
  }

  function abrevMes(m) {
    const a = MESES_ABREV[(Number(m) || 1) - 1] || 'JAN';
    return a.charAt(0) + a.slice(1).toLowerCase();
  }

  function estiloMes(m) {
    const nome = MESES[(Number(m) || 1) - 1] || '';
    const cor = mesesCores[nome];
    if (!cor) return '';
    return ` style="background:${cor};color:#fff;border-color:${cor}"`;
  }

  function novaAposta(nums, mes) {
    const base = Array.isArray(nums) ? nums.slice(0, PICK) : [];
    while (base.length < PICK) base.push(null);
    let m = Number(mes);
    if (!Number.isFinite(m) || m < 1 || m > 12) m = mesPadrao();
    apostas.push({ id: ++apostaSeq, nums: base, mes: m });
  }

  function parseTexto(texto) {
    const out = [];
    String(texto || '').split(/\r?\n/).forEach((linha) => {
      const nums = [];
      const vistos = new Set();
      const re = /\d{1,2}/g;
      let m;
      while ((m = re.exec(linha))) {
        const n = parseInt(m[0], 10);
        if (n < DMIN || n > DMAX || vistos.has(n)) continue;
        vistos.add(n);
        nums.push(n);
        if (nums.length >= PICK) break;
      }
      if (nums.length) out.push({ nums, mes: mesDeTexto(linha) });
    });
    return out;
  }

  function incluirTexto(texto) {
    const lista = parseTexto(texto);
    if (!lista.length) {
      avisoAposta('Nenhuma aposta encontrada no texto.');
      return;
    }
    const cabe = MAX_APOSTAS - apostas.length;
    if (cabe < 1) {
      avisoAposta(`Limite de ${MAX_APOSTAS} apostas.`);
      return;
    }
    lista.slice(0, cabe).forEach((item) => novaAposta(item.nums, item.mes));
    avisoAposta(lista.length > cabe ? `Entraram ${cabe} apostas. O limite é ${MAX_APOSTAS}.` : '');
    renderApostas();
  }

  function casasHtml(ap) {
    const ref = referenciaReal();
    const refSet = new Set(((ref && ref.numeros) || []).map(Number));
    return `<div class="ev-ap-casas">${ap.nums.map((n, i) => {
      const val = n == null ? '' : fmt(n);
      const noReal = n != null && refSet.has(Number(n));
      return `<span class="ev-ap-casa${noReal ? ' is-no-real' : ''}">
        <input class="ev-ap-num" data-id="${ap.id}" data-i="${i}" value="${escHtml(val)}" inputmode="numeric" maxlength="2" aria-label="Dezena ${i + 1}">
        <span class="ev-ap-spin">
          <button type="button" class="ev-ap-step" data-id="${ap.id}" data-i="${i}" data-delta="1" tabindex="-1" aria-label="Aumentar dezena">▲</button>
          <button type="button" class="ev-ap-step" data-id="${ap.id}" data-i="${i}" data-delta="-1" tabindex="-1" aria-label="Diminuir dezena">▼</button>
        </span>
      </span>`;
    }).join('')}</div>`;
  }

  function casasLeitura(nums) {
    const lista = (nums || []).map(Number).filter(Number.isFinite);
    if (!lista.length) return '<span class="text-muted">—</span>';
    return `<div class="ev-ap-casas">${lista.map((n) => `<span class="ev-ap-casa is-ro"><span class="ev-ap-num">${fmt(n)}</span></span>`).join('')}</div>`;
  }

  function mesLeitura(ref) {
    const m = Number(ref && ref.mes_num);
    if (!m) return '<span class="text-muted">—</span>';
    const nome = (ref && ref.mes_nome) || MESES[m - 1] || '';
    return `<span class="ev-ap-casa is-ro ev-ap-mes"${estiloMes(m)} title="${escHtml(nome)}"><span class="ev-ap-mes-label">${escHtml(abrevMes(m))}</span></span>`;
  }

  function mesControle(ap) {
    const m = Number(ap.mes) || mesPadrao();
    const nome = MESES[m - 1] || '';
    return `<span class="ev-ap-casa ev-ap-mes"${estiloMes(m)} title="${escHtml(nome)}">
      <span class="ev-ap-mes-label">${escHtml(abrevMes(m))}</span>
      <span class="ev-ap-spin">
        <button type="button" class="ev-ap-step" data-id="${ap.id}" data-mes-delta="1" tabindex="-1" aria-label="Mês seguinte">▲</button>
        <button type="button" class="ev-ap-step" data-id="${ap.id}" data-mes-delta="-1" tabindex="-1" aria-label="Mês anterior">▼</button>
      </span>
    </span>`;
  }

  function colunasAposta() {
    return 9 + (EXTRA_MES ? 1 : 0);
  }

  function tdsMetrica(an, ref) {
    return CHAVES_APOSTA.map((k) => {
      if (!an) return '<td class="ev-basic-nums text-muted">—</td>';
      const igual = mesmoPatamar(an, ref, k);
      const texto = celulaGrupo(k, an[k]);
      const title = igual ? 'Mesma quantidade do resultado real' : texto;
      return `<td class="ev-basic-nums${igual ? ' is-patamar' : ''}" style="color:${CORES[k]}" title="${escHtml(title)}">${escHtml(texto)}</td>`;
    }).join('');
  }

  function atualizarInfo() {
    const el = document.getElementById('evApostasInfo');
    if (!el) return;
    const ref = referenciaReal();
    const conc = ref ? `concurso ${ref.concurso}` : 'sem concurso';
    const completas = apostas.filter((ap) => analiseAposta(ap.nums)).length;
    el.textContent = apostas.length
      ? `${apostas.length} aposta${apostas.length === 1 ? '' : 's'} · ${completas} completa${completas === 1 ? '' : 's'} · ${conc}`
      : conc;
  }

  function renderApostas() {
    const tbody = document.getElementById('evApostasTabela');
    if (!tbody) return;
    const ref = referenciaReal();
    const mesReal = EXTRA_MES ? `<td class="ev-ap-mes-td">${ref ? mesLeitura(ref) : ''}</td>` : '';
    const cols = colunasAposta();
    const real = ref
      ? `<tr class="ev-ap-real">
          <td class="ev-basic-conc ev-ultimo-ref"><strong>${escHtml(ref.concurso)}</strong>${ref.data ? `<div class="small text-muted">${escHtml(ref.data)}</div>` : ''}</td>
          <td class="ev-ap-dezenas">${casasLeitura(ref.numeros)}</td>
          ${mesReal}
          ${CHAVES_APOSTA.map((k) => `<td class="ev-basic-nums" style="color:${CORES[k]}">${escHtml(celulaGrupo(k, ref[k]))}</td>`).join('')}
          <td></td>
        </tr>`
      : `<tr class="ev-ap-real"><td colspan="${cols}" class="text-muted">Carregando o resultado real…</td></tr>`;
    const corpo = apostas.length
      ? apostas.map((ap, i) => `<tr data-id="${ap.id}">
          <td class="ev-basic-conc">${i + 1}</td>
          <td class="ev-ap-dezenas">${casasHtml(ap)}</td>
          ${EXTRA_MES ? `<td class="ev-ap-mes-td">${mesControle(ap)}</td>` : ''}
          ${tdsMetrica(analiseAposta(ap.nums), ref)}
          <td><button type="button" class="btn btn-sm btn-link text-danger ev-ap-del p-0" data-id="${ap.id}" aria-label="Excluir aposta ${i + 1}">×</button></td>
        </tr>`).join('')
      : `<tr><td colspan="${cols}" class="text-muted">Inclua apostas para aproximar o padrão do resultado real.</td></tr>`;
    tbody.innerHTML = real + corpo;
    atualizarInfo();
  }

  function pintarLinha(id) {
    const tr = document.querySelector(`#evApostasTabela tr[data-id="${id}"]`);
    const ap = apostas.find((item) => item.id === id);
    if (!tr || !ap) {
      renderApostas();
      return;
    }
    const ref = referenciaReal();
    const an = analiseAposta(ap.nums);
    const tds = tr.querySelectorAll('td');
    const offset = EXTRA_MES ? 3 : 2;
    CHAVES_APOSTA.forEach((k, i) => {
      const td = tds[i + offset];
      if (!td) return;
      if (!an) {
        td.textContent = '—';
        td.className = 'ev-basic-nums text-muted';
        td.removeAttribute('style');
        td.removeAttribute('title');
        return;
      }
      const igual = mesmoPatamar(an, ref, k);
      const texto = celulaGrupo(k, an[k]);
      td.textContent = texto;
      td.className = `ev-basic-nums${igual ? ' is-patamar' : ''}`;
      td.style.color = CORES[k];
      td.title = igual ? 'Mesma quantidade do resultado real' : texto;
    });
    const refSet = new Set(((ref && ref.numeros) || []).map(Number));
    tr.querySelectorAll('.ev-ap-num').forEach((inp) => {
      const i = Number(inp.dataset.i);
      const n = ap.nums[i];
      inp.value = n == null ? '' : fmt(n);
      const casa = inp.closest('.ev-ap-casa');
      if (casa) casa.classList.toggle('is-no-real', n != null && refSet.has(Number(n)));
    });
    atualizarInfo();
  }

  function definirCasa(id, i, valor) {
    const ap = apostas.find((item) => item.id === id);
    if (!ap) return;
    const texto = String(valor == null ? '' : valor).trim();
    if (!texto) {
      ap.nums[i] = null;
      avisoAposta('');
      pintarLinha(id);
      return;
    }
    let n = parseInt(texto, 10);
    if (!Number.isFinite(n)) {
      pintarLinha(id);
      return;
    }
    n = Math.min(DMAX, Math.max(DMIN, n));
    if (ap.nums.some((v, j) => j !== i && Number(v) === n)) {
      avisoAposta(`A dezena ${fmt(n)} já está nesta aposta.`);
      pintarLinha(id);
      return;
    }
    ap.nums[i] = n;
    avisoAposta('');
    pintarLinha(id);
  }

  function definirMes(id, delta) {
    const ap = apostas.find((item) => item.id === id);
    if (!ap) return;
    let m = Number(ap.mes);
    if (!Number.isFinite(m) || m < 1 || m > 12) m = 1;
    m = ((m - 1 + Number(delta || 0)) % 12 + 12) % 12 + 1;
    ap.mes = m;
    const tr = document.querySelector(`#evApostasTabela tr[data-id="${id}"]`);
    const casa = tr && tr.querySelector('.ev-ap-mes');
    if (!casa) return;
    const nome = MESES[m - 1] || '';
    casa.title = nome;
    casa.setAttribute('style', estiloMes(m).replace(/^ style="|"$/g, ''));
    const lab = casa.querySelector('.ev-ap-mes-label');
    if (lab) lab.textContent = abrevMes(m);
  }

  function exportarApostas() {
    const linhas = [];
    apostas.forEach((ap) => {
      if (!analiseAposta(ap.nums)) return;
      const nums = ap.nums.map(Number).filter(Number.isFinite).slice().sort((a, b) => a - b);
      let line = nums.map(fmt).join(' ');
      if (EXTRA_MES) line += ` ${abrevMes(ap.mes)}`;
      linhas.push(line);
    });
    if (!linhas.length) {
      avisoAposta('Nenhuma aposta válida para exportar.');
      return;
    }
    avisoAposta('');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([`${linhas.join('\n')}\n`], { type: 'text/plain' }));
    a.download = 'escolha_visual_apostas.txt';
    a.click();
  }

  function bindApostas() {
    const drop = document.getElementById('evApostasDrop');
    const texto = document.getElementById('evApostasTexto');
    const arquivo = document.getElementById('evApostasArquivo');
    document.getElementById('evApostasProcessar')?.addEventListener('click', () => {
      incluirTexto(texto ? texto.value : '');
    });
    document.getElementById('evApostasAdd')?.addEventListener('click', () => {
      const qtd = Math.min(MAX_APOSTAS, Math.max(1, parseInt(document.getElementById('evApostasQtd')?.value, 10) || 1));
      const cabe = MAX_APOSTAS - apostas.length;
      const n = Math.min(qtd, cabe);
      if (!n) {
        avisoAposta(`Limite de ${MAX_APOSTAS} apostas.`);
        return;
      }
      for (let i = 0; i < n; i += 1) novaAposta(null);
      avisoAposta(n < qtd ? `Entraram ${n} linhas. O limite é ${MAX_APOSTAS}.` : '');
      renderApostas();
    });
    document.getElementById('evApostasExportar')?.addEventListener('click', exportarApostas);
    document.getElementById('evApostasLimpar')?.addEventListener('click', () => {
      apostas = [];
      if (texto) texto.value = '';
      avisoAposta('');
      renderApostas();
    });
    arquivo?.addEventListener('change', () => {
      const file = arquivo.files && arquivo.files[0];
      arquivo.value = '';
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => incluirTexto(String(reader.result || ''));
      reader.readAsText(file);
    });
    function ligarDrop(el) {
      if (!el) return;
      ['dragenter', 'dragover'].forEach((nome) => {
        el.addEventListener(nome, (ev) => {
          ev.preventDefault();
          el.classList.add('is-over');
        });
      });
      ['dragleave', 'drop'].forEach((nome) => {
        el.addEventListener(nome, (ev) => {
          ev.preventDefault();
          el.classList.remove('is-over');
        });
      });
      el.addEventListener('drop', (ev) => {
        const file = ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0];
        if (file) {
          const reader = new FileReader();
          reader.onload = () => incluirTexto(String(reader.result || ''));
          reader.readAsText(file);
          return;
        }
        incluirTexto(ev.dataTransfer ? ev.dataTransfer.getData('text') : '');
      });
    }
    ligarDrop(drop);
    ligarDrop(texto);
    document.getElementById('evApostasTabela')?.addEventListener('click', (ev) => {
      const del = ev.target.closest('.ev-ap-del');
      if (del) {
        const id = Number(del.dataset.id);
        apostas = apostas.filter((ap) => ap.id !== id);
        avisoAposta('');
        renderApostas();
        return;
      }
      const step = ev.target.closest('.ev-ap-step');
      if (!step) return;
      if (step.dataset.mesDelta != null) {
        definirMes(Number(step.dataset.id), Number(step.dataset.mesDelta));
        return;
      }
      const id = Number(step.dataset.id);
      const i = Number(step.dataset.i);
      const ap = apostas.find((item) => item.id === id);
      if (!ap) return;
      const atual = ap.nums[i] == null ? DMIN - 1 : Number(ap.nums[i]);
      definirCasa(id, i, atual + Number(step.dataset.delta));
    });
    document.getElementById('evApostasTabela')?.addEventListener('change', (ev) => {
      const inp = ev.target.closest('.ev-ap-num');
      if (!inp) return;
      definirCasa(Number(inp.dataset.id), Number(inp.dataset.i), inp.value);
    });
    renderApostas();
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
    document.getElementById('evStatBasicosXls')?.addEventListener('click', baixarBasicosServidor);
    const pathEl = document.getElementById('evStatBasicosPath');
    if (pathEl && !pathEl.textContent.trim()) {
      const caminho = caminhoPadrao();
      if (caminho) pathEl.textContent = caminho;
    }
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
    bindApostas();

    const qsPagina = new URLSearchParams(window.location.search);
    if (qsPagina.get('aba') === 'estatisticas' || qsPagina.get('embed') === '1') {
      const tabBtn = document.getElementById('ev-tab-estatisticas');
      if (tabBtn && window.bootstrap && bootstrap.Tab) {
        bootstrap.Tab.getOrCreateInstance(tabBtn).show();
      } else if (tabBtn) {
        tabBtn.click();
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
