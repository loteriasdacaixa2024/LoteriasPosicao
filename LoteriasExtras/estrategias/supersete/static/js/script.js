/**
 * SuperSet Estratégia 1 — JavaScript Principal
 * ==============================================
 * Lógica do frontend com comunicação ao backend Flask via API REST.
 * Distribuição rotacional, detecção de acertos e exportação.
 */

/* ══════════════════════════════════════════════════
   CONSTANTES
   ══════════════════════════════════════════════════ */

var COLUMNS = 7;

var PRIZE_TIERS = {
  3: { name: "3 acertos", value: "R$ 5,00" },
  4: { name: "4 acertos", value: "R$ 50,00" },
  5: { name: "5 acertos", value: "R$ 1.000,00" },
  6: { name: "6 acertos", value: "R$ 20.000,00" },
  7: { name: "7 acertos", value: "Prêmio Principal" }
};

/* ══════════════════════════════════════════════════
   DARK MODE DETECTION
   ══════════════════════════════════════════════════ */

if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
  document.documentElement.classList.add("dark");
}
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function (event) {
  if (event.matches) {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
});

/* ══════════════════════════════════════════════════
   APPLICATION STATE (client-side mirror)
   ══════════════════════════════════════════════════ */

var state = {
  sequence: [],
  matrices: [],
  matrixCounter: 0,
  hybridMode: false,
  recentConcursos: [],
  ranking: [],
  rankingColumns: [],
  selectedNucleus: [],
  selectedNucleusE3: [[], [], [], [], [], [], []],
  selectedDigitsE4: [],
  analysisResults: null
};

/* ══════════════════════════════════════════════════
   UTILITY FUNCTIONS
   ══════════════════════════════════════════════════ */

function showToast(msg) {
  var toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(function () {
    toast.classList.remove("show");
  }, 2600);
}

function showConfirmDialog(title, message, onConfirm) {
  var existing = document.querySelector(".modal-overlay");
  if (existing) existing.remove();

  var overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML =
    '<div class="modal-box">' +
    '<div class="modal-title">' + title + "</div>" +
    '<div class="modal-text">' + message + "</div>" +
    '<div class="modal-actions">' +
    '<button class="btn btn-secondary btn-sm modal-cancel-btn">Cancelar</button>' +
    '<button class="btn btn-danger btn-sm modal-confirm-btn">Confirmar</button>' +
    "</div></div>";
  document.body.appendChild(overlay);

  overlay.querySelector(".modal-cancel-btn").addEventListener("click", function () {
    overlay.remove();
  });
  overlay.querySelector(".modal-confirm-btn").addEventListener("click", function () {
    overlay.remove();
    onConfirm();
  });
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) overlay.remove();
  });
}

function escapeHtml(str) {
  var div = document.createElement("div");
  div.appendChild(document.createTextNode(String(str)));
  return div.innerHTML;
}

function showStrategyGuide() {
  var existing = document.querySelector(".modal-overlay");
  if (existing) existing.remove();

  var overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML =
    '<div class="modal-box large" style="max-height: 90vh; overflow-y: auto;">' +
    '<div class="modal-title" style="position: sticky; top: 0; background: var(--modal-bg); z-index: 10; padding-bottom: 15px; border-bottom: 1px solid var(--border-light);">' +
    '<i class="fa-solid fa-circle-info"></i> Central de Ajuda: Estratégias & Análises</div>' +

    '<div class="guide-tabs" style="display: flex; gap: 10px; margin-top: 20px; margin-bottom: 20px;">' +
    '<button class="guide-tab-btn active" data-tab="estrategias" onclick="switchGuideTab(\'estrategias\')">Estratégias de Jogo</button>' +
    '<button class="guide-tab-btn" data-tab="analises" onclick="switchGuideTab(\'analises\')">Módulos de Análise</button>' +
    '</div>' +

    '<div id="guide-estrategias" class="guide-tab-content active">' +
    '<div class="guide-content">' +
    '<div class="guide-item"><h4><i class="fa-solid fa-layer-group"></i> Estratégia 1 — Sequência Base</h4><p>Cria matrizes a partir de uma <strong>sequência personalizada</strong> (mín. 9 dígitos). Ideal para quem já possui um palpite estruturado.</p></div>' +
    '<div class="guide-item"><h4><i class="fa-solid fa-flask"></i> Estratégia 2 — Núcleo Estratégico</h4><p>Utiliza os <strong>dígitos mais frequentes</strong> da história. Foca na "Tendência Global" para preencher as colunas.</p></div>' +
    '<div class="guide-item"><h4><i class="fa-solid fa-chart-line"></i> Estratégia 3 — Ranking por Coluna</h4><p>Analisa a <strong>frequência por posição</strong> (1 a 7). Cria uma matriz de alta precisão baseada no histórico local.</p></div>' +
    '<div class="guide-item"><h4><i class="fa-solid fa-shapes"></i> Estratégia 4 — Restrição de 5 Dígitos <span class="badge">Especialista</span></h4><p>Foca na <strong>concentração numérica</strong>. Força repetições estratégicas para maximizar acertos múltiplos.</p></div>' +
    '<div class="guide-item" style="border-color: var(--gold); background: rgba(212, 175, 55, 0.05);"><h4><i class="fa-solid fa-arrows-spin"></i> O Poder do Modo Híbrido</h4><p>Permite o <strong>deslocamento de colunas</strong> para rotacionar a matriz e encontrar o melhor encaixe histórico.</p></div>' +
    '</div>' +
    '</div>' +

    '<div id="guide-analises" class="guide-tab-content" style="display:none;">' +
    '<div class="guide-content">' +
    '<div class="guide-item"><h4><i class="fa-solid fa-dna"></i> Análise 1 — <strong>Composição</strong></h4><p>Avalia quantos <strong>números distintos</strong> (ex: 7 diferentes) saem por concurso e identifica <strong>padrões de repetição interna</strong> (ex: trincas na mesma linha).</p></div>' +
    '<div class="guide-item"><h4><i class="fa-solid fa-table-columns"></i> Análise 2 — <strong>Colunas</strong></h4><p>Exibe um <strong>mapa térmico detalhado</strong> mostrando a freqüência de cada dígito em <strong>cada uma das 7 colunas</strong> isoladamente.</p></div>' +
    '<div class="guide-item"><h4><i class="fa-solid fa-qrcode"></i> Análise 3 — <strong>Estrutural</strong></h4><p>Categoriza o histórico por <strong>padrões estruturais de repetição</strong>, informando se o sorteio teve <strong>Duplas, Trincas ou Quadras</strong> recorrentes.</p></div>' +
    '<div class="guide-item"><h4><i class="fa-solid fa-bullseye"></i> Análise 4 — <strong>Concentração</strong></h4><p>Mede a <strong>concentração estratégica</strong> do período, revelando se os sorteios estão focados em um <strong>pequeno grupo de dígitos</strong>.</p></div>' +
    '<div class="guide-item"><h4><i class="fa-solid fa-scale-balanced"></i> Análise 5 — <strong>Pares e Ímpares</strong></h4><p>Faz o levantamento do <strong>equilíbrio de paridade</strong>, mostrando o percentual exato de <strong>Pares e Ímpares</strong> sorteados por concurso.</p></div>' +
    '<div class="guide-item"><h4><i class="fa-solid fa-list-ul"></i> Análise 6 — <strong>Repetição Detalhada</strong></h4><p>Exibe o <strong>ranking de persistência</strong>, identificando quais dígitos tendem a <strong>aparecer consecutivamente</strong> entre um concurso e outro.</p></div>' +
    '</div>' +
    '</div>' +

    '<div class="modal-actions" style="margin-top:30px; display: flex !important; justify-content: center !important; align-items: center !important; position: sticky; bottom: 0; background: var(--modal-bg); padding-top: 20px; border-top: 1px solid var(--border-light); width: 100%; box-sizing: border-box;">' +
    '<button class="btn btn-primary btn-lg modal-close-btn" style="width: 220px; text-align: center; justify-content: center; display: flex; align-items: center; box-shadow: 0 4px 15px var(--accent-glow);">Entendido!</button>' +
    '</div></div>';
  document.body.appendChild(overlay);

  overlay.querySelector(".modal-close-btn").addEventListener("click", function () {
    overlay.remove();
  });
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) overlay.remove();
  });
}

function switchGuideTab(tab) {
  document.querySelectorAll(".guide-tab-btn").forEach(function (btn) {
    if (btn.getAttribute("data-tab") === tab) btn.classList.add("active");
    else btn.classList.remove("active");
  });
  document.querySelectorAll(".guide-tab-content").forEach(function (content) {
    if (content.id === "guide-" + tab) content.style.display = "block";
    else content.style.display = "none";
  });
}

/* ══════════════════════════════════════════════════
   API HELPERS
   ══════════════════════════════════════════════════ */

function appRoot() {
  var el = document.querySelector('meta[name="app-root"]');
  var meta = ((el && el.getAttribute("content")) || "").replace(/\/$/, "");
  if (meta) return meta;
  var parts = (window.location.pathname || "").split("/").filter(Boolean);
  if (parts[0] === "estrategias" && parts[1] && parts[1] !== "static") {
    return "/estrategias/" + parts[1];
  }
  if (parts[0] === "estrategias") return "/estrategias";
  return "";
}

function apiPath(url) {
  if (url.charAt(0) === "/") return appRoot() + url;
  return url;
}

function api(method, url, data) {
  url = apiPath(url);
  var opts = {
    method: method,
    headers: { "Content-Type": "application/json" }
  };
  if (data !== undefined) {
    opts.body = JSON.stringify(data);
  }
  return fetch(url, opts).then(function (res) {
    if (!res.ok) throw new Error("API error: " + res.status);
    return res.json();
  });
}

/* ══════════════════════════════════════════════════
   DISTRIBUTION LOGIC (client-side for instant UI)
   ══════════════════════════════════════════════════ */

function computeDistribution(sequence, startCol) {
  var N = sequence.length;
  if (N === 0) return [];
  var sc = startCol || 0;
  var rows = [];
  for (var i = 0; i < N; i++) {
    var row = [];
    for (var j = 0; j < COLUMNS; j++) {
      var shift = (j - sc + COLUMNS) % COLUMNS;
      var seqIndex = (i + shift) % N;
      row.push(sequence[seqIndex]);
    }
    rows.push(row);
  }
  return rows;
}

function computeHits(rows, result) {
  var rowHits = [];
  var bestHits = 0;
  var bestRowIdx = -1;
  for (var i = 0; i < rows.length; i++) {
    var hits = 0;
    var hitCols = [];
    for (var j = 0; j < COLUMNS; j++) {
      if (result[j] !== null && result[j] !== undefined && rows[i][j] === result[j]) {
        hits++;
        hitCols.push(j);
      }
    }
    rowHits.push({ hits: hits, hitCols: hitCols });
    if (hits > bestHits) {
      bestHits = hits;
      bestRowIdx = i;
    }
  }
  return { rowHits: rowHits, bestHits: bestHits, bestRowIdx: bestRowIdx };
}

/* ══════════════════════════════════════════════════
   SEQUENCE MANAGEMENT
   ══════════════════════════════════════════════════ */

function initDigitButtons() {
  var container = document.getElementById("digitButtons");
  container.innerHTML = "";
  for (var d = 0; d <= 9; d++) {
    var btn = document.createElement("button");
    btn.className = "digit-btn";
    btn.textContent = d;
    btn.setAttribute("data-digit", d);
    if (state.sequence.indexOf(d) !== -1) {
      btn.classList.add("selected");
    }
    btn.addEventListener("click", handleDigitClick);
    container.appendChild(btn);
  }
}

function handleDigitClick(e) {
  var digit = parseInt(e.target.getAttribute("data-digit"), 10);
  state.sequence.push(digit);
  syncSequenceUI();
  saveSequenceToServer();
  renderAllMatrices();
}

function applyManualSequence() {
  var input = document.getElementById("seqManualInput");
  var val = input.value.trim();
  if (!val) return;

  var newSeq = [];
  for (var i = 0; i < val.length; i++) {
    var ch = val[i];
    if (ch >= "0" && ch <= "9") {
      var num = parseInt(ch, 10);
      newSeq.push(num);
    }
  }
  if (newSeq.length < 9) {
    showToast("A sequência deve ter pelo menos 9 dígitos");
    return;
  }
  state.sequence = newSeq;
  input.value = "";
  syncSequenceUI();
  saveSequenceToServer();
  renderAllMatrices();
  showToast("Sequência aplicada: " + newSeq.join(" "));
}

function clearSequence() {
  state.sequence = [];
  syncSequenceUI();
  saveSequenceToServer();
  renderAllMatrices();
  showToast("Sequência limpa");
}

function syncSequenceUI() {
  initDigitButtons();
  var display = document.getElementById("seqDisplay");
  var label = document.querySelector(".sub-label");
  if (state.sequence.length === 0) {
    if (label) label.style.display = "none";
    display.className = "sequence-display empty";
    display.textContent = "Nenhum dígito selecionado";
    return;
  }
  if (label) label.style.display = "block";
  display.className = "sequence-display";
  display.innerHTML = "";
  for (var i = 0; i < state.sequence.length; i++) {
    if (i > 0) {
      var arrow = document.createElement("span");
      arrow.className = "seq-arrow";
      arrow.innerHTML = '<i class="fa-solid fa-arrow-right"></i>';
      display.appendChild(arrow);
    }
    var chip = document.createElement("span");
    chip.className = "seq-chip";
    chip.textContent = state.sequence[i];
    chip.setAttribute("data-index", i);
    chip.setAttribute("title", "Clique para remover este dígito");
    chip.addEventListener("click", function () {
      var idx = parseInt(this.getAttribute("data-index"), 10);
      state.sequence.splice(idx, 1);
      syncSequenceUI();
      saveSequenceToServer();
      renderAllMatrices();
    });
    display.appendChild(chip);
  }
}

function saveSequenceToServer() {
  api("PUT", "/api/sequence", { sequence: state.sequence }).catch(function (err) {
    console.log("Erro ao salvar sequência: " + err.message);
  });
}

/* ══════════════════════════════════════════════════
   MATRIX OPERATIONS
   ══════════════════════════════════════════════════ */

function addMatrix() {
  api("POST", "/api/matrix").then(function (matrix) {
    // Update local state with server sequence
    matrix.sequence = state.sequence;
    state.matrices.push(matrix);
    renderAllMatrices();
    showToast(matrix.name + " criada");
    setTimeout(function () {
      var card = document.getElementById("matrix-" + matrix.id);
      if (card) card.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  }).catch(function (err) {
    showToast("Erro ao criar matriz: " + err.message);
  });
}

function deleteMatrix(id) {
  var matrix = state.matrices.find(function (m) { return m.id === id; });
  if (!matrix) return;
  showConfirmDialog(
    "Excluir " + matrix.name + "?",
    "Esta ação removerá a matriz e todos os seus dados. Deseja continuar?",
    function () {
      api("DELETE", "/api/matrix/" + id).then(function () {
        state.matrices = state.matrices.filter(function (m) { return m.id !== id; });
        renderAllMatrices();
        showToast(matrix.name + " excluída");
      }).catch(function (err) {
        showToast("Erro ao excluir: " + err.message);
      });
    }
  );
}

function updateResult(matrixId, colIdx, value) {
  var matrix = state.matrices.find(function (m) { return m.id === matrixId; });
  if (!matrix) return;

  if (value === "" || value === null || value === undefined) {
    matrix.result[colIdx] = null;
  } else {
    var num = parseInt(value, 10);
    if (!isNaN(num) && num >= 0 && num <= 9) {
      matrix.result[colIdx] = num;
    }
  }

  // Save to server
  api("PUT", "/api/matrix/" + matrixId + "/result", { result: matrix.result }).catch(function (err) {
    console.log("Erro ao salvar resultado: " + err.message);
  });

  renderMatrixGrid(matrixId);
}

function setStartCol(matrixId, col) {
  var matrix = state.matrices.find(function (m) { return m.id === matrixId; });
  if (!matrix) return;

  // Atualização local imediata (reatividade instantânea)
  matrix.start_col = col;
  renderMatrixGrid(matrixId);

  // Sincronização visual imediata dos botões
  var cardElement = document.getElementById("matrix-" + matrixId);
  if (cardElement) {
    var btns = cardElement.querySelectorAll(".start-col-btn");
    btns.forEach(function (btn, idx) {
      if (idx === col) btn.classList.add("active");
      else btn.classList.remove("active");
    });
  }

  // Persistência no servidor
  api("PUT", "/api/matrix/" + matrixId + "/start-col", { startCol: col }).then(function (res) {
    if (res.success && res.matrix) {
      // Sincroniza com dados oficiais do servidor
      // Map startCol (DB) to start_col (JS state)
      matrix.start_col = (res.matrix.startCol !== undefined) ? res.matrix.startCol : res.matrix.start_col;

      // Apenas para E2/E3/E4 o grid é atualizado pelo server. Para E1 é reativo no front.
      if (res.matrix.grid) matrix.grid = res.matrix.grid;

      matrix.hits_count = res.matrix.hitsCount;
      matrix.best_row = res.matrix.bestRow;

      // Re-render para garantir sincronia final
      renderMatrixGrid(matrixId);
    }
  }).catch(function (err) {
    console.log("Erro ao salvar coluna: " + err.message);
  });
}

/* ══════════════════════════════════════════════════
   RENDERING
   ══════════════════════════════════════════════════ */

function renderAllMatrices() {
  var container1 = document.getElementById("matricesContainer");
  var container2 = document.getElementById("matricesContainerV2");
  var container3 = document.getElementById("matricesContainerV3");

  var mats1 = state.matrices.filter(function (m) { return m.strategy_type === 1 || !m.strategy_type; });
  var mats2 = state.matrices.filter(function (m) { return m.strategy_type === 2; });
  var mats3 = state.matrices.filter(function (m) { return m.strategy_type === 3; });

  // Render Container 1
  if (container1) {
    if (mats1.length === 0) {
      container1.innerHTML = '<div class="empty-state"><i class="fa-solid fa-table-cells-large"></i><h3>Nenhuma matriz criada</h3><p>Clique em "Adicionar Matriz" para começar</p></div>';
    } else {
      container1.innerHTML = "";
      mats1.forEach(function (matrix) { container1.appendChild(buildMatrixCard(matrix)); });
    }
  }

  // Render Container 2
  if (container2) {
    if (mats2.length === 0) {
      container2.innerHTML = '<div class="empty-state"><i class="fa-solid fa-flask"></i><h3>Nenhuma matriz gerada</h3><p>Escolha o núcleo e clique em "Gerar Matriz"</p></div>';
    } else {
      container2.innerHTML = "";
      mats2.forEach(function (matrix) { container2.appendChild(buildMatrixCard(matrix)); });
    }
  }

  // Render Container 3
  if (container3) {
    if (mats3.length === 0) {
      container3.innerHTML = '<div class="empty-state"><i class="fa-solid fa-chart-line"></i><h3>Nenhuma matriz gerada</h3><p>Escolha o ranking por coluna e clique em "Gerar Matriz"</p></div>';
    } else {
      container3.innerHTML = "";
      mats3.forEach(function (matrix) { container3.appendChild(buildMatrixCard(matrix)); });
    }
  }

  // Render Container 4
  var container4 = document.getElementById("matricesContainerV4");
  if (container4) {
    var mats4 = state.matrices.filter(function (m) { return m.strategy_type === 4; });
    if (mats4.length === 0) {
      container4.innerHTML = '<div class="empty-state"><i class="fa-solid fa-shapes"></i><h3>Nenhuma matriz gerada</h3><p>Selecione 5 dígitos e clique em "Gerar Matriz"</p></div>';
    } else {
      container4.innerHTML = "";
      mats4.forEach(function (matrix) { container4.appendChild(buildMatrixCard(matrix)); });
    }
  }
}

function buildMatrixCard(matrix) {
  var card = document.createElement("div");
  card.className = "matrix-card";
  card.id = "matrix-" + matrix.id;

  // Header
  var header = document.createElement("div");
  header.className = "matrix-header";

  var displayId = matrix.name.replace(/\D/g, "") || matrix.id;
  header.innerHTML =
    '<div class="matrix-title-group">' +
    '<div class="matrix-number">' + displayId + "</div>" +
    '<span class="matrix-name">' + escapeHtml(matrix.name) + "</span>" +
    "</div>" +
    '<div class="matrix-actions">' +
    '<button class="btn btn-secondary btn-xs export-txt-btn" data-id="' + matrix.id + '" title="Exportar TXT">' +
    '<i class="fa-solid fa-file-lines"></i> TXT</button>' +
    '<button class="btn btn-secondary btn-xs export-xml-btn" data-id="' + matrix.id + '" title="Exportar XML">' +
    '<i class="fa-solid fa-code"></i> XML</button>' +
    '<button class="btn btn-secondary btn-xs export-html-btn" data-id="' + matrix.id + '" title="Exportar HTML">' +
    '<i class="fa-solid fa-globe"></i> HTML</button>' +
    '<button class="btn btn-danger btn-xs delete-matrix-btn" data-id="' + matrix.id + '" title="Excluir">' +
    '<i class="fa-solid fa-trash-can"></i></button>' +
    "</div>";
  card.appendChild(header);

  // Body
  var body = document.createElement("div");
  body.className = "matrix-body";

  // Concurso row
  var concRow = document.createElement("div");
  concRow.className = "concurso-row";

  var selectOptions = '<option value="">Selecionar...</option>';
  if (state.recentConcursos && state.recentConcursos.length > 0) {
    state.recentConcursos.forEach(function (c) {
      selectOptions += '<option value="' + c + '"' + (matrix.concurso == c ? ' selected' : '') + '>Conc. ' + c + '</option>';
    });
  }

  concRow.innerHTML =
    '<span class="concurso-label">Concurso Nº:</span>' +
    '<div class="concurso-controls">' +
    '<input type="text" class="concurso-input" data-matrix="' + matrix.id + '" placeholder="0000" value="' + escapeHtml(matrix.concurso || "") + '" inputmode="numeric" list="concursosList">' +
    '<select class="concurso-select" data-matrix="' + matrix.id + '">' + selectOptions + '</select>' +
    '</div>' +
    '<button class="btn btn-primary btn-xs sync-api-btn" data-matrix="' + matrix.id + '" title="Sincronizar com Caixa">' +
    '<i class="fa-solid fa-rotate"></i> Sincronizar</button>';
  body.appendChild(concRow);

  // Resumo da matriz (hits, etc) - RESTAURADO AO TOPO
  var summaryArea = document.createElement("div");
  summaryArea.id = "summary-area-" + matrix.id;
  body.appendChild(summaryArea);

  // Result section
  var resultSection = document.createElement("div");
  resultSection.className = "result-section";
  resultSection.innerHTML =
    '<div class="result-section-header">' +
    '<div class="result-label"><i class="fa-solid fa-trophy"></i> Resultado do Sorteio</div>' +
    '<button class="btn-clear-result" data-matrix="' + matrix.id + '"><i class="fa-solid fa-eraser"></i> Limpar</button>' +
    '</div>';
  var resultInputs = document.createElement("div");
  resultInputs.className = "result-inputs";
  for (var c = 0; c < COLUMNS; c++) {
    var colGroup = document.createElement("div");
    colGroup.className = "result-col-group";
    var resultVal = (matrix.result && matrix.result[c] !== null && matrix.result[c] !== undefined) ? matrix.result[c] : "";
    colGroup.innerHTML =
      '<div class="result-col-label">COL ' + (c + 1) + "</div>" +
      '<input type="text" class="result-input" data-matrix="' + matrix.id + '" data-col="' + c + '" ' +
      'maxlength="1" inputmode="numeric" placeholder="–" ' +
      'value="' + resultVal + '">';
    resultInputs.appendChild(colGroup);
  }
  resultSection.appendChild(resultInputs);
  body.appendChild(resultSection);

  // Hybrid start column (Directly following Strategy 1 pattern)
  var isE1 = (matrix.strategy_type === 1 || !matrix.strategy_type);
  var isE2 = (matrix.strategy_type === 2);
  var isE3 = (matrix.strategy_type === 3);
  var isE4 = (matrix.strategy_type === 4);

  var showHybridRow = false;
  if (isE1 && state.hybridMode) showHybridRow = true;
  if (isE2 && state.hybridModeE2) showHybridRow = true;
  if (isE3 && state.hybridModeE3) showHybridRow = true;
  if (isE4 && state.hybridModeE4) showHybridRow = true;
  // Individual matrix override (if it was created hybrid)
  if (matrix.isHybrid) showHybridRow = true;

  if (showHybridRow) {
    var startRow = document.createElement("div");
    startRow.className = "start-col-row";
    var btnsHtml = '<span class="start-col-label"><i class="fa-solid fa-arrows-to-dot"></i> Coluna inicial:</span><div class="start-col-btns">';
    for (var i = 0; i < 7; i++) {
      var active = (matrix.start_col === i) ? "active" : "";
      btnsHtml += '<button class="start-col-btn ' + active + '" onclick="setStartCol(' + matrix.id + ', ' + i + ')">' + (i + 1) + '</button>';
    }
    btnsHtml += '</div>';
    startRow.innerHTML = btnsHtml;
    body.appendChild(startRow);
  }

  // Grid area
  var gridArea = document.createElement("div");
  gridArea.id = "grid-area-" + matrix.id;
  body.appendChild(gridArea);

  // API Details area
  var apiDetailsArea = document.createElement("div");
  apiDetailsArea.id = "api-details-" + matrix.id;
  apiDetailsArea.className = "api-details-area";
  body.appendChild(apiDetailsArea);

  card.appendChild(body);

  // Render grid after card is built
  var matId = matrix.id;
  setTimeout(function () { renderMatrixGrid(matId); }, 0);

  return card;
}

function renderMatrixGrid(matrixId) {
  var matrix = state.matrices.find(function (m) { return m.id === matrixId; });
  if (!matrix) return;

  var gridArea = document.getElementById("grid-area-" + matrixId);
  var summaryArea = document.getElementById("summary-area-" + matrixId);
  if (!gridArea || !summaryArea) return;

  var rows = [];
  var currentSeq = matrix.sequence || [];
  var strategy = matrix.strategy_type || 1;

  if (matrix.grid && matrix.grid.length > 0) {
    // ESTRATÉGIA 2 ou 3: Usa o grid pré-calculado do servidor
    rows = matrix.grid;
  } else {
    // ESTRATÉGIA 1: Usa lógica rotacional (reativa ao painel global)
    if (strategy === 1) {
      currentSeq = state.sequence;
    }

    if (currentSeq.length < 9 && strategy === 1) {
      gridArea.innerHTML =
        '<div class="no-sequence-msg">' +
        '<i class="fa-solid fa-keyboard"></i>' +
        "Selecione pelo menos 9 dígitos no painel de controle" +
        "</div>";
      summaryArea.innerHTML = "";
      return;
    }
    rows = computeDistribution(currentSeq, matrix.start_col || 0);
  }

  var hitsData = computeHits(rows, matrix.result || []);
  var hasResult = (matrix.result || []).some(function (v) { return v !== null && v !== undefined; });

  // Build table
  var html = '<div class="grid-wrapper"><table class="dist-grid"><thead><tr>';
  for (var h = 1; h <= COLUMNS; h++) {
    html += "<th>COL " + h + "</th>";
  }
  html += "<th>Acertos</th></tr></thead><tbody>";

  for (var i = 0; i < rows.length; i++) {
    var rowData = hitsData.rowHits[i];
    var isBestRow = hasResult && hitsData.bestHits >= 3 && i === hitsData.bestRowIdx;
    html += '<tr class="' + (isBestRow ? "best-row-highlight" : "") + '">';
    for (var j = 0; j < COLUMNS; j++) {
      var isHit = hasResult && rowData.hitCols.indexOf(j) !== -1;
      var cls = isHit ? "hit" : "";
      var rowAttr = (j === 0) ? ' data-row-num="' + (i + 1) + '"' : '';
      html += '<td class="' + cls + '" data-value="' + rows[i][j] + '"' + rowAttr + '></td>';
    }
    var hitsCls = "hits-col";
    if (hasResult && rowData.hits > 0) hitsCls += " has-hits";
    if (isBestRow) hitsCls += " best-row";
    html += '<td class="' + hitsCls + '"><span>' + (hasResult ? rowData.hits : "—") + "</span></td>";
    html += "</tr>";
  }
  html += "</tbody></table></div>";
  gridArea.innerHTML = html;

  // Summary reconstruction (Always show structure)
  var tier = PRIZE_TIERS[hitsData.bestHits || 0];
  var tierName = hasResult ? (tier ? tier.name : hitsData.bestHits + " acerto" + (hitsData.bestHits > 1 ? "s" : "")) : "Aguardando Sorteio";
  var tierValue = hasResult ? (tier ? tier.value : "—") : "—";
  var valueLabel = "Valor Estimado";

  // Tenta buscar valor real se houver detalhes do rateio sincronizados
  if (hasResult && matrix.rateioDetail && matrix.rateioDetail.length > 0) {
    var realRateio = matrix.rateioDetail.find(function (r) {
      // Super Sete: 7 acertos = faixa 1, 6 = 2, 5 = 3, 4 = 4, 3 = 5
      return (8 - r.faixa) === hitsData.bestHits;
    });
    if (realRateio && realRateio.valor !== undefined) {
      tierValue = formatCurrency(realRateio.valor);
      valueLabel = "Valor Real";
    }
  }

  var tierColor = (hasResult && hitsData.bestHits >= 3) ? "gold" : "";

  var seqLabel = "Sequência";
  var seqDisplay = currentSeq.join(" ");
  var seqSub = currentSeq.length + " dígitos";

  if (strategy === 2) {
    seqLabel = "Núcleo";
    seqDisplay = currentSeq.join(", ");
    seqSub = "Base Histórica";
  } else if (strategy === 3) {
    seqLabel = "Seleção";
    seqDisplay = "Multicolunas";
    seqSub = "Ranking Local";
  } else if (strategy === 4) {
    seqLabel = "Restrição";
    seqDisplay = currentSeq.join(", ");
    seqSub = "5 Dígitos";
  }

  summaryArea.innerHTML =
    '<div class="matrix-summary">' +
    '<div class="summary-item">' +
    '<div class="summary-label">Melhor Linha</div>' +
    '<div class="summary-value accent">' + (hasResult && hitsData.bestRowIdx !== -1 ? hitsData.bestRowIdx + 1 : "—") + "</div>" +
    '<div class="summary-sub">de ' + rows.length + " linhas</div></div>" +
    '<div class="summary-item">' +
    '<div class="summary-label">Acertos</div>' +
    '<div class="summary-value ' + tierColor + '">' + (hasResult ? hitsData.bestHits : "—") + "</div>" +
    '<div class="summary-sub">' + escapeHtml(tierName) + "</div></div>" +
    '<div class="summary-item">' +
    '<div class="summary-label">' + valueLabel + '</div>' +
    '<div class="summary-value ' + (hasResult && hitsData.bestHits >= 3 ? "gold" : "") + '">' + tierValue + "</div>" +
    '<div class="summary-sub">' + (hasResult && hitsData.bestHits >= 3 ? "Faixa premiada" : "Mín. 3 acertos") + "</div></div>" +
    '<div class="summary-item">' +
    '<div class="summary-label">' + seqLabel + '</div>' +
    '<div class="summary-value" style="font-size:15px;">' + seqDisplay + "</div>" +
    '<div class="summary-sub">' + seqSub + "</div></div>" +
    "</div>";
}

/* ══════════════════════════════════════════════════
   EXPORT FUNCTIONS (via server endpoints)
   ══════════════════════════════════════════════════ */

function triggerExport(matrixId, format) {
  if (state.sequence.length === 0) {
    showToast("Insira uma sequência primeiro");
    return;
  }
  // Open download URL
  var url = apiPath("/api/matrix/" + matrixId + "/export/" + format);
  var link = document.createElement("a");
  link.href = url;
  link.download = "";
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  setTimeout(function () {
    document.body.removeChild(link);
  }, 100);

  var matrix = state.matrices.find(function (m) { return m.id === matrixId; });
  var name = matrix ? matrix.name : "Matriz";
  showToast("Exportando " + name + " como " + format.toUpperCase());
}

document.addEventListener("click", function (e) {
  var target = e.target.closest("button");
  if (!target) return;

  if (target.classList.contains("delete-matrix-btn")) {
    deleteMatrix(parseInt(target.getAttribute("data-id"), 10));
  } else if (target.classList.contains("export-txt-btn")) {
    triggerExport(parseInt(target.getAttribute("data-id"), 10), "txt");
  } else if (target.classList.contains("export-xml-btn")) {
    triggerExport(parseInt(target.getAttribute("data-id"), 10), "xml");
  } else if (target.classList.contains("export-html-btn")) {
    triggerExport(parseInt(target.getAttribute("data-id"), 10), "html");
  } else if (target.classList.contains("start-col-btn")) {
    setStartCol(
      parseInt(target.getAttribute("data-matrix"), 10),
      parseInt(target.getAttribute("data-col"), 10)
    );
    var parent = target.closest(".start-col-btns");
    if (parent) {
      parent.querySelectorAll(".start-col-btn").forEach(function (b) { b.classList.remove("active"); });
      target.classList.add("active");
    }
  } else if (target.classList.contains("btn-clear-result")) {
    var mid = parseInt(target.getAttribute("data-matrix"), 10);
    clearMatrixResult(mid);
  } else if (target.classList.contains("sync-api-btn")) {
    var mid = parseInt(target.getAttribute("data-matrix"), 10);
    syncMatrixWithApi(mid);
  }
});

function clearMatrixResult(matrixId) {
  var matrix = state.matrices.find(function (m) { return m.id === matrixId; });
  if (!matrix) return;
  matrix.result = [null, null, null, null, null, null, null];

  // Clear inputs in DOM
  var inputs = document.querySelectorAll('.result-input[data-matrix="' + matrixId + '"]');
  inputs.forEach(function (input) { input.value = ""; });

  api("PUT", "/api/matrix/" + matrixId + "/result", { result: matrix.result }).then(function () {
    renderMatrixGrid(matrixId);
    showToast("Resultado limpo");
    if (document.getElementById("tab-estrat4").classList.contains("active")) fetchTopHitsE4();
  });
}

function syncMatrixWithApi(matrixId) {
  var matrix = state.matrices.find(function (m) { return m.id === matrixId; });
  if (!matrix) return;

  var concurso = matrix.concurso ? parseInt(matrix.concurso, 10) : null;
  var url = concurso ? "/api/sync/" + concurso : "/api/last-result";

  showToast("Sincronizando...");

  api("GET", url).then(function (res) {
    if (res.success) {
      var data = res.result;
      matrix.result = data.dezenas;
      matrix.concurso = data.concurso;
      matrix.rateioDetail = data.rateio;

      // Update UI controls specifically for THIS matrix card
      var card = document.getElementById("matrix-" + matrixId);
      if (card) {
        var concInput = card.querySelector('.concurso-input');
        if (concInput) concInput.value = data.concurso;

        var concSelect = card.querySelector('.concurso-select');
        if (concSelect) concSelect.value = data.concurso;

        // Update result inputs
        for (var c = 0; c < COLUMNS; c++) {
          var input = card.querySelector('.result-input[data-col="' + c + '"]');
          if (input) input.value = data.dezenas[c] !== null ? data.dezenas[c] : "";
        }
      }

      api("PUT", "/api/matrix/" + matrixId + "/result", { result: matrix.result }).then(function () {
        renderMatrixGrid(matrixId);
        renderApiDetails(matrixId, data);
        showToast("Concurso " + data.concurso + " sincronizado!");
        if (document.getElementById("tab-estrat4").classList.contains("active")) fetchTopHitsE4();
      });
    } else {
      showToast("Erro: " + res.error);
    }
  }).catch(function (err) {
    showToast("Erro na sincronização");
    console.error(err);
  });
}

function renderApiDetails(matrixId, data) {
  var container = document.getElementById("api-details-" + matrixId);
  if (!container || !data) return;

  var html = '<div class="api-info-card animate-in">';

  if (data.acumulado) {
    html += '<div class="acumulado-badge">ACUMULOU!</div>';
  }

  html += '<div class="api-info-grid">';
  html += '<div class="api-info-item"><span class="label">Sorteio:</span> <span class="val">' + data.data + '</span></div>';
  html += '<div class="api-info-item"><span class="label">Arrecadação:</span> <span class="val">' + formatCurrency(data.arrecadacao) + '</span></div>';
  html += '<div class="api-info-item"><span class="label">Estimativa Próximo:</span> <span class="val highlight">' + formatCurrency(data.estimativaProximo) + '</span></div>';
  html += '</div>';

  if (data.rateio && data.rateio.length > 0) {
    html += '<div class="rateio-table-wrapper"><table class="rateio-table"><thead><tr><th>Faixa</th><th>Ganhadores</th><th>Prêmio</th></tr></thead><tbody>';
    data.rateio.forEach(function (item) {
      html += '<tr><td>' + item.descricao + '</td><td>' + item.ganhadores + '</td><td>' + formatCurrency(item.valor) + '</td></tr>';
    });
    html += '</tbody></table></div>';
  }

  html += '</div>';
  container.innerHTML = html;
}

function formatCurrency(val) {
  if (val === undefined || val === null || val === 0) return "R$ 0,00";
  return "R$ " + val.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

document.addEventListener("input", function (e) {
  if (e.target.classList.contains("result-input")) {
    var val = e.target.value.replace(/[^0-9]/g, "");
    e.target.value = val.slice(0, 1);
    var matId = parseInt(e.target.getAttribute("data-matrix"), 10);
    var colIdx = parseInt(e.target.getAttribute("data-col"), 10);
    updateResult(matId, colIdx, e.target.value);

    // Auto-advance
    if (val.length >= 1) {
      var nextCol = colIdx + 1;
      if (nextCol < COLUMNS) {
        var nextInput = document.querySelector(
          '.result-input[data-matrix="' + matId + '"][data-col="' + nextCol + '"]'
        );
        if (nextInput) nextInput.focus();
      }
    }
  } else if (e.target.classList.contains("concurso-input")) {
    var mid = parseInt(e.target.getAttribute("data-matrix"), 10);
    var matrix = state.matrices.find(function (m) { return m.id === mid; });
    if (matrix) {
      matrix.concurso = e.target.value;
      // Keep select in sync if it matches an option
      var select = document.querySelector('.concurso-select[data-matrix="' + mid + '"]');
      if (select) select.value = e.target.value;

      api("PUT", "/api/matrix/" + mid + "/concurso", { concurso: e.target.value }).catch(function () { });
    }
  }
});

document.addEventListener("change", function (e) {
  if (e.target.classList.contains("concurso-select")) {
    var mid = parseInt(e.target.getAttribute("data-matrix"), 10);
    var val = e.target.value;
    if (!val) return;

    var matrix = state.matrices.find(function (m) { return m.id === mid; });
    if (matrix) {
      matrix.concurso = val;
      // Update the text input as well
      var input = document.querySelector('.concurso-input[data-matrix="' + mid + '"]');
      if (input) input.value = val;

      api("PUT", "/api/matrix/" + mid + "/concurso", { concurso: val }).then(function () {
        syncMatrixWithApi(mid);
      });
    }
  }
});

/* ══════════════════════════════════════════════════
   INITIALIZATION
   ══════════════════════════════════════════════════ */

document.getElementById("addMatrixBtn").addEventListener("click", addMatrix);
if (document.getElementById("helpGuideBtn")) {
  document.getElementById("helpGuideBtn").addEventListener("click", showStrategyGuide);
}
document.getElementById("syncHistoryBtn").addEventListener("click", function () {
  var btn = this;
  btn.disabled = true;
  var originalHtml = btn.innerHTML;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sincronizando...';

  showToast("Verificando concursos pendentes...");

  api("GET", "/api/sync-history").then(function (res) {
    if (res.success) {
      showToast(res.message);
    } else {
      showToast("Erro: " + res.error);
    }
  }).catch(function (err) {
    showToast("Erro na sincronização automática");
  }).finally(function () {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
  });
});
document.getElementById("seqApplyBtn").addEventListener("click", applyManualSequence);
document.getElementById("seqClearBtn").addEventListener("click", clearSequence);
document.getElementById("seqManualInput").addEventListener("keydown", function (e) {
  if (e.key === "Enter") applyManualSequence();
});
document.querySelectorAll('input[name="modeE1"]').forEach(function (radio) {
  radio.addEventListener("change", function () {
    state.hybridMode = (this.value === "Hibrido");
    api("PUT", "/api/hybrid", { hybridMode: state.hybridMode }).catch(function () { });
    renderAllMatrices();
  });
});

// Eventos para Padrão/Híbrido em todas as estratégias (Padronizado com S1)
['E1', 'E2', 'E3', 'E4'].forEach(function (eNum) {
  document.querySelectorAll('input[name="mode' + eNum + '"]').forEach(function (radio) {
    radio.addEventListener("change", function () {
      var isHybrid = (this.value === "Hibrido");
      if (eNum === 'E1') state.hybridMode = isHybrid;
      else state['hybridMode' + eNum] = isHybrid;

      // Persiste se for E1 (global state), os outros são locais por enquanto ou persistidos na geração
      if (eNum === 'E1') api("PUT", "/api/hybrid", { hybridMode: state.hybridMode }).catch(function () { });

      renderAllMatrices();
    });
  });
});

// Load initial state
api("GET", "/api/state").then(function (data) {
  state.sequence = data.sequence || [];
  state.hybridMode = false; // Força Início no Padrão
  state.hybridModeE2 = false;
  state.hybridModeE3 = false;
  state.hybridModeE4 = false;
  state.matrixCounter = data.matrixCounter || 0;
  state.matrices = (data.matrices || []).map(function (m) {
    return {
      id: m.id,
      name: m.name,
      strategy_type: m.strategy_type,
      sequence: m.sequence,
      start_col: m.startCol || 0,
      result: m.result || [null, null, null, null, null, null, null],
      concurso: m.concurso || "",
      createdAt: m.createdAt,
      isHybrid: m.isHybrid,
      grid: m.grid,
      hits_count: m.hitsCount || 0,
      best_row: m.bestRow || -1,
      rateioDetail: m.rateioDetail
    };
  });

  // Update prize tiers from server if available
  if (data.prizeTiers) {
    Object.keys(data.prizeTiers).forEach(function (key) {
      PRIZE_TIERS[key] = data.prizeTiers[key];
    });
  }

  // Update datalist for concursos
  if (data.recentConcursos) {
    state.recentConcursos = data.recentConcursos || [];
    var dl = document.getElementById("concursosList");
    if (dl) {
      dl.innerHTML = "";
      state.recentConcursos.forEach(function (num) {
        var opt = document.createElement("option");
        opt.value = num;
        dl.appendChild(opt);
      });
    }
  }

  // Reset visual checks to Padrao explicitly
  ['E1', 'E2', 'E3', 'E4'].forEach(function (code) {
    var radio = document.querySelector('input[name="mode' + code + '"][value="Padrao"]');
    if (radio) radio.checked = true;
  });

  syncSequenceUI();
  renderAllMatrices();
}).catch(function (err) {
  console.log("Erro ao carregar estado: " + err.message);
  syncSequenceUI();
  renderAllMatrices();
});

/* ══════════════════════════════════════════════════
   TAB SYSTEM LOGIC
   ══════════════════════════════════════════════════ */

document.addEventListener("click", function (e) {
  var tabBtn = e.target.closest(".tab-btn");
  if (!tabBtn) return;

  var tabId = tabBtn.getAttribute("data-tab");
  if (!tabId) return;

  // Update Buttons
  document.querySelectorAll(".tab-btn").forEach(function (btn) {
    btn.classList.toggle("active", btn === tabBtn);
  });

  // Update Panes
  document.querySelectorAll(".tab-pane").forEach(function (pane) {
    pane.classList.toggle("active", pane.id === "tab-" + tabId);
  });

  if (tabId === "estrat2" && state.ranking.length === 0) {
    fetchRanking();
  }
  if (tabId === "estrat3" && state.rankingColumns.length === 0) {
    fetchRankingColumns();
  }
  if (tabId === "estrat4") {
    if (state.ranking.length === 0) fetchRanking();
    renderSelectionE4();
    fetchTopHitsE4();
  }
});

/* ══════════════════════════════════════════════════
   STRATEGY 2 LOGIC
   ══════════════════════════════════════════════════ */

function fetchRanking() {
  api("GET", "/api/stats/ranking").then(function (res) {
    state.ranking = res.ranking;
    renderRanking();
  }).catch(function (err) {
    console.error("Erro ranking:", err);
  });
}

function renderRanking() {
  var list = document.getElementById("rankingList");
  if (!list) return;
  list.innerHTML = "";

  state.ranking.forEach(function (item) {
    var div = document.createElement("div");
    div.className = "ranking-item" + (state.selectedNucleus.indexOf(item.digit) !== -1 ? " selected" : "");
    div.innerHTML =
      '<span class="rank-pos">' + item.pos + '</span>' +
      '<div class="rank-digit">' + item.digit + '</div>' +
      '<i class="fa-solid fa-check rank-check"></i>';

    div.addEventListener("click", function () {
      toggleNucleusDigit(item.digit);
    });
    list.appendChild(div);
  });
  updateSelectionStatus();
}

function toggleNucleusDigit(digit) {
  var idx = state.selectedNucleus.indexOf(digit);
  var status = document.getElementById("selectionStatus");

  if (idx !== -1) {
    state.selectedNucleus.splice(idx, 1);
  } else {
    if (state.selectedNucleus.length >= 3) {
      status.textContent = "Limite máximo de 3 dígitos atingido!";
      status.classList.add("error");
      setTimeout(function () { status.classList.remove("error"); }, 1000);
      return;
    }
    state.selectedNucleus.push(digit);
  }
  renderRanking();
}

function updateSelectionStatus() {
  var status = document.getElementById("selectionStatus");
  if (!status) return;
  var count = state.selectedNucleus.length;
  status.textContent = "Selecionados: " + count + " (Mín: 2, Máx: 3)";
}

function generateEstrat2Matrix() {
  if (state.selectedNucleus.length < 2) {
    showToast("Selecione pelo menos 2 dígitos para o núcleo!");
    return;
  }

  var intensity = document.querySelector('input[name="intensityE2"]:checked').value;
  var isHybrid = document.querySelector('input[name="modeE2"]:checked').value === "Hibrido";
  var startCol = 0;

  showToast("Gerando matriz estratégica...");

  api("POST", "/api/matrix/strategy2", {
    nucleus: state.selectedNucleus,
    intensity: intensity,
    isHybrid: isHybrid,
    startCol: startCol
  }).then(function (matrix) {
    state.matrices.push(matrix);
    renderAllMatrices();
    showToast("Matriz Estratégica Gerada!");
  }).catch(function (err) {
    showToast("Erro ao gerar: " + err.message);
  });
}

/* ════ ESTRATÉGIA 3 LOGIC ════ */

function fetchRankingColumns() {
  api("GET", "/api/stats/ranking-columns").then(function (res) {
    state.rankingColumns = res.rankings;
    renderRankingColumns();
  }).catch(function (err) {
    console.error("Erro ranking col:", err);
  });
}

function renderRankingColumns() {
  var grid = document.getElementById("rankingColumnsGrid");
  if (!grid) return;
  grid.innerHTML = "";

  state.rankingColumns.forEach(function (colData, cIdx) {
    var card = document.createElement("div");
    card.className = "col-rank-card";
    card.innerHTML = '<div class="col-rank-title">Coluna ' + (cIdx + 1) + '</div>';

    colData.slice(0, 4).forEach(function (item) {
      var selIdx = state.selectedNucleusE3[cIdx].indexOf(item.digit);
      var itemDiv = document.createElement("div");
      itemDiv.className = "col-rank-item" + (selIdx !== -1 ? " selected" : "");
      itemDiv.innerHTML =
        '<span class="col-rank-pos">' + item.pos + '</span>' +
        '<div class="col-rank-digit">' + item.digit + '</div>' +
        '<i class="fa-solid fa-check col-rank-check"></i>';

      itemDiv.addEventListener("click", function () {
        toggleNucleusE3(cIdx, item.digit);
      });
      card.appendChild(itemDiv);
    });
    grid.appendChild(card);
  });
}

function toggleNucleusE3(colIdx, digit) {
  var selections = state.selectedNucleusE3[colIdx];
  var idx = selections.indexOf(digit);

  if (idx !== -1) {
    selections.splice(idx, 1);
  } else {
    if (selections.length >= 2) {
      showToast("Máximo de 2 dígitos por coluna!");
      return;
    }
    selections.push(digit);
  }
  renderRankingColumns();
}

function generateEstrat3Matrix() {
  var valid = state.selectedNucleusE3.every(function (s) { return s.length >= 1; });
  if (!valid) {
    showToast("Selecione pelo menos 1 dígito para cada uma das 7 colunas!");
    return;
  }

  var intensity = document.querySelector('input[name="intensityE3"]:checked').value;
  var isHybrid = document.querySelector('input[name="modeE3"]:checked').value === "Hibrido";
  var startCol = 0;

  showToast("Gerando matriz estratégica...");

  api("POST", "/api/matrix/strategy3", {
    selections: state.selectedNucleusE3,
    intensity: intensity,
    isHybrid: isHybrid,
    startCol: startCol
  }).then(function (matrix) {
    state.matrices.push(matrix);
    renderAllMatrices();
    showToast("Matriz Estratégica (E3) Gerada!");
  }).catch(function (err) {
    showToast("Erro ao gerar: " + err.message);
  });
}

/* ════ ESTRATÉGIA 4 LOGIC ════ */

function renderSelectionE4() {
  var list = document.getElementById("selectionListE4");
  if (!list) return;
  list.innerHTML = "";

  // Reuse state.ranking if available
  var data = state.ranking.length > 0 ? state.ranking : Array.from({ length: 10 }, (_, i) => ({ digit: i, pos: (i + 1).toString().padStart(3, '0') }));

  data.forEach(function (item) {
    var div = document.createElement("div");
    div.className = "ranking-item" + (state.selectedDigitsE4.indexOf(item.digit) !== -1 ? " selected" : "");
    div.innerHTML =
      '<span class="rank-pos">' + item.pos + '</span>' +
      '<div class="rank-digit">' + item.digit + '</div>' +
      '<i class="fa-solid fa-check rank-check"></i>';

    div.addEventListener("click", function () {
      toggleDigitE4(item.digit);
    });
    list.appendChild(div);
  });
  updateStatusE4();
}

function toggleDigitE4(digit) {
  var idx = state.selectedDigitsE4.indexOf(digit);
  var status = document.getElementById("selectionStatusE4");

  if (idx !== -1) {
    state.selectedDigitsE4.splice(idx, 1);
  } else {
    if (state.selectedDigitsE4.length >= 5) {
      status.textContent = "Máximo de 5 dígitos atingido!";
      status.classList.add("error");
      setTimeout(function () { status.classList.remove("error"); }, 1000);
      return;
    }
    state.selectedDigitsE4.push(digit);
  }
  renderSelectionE4();
}

function updateStatusE4() {
  var status = document.getElementById("selectionStatusE4");
  if (!status) return;
  var count = state.selectedDigitsE4.length;
  status.textContent = "Selecionados: " + count + " (Necessário: 5)";
}

function useTop5E4() {
  if (state.ranking.length === 0) {
    api("GET", "/api/stats/ranking").then(function (res) {
      state.ranking = res.ranking;
      applyTop5();
    });
  } else {
    applyTop5();
  }

  function applyTop5() {
    state.selectedDigitsE4 = state.ranking.slice(0, 5).map(function (item) { return item.digit; });
    renderSelectionE4();
    showToast("Top 5 Histórico aplicado!");
  }
}

function generateEstrat4Matrix() {
  if (state.selectedDigitsE4.length !== 5) {
    showToast("Selecione exatamente 5 dígitos!");
    return;
  }

  var intensity = document.querySelector('input[name="intensityE4"]:checked').value;
  var isHybrid = document.querySelector('input[name="modeE4"]:checked').value === "Hibrido";
  var startCol = 0;

  showToast("Gerando matriz com restrição estrutural...");

  api("POST", "/api/matrix/strategy4", {
    digits: state.selectedDigitsE4,
    intensity: intensity,
    isHybrid: isHybrid,
    startCol: startCol
  }).then(function (matrix) {
    state.matrices.push(matrix);
    renderAllMatrices();
    showToast("Estratégia 4 Gerada!");
  }).catch(function (err) {
    showToast("Erro ao gerar: " + err.message);
  });
}

function fetchTopHitsE4() {
  var min = document.getElementById("filterHitsE4").value;
  var apiMin = min === "all" ? 6 : (min === "6" ? 6 : 7);

  api("GET", "/api/matrix/top-hits?min=" + apiMin).then(function (res) {
    renderTopHitsTable(res, min);
  });
}

function renderTopHitsTable(data, filter) {
  var tbody = document.getElementById("topHitsBodyE4");
  if (!tbody) return;
  tbody.innerHTML = "";

  var filtered = data;
  if (filter === "6") filtered = data.filter(function (m) { return m.hitsCount === 6; });
  if (filter === "7") filtered = data.filter(function (m) { return m.hitsCount === 7; });

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 20px; color: var(--text-tertiary);">Nenhum registro encontrado</td></tr>';
    return;
  }

  filtered.forEach(function (m) {
    var tr = document.createElement("tr");
    var dateStr = m.createdAt ? new Date(m.createdAt).toLocaleString('pt-BR') : "—";
    tr.innerHTML =
      '<td>' + dateStr + '</td>' +
      '<td>E' + m.strategy_type + '</td>' +
      '<td>' + (m.isHybrid ? "Híb" : "Pad") + '</td>' +
      '<td>' + m.concurso + '</td>' +
      '<td class="gold"><strong>' + m.hitsCount + '</strong></td>' +
      '<td style="font-size: 11px; font-family:var(--font-mono);">' + (m.sequence || "[]") + '</td>';
    tbody.appendChild(tr);
  });
}

/* ════ ABA 5: RANKINGS / ANÁLISE ════ */

function executeAnalysis() {
  var period = document.getElementById("analysisPeriod").value;
  var selectedStrats = Array.from(document.querySelectorAll('input[name="analyzeStrat"]:checked')).map(function (cb) { return cb.value; });

  if (selectedStrats.length < 2) {
    showToast("Selecione pelo menos duas estratégias para análise!");
    return;
  }

  var btn = document.getElementById("executeAnalysisBtn");
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Executando Simulação...';

  var payload = { period: period, strategies: selectedStrats };
  if (period === "custom") {
    payload.start = parseInt(document.getElementById("startConcAnalysis").value);
    payload.end = parseInt(document.getElementById("endConcAnalysis").value);
  }

  api("POST", "/api/stats/compare", payload).then(function (res) {
    state.analysisResults = res;
    renderAnalysisResults();
  }).catch(function (err) {
    showToast("Erro na análise: " + err.message);
  }).finally(function () {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-magnifying-glass-chart"></i> Executar Análise';
  });
}

function renderAnalysisResults() {
  var area = document.getElementById("analysisResultsArea");
  var tbody = document.getElementById("analysisBody");
  var winnerSlot = document.getElementById("analysisWinnerSlot");

  if (!area || !state.analysisResults) return;
  area.style.display = "block";
  tbody.innerHTML = "";

  var ranking = state.analysisResults.ranking;
  var winner = ranking[0];

  winnerSlot.innerHTML =
    '<div class="summary-card gold-border animate-in" style="margin-bottom: 25px; background: linear-gradient(135deg, rgba(212,175,55,0.1), rgba(0,0,0,0.05)); border: 1px solid var(--gold-color);">' +
    '<div class="summary-label" style="color:var(--gold-color); font-weight:700;"><i class="fa-solid fa-crown"></i> Recomendação Técnica</div>' +
    '<div class="summary-value" style="font-size: 24px;">' + winner.strategy + '</div>' +
    '<div class="summary-sub">Com Score de <strong>' + winner.score + '</strong>, esta foi a estratégia mais consistente no período analisado.</div>' +
    '</div>';

  ranking.forEach(function (item) {
    var tr = document.createElement("tr");
    tr.innerHTML =
      '<td><strong>' + item.strategy + '</strong></td>' +
      '<td>' + item.media + '</td>' +
      '<td>' + item.melhor + '</td>' +
      '<td>' + item.p3 + '%</td>' +
      '<td>' + (item.t6 + item.t7) + '</td>' +
      '<td class="gold" style="font-weight:700;">' + item.score + '</td>';
    tbody.appendChild(tr);
  });

  area.scrollIntoView({ behavior: 'smooth' });
}

document.getElementById("generateEstrat4Btn").addEventListener("click", generateEstrat4Matrix);
document.getElementById("useTop5Btn").addEventListener("click", useTop5E4);
document.getElementById("filterHitsE4").addEventListener("change", fetchTopHitsE4);
document.getElementById("executeAnalysisBtn").addEventListener("click", executeAnalysis);
document.getElementById("analysisPeriod").addEventListener("change", function () {
  document.getElementById("customPeriodInputs").style.display = (this.value === "custom" ? "flex" : "none");
});

document.getElementById("generateEstrat2Btn").addEventListener("click", generateEstrat2Matrix);
document.getElementById("generateEstrat3Btn").addEventListener("click", generateEstrat3Matrix);

/* ════ MÓDULOS NAV LOGIC ════ */

function initModuleSwitcher() {
  document.querySelectorAll(".module-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var moduleName = this.getAttribute("data-module");
      switchModule(moduleName);
    });
  });
}

function switchModule(moduleName) {
  document.querySelectorAll(".module-btn").forEach(function (b) { b.classList.remove("active"); });
  var activeBtn = document.querySelector('.module-btn[data-module="' + moduleName + '"]');
  if (activeBtn) activeBtn.classList.add("active");

  document.querySelectorAll(".module-view").forEach(function (v) { v.classList.remove("active"); });
  var activeView = document.getElementById(moduleName);
  if (activeView) activeView.classList.add("active");

  showToast("Alternando para " + (moduleName === "modulo-estrategias" ? "Estratégias" : "Análises"));
}

/* ════ ANÁLISES MODULAR LOGIC ════ */

function initAnalysisEvents() {
  document.querySelectorAll(".run-analysis-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var type = this.getAttribute("data-type");
      runAnalysis(type);
    });
  });

  document.querySelectorAll(".clear-analysis-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var container = this.closest(".tab-pane").querySelector(".analysis-result-view");
      if (container) container.innerHTML = "";
    });
  });
}

function runAnalysis(type) {
  var select = document.querySelector('.period-selector[data-analise="' + type + '"]');
  var period = select ? select.value : "50";

  var container = document.getElementById("res-" + type);
  if (!container) return;

  container.innerHTML = '<div style="text-align:center; padding:60px;"><i class="fa-solid fa-spinner fa-spin fa-3x" style="color:var(--accent);"></i><br><br><span style="font-weight:600; color:var(--text-secondary);">Processando Inteligência de Dados...</span></div>';

  api("POST", "/api/stats/analysis", { type: type, period: period }).then(function (res) {
    if (res.success) {
      renderAnalysisResult(type, res.data);
    } else {
      showToast("Erro: " + res.error);
    }
  }).catch(function (err) {
    showToast("Erro na requisição estatística");
    console.error(err);
  });
}

function renderAnalysisResult(type, data) {
  var container = document.getElementById("res-" + type);
  if (!container) return;
  container.innerHTML = "";

  if (type === "composicao") {
    var html = '<div class="stat-card-grid animate-in">';
    html += '<div class="stat-card-mini"><span class="val">' + data.media_distintos + '</span><span class="lab">Média de Distintos</span></div>';
    html += '<div class="stat-card-mini"><span class="val">' + data.desvio_padrao + '</span><span class="lab">Desvio Padrão</span></div>';
    html += '<div class="stat-card-mini"><span class="val">' + data.rep_percent + '%</span><span class="lab">Taxa de Repetição</span></div>';
    html += '</div>';

    html += '<div class="section-label">Frequência de Dígitos Distintos</div>';
    html += '<div class="table-wrapper"><table class="rateio-table"><thead><tr><th>Padrão</th><th>Concursos</th></tr></thead><tbody>';
    for (var i = 1; i <= 7; i++) {
      html += "<tr><td>" + i + " dígito(s) distinto(s)</td><td><strong>" + (data.hist_distinct[i] || 0) + "</strong></td></tr>";
    }
    html += "</tbody></table></div>";

    html += '<div class="section-label" style="margin-top:25px;">Distribuição de Repetições Internas</div>';
    html += '<div class="table-wrapper"><table class="rateio-table"><thead><tr><th>Qtd Repetições</th><th>Qtde Concursos</th></tr></thead><tbody>';
    for (var r = 0; r <= 6; r++) {
      html += "<tr><td>" + r + " repetição(ões)</td><td>" + (data.rep_counts[r] || 0) + "</td></tr>";
    }
    html += "</tbody></table></div>";

    container.innerHTML = html;
  } else if (type === "colunas") {
    var html = '<div class="section-label">Mapeamento de Frequência Individual por Coluna</div>';
    html += '<div class="table-wrapper"><table class="heat-map-table"><thead><tr><th>#</th><th>C1</th><th>C2</th><th>C3</th><th>C4</th><th>C5</th><th>C6</th><th>C7</th></tr></thead><tbody>';
    for (var d = 0; d <= 9; d++) {
      html += '<tr><td style="background:var(--bg-tertiary); font-weight:bold;">' + d + "</td>";
      for (var c = 0; c < 7; c++) {
        var count = data.matrix[c][d] || 0;
        var opacity = Math.min(count / 15, 0.8);
        var bg = "rgba(169, 207, 70, " + opacity + ")";
        html += '<td style="background:' + bg + '"><span class="heat-cell-val">' + count + "</span></td>";
      }
      html += "</tr>";
    }
    html += "</tbody></table></div>";
    container.innerHTML = html;
  } else if (type === "estrutural") {
    var html = '<div class="section-label">Frequência dos Padrões Estruturais</div>';
    html += '<div class="table-wrapper"><table class="rateio-table"><thead><tr><th>Padrão Identificado</th><th>Ocorrências</th></tr></thead><tbody>';
    Object.keys(data.patterns).sort(function (a, b) { return data.patterns[b] - data.patterns[a]; }).forEach(function (p) {
      html += "<tr><td><strong>" + p + "</strong></td><td class='gold'>" + data.patterns[p] + "</td></tr>";
    });
    html += "</tbody></table></div>";
    container.innerHTML = html;
  } else if (type === "concentracao") {
    var html = '<div class="stat-card-mini animate-in" style="margin-bottom:20px; width:100%; border-left-color: ' + (data.diff < 0 ? "var(--danger)" : "var(--accent)") + '">';
    html += '<span class="lab">Indicador de Concentração</span><span class="val">' + data.status + "</span>";
    html += '<p style="font-size:14px; margin-top:10px;">A média de dígitos distintos do período (<strong>' + data.period_avg + "</strong>) comparada à média histórica global (<strong>" + data.global_avg + "</strong>).</p></div>";
    container.innerHTML = html;
  } else if (type === "par_impar") {
    var html = '<div class="section-label">Análise de Paridade (Pares vs Ímpares)</div>';
    html += '<div class="table-wrapper"><table class="rateio-table"><thead><tr><th>Distribuição</th><th>Qtde Concursos</th></tr></thead><tbody>';
    Object.keys(data.distribuicao).sort().forEach(function (lbl) {
      html += "<tr><td>" + lbl + "</td><td class='gold'><strong>" + data.distribuicao[lbl] + "</strong></td></tr>";
    });
    html += "</tbody></table></div>";
    container.innerHTML = html;
  } else if (type === "repeticao_detalhada") {
    var html = '<div class="section-label">Ranking de Concursos com Repetição</div>';
    html += '<div class="table-wrapper"><table class="rateio-table"><thead><tr><th>Dígito</th><th>Vezes em Repetição</th></tr></thead><tbody>';
    data.ranking_repetidores.forEach(function (item) {
      html += '<tr><td><span class="rank-digit-mini">' + item[0] + '</span></td><td class="gold"><strong>' + item[1] + "</strong></td></tr>";
    });
    html += "</tbody></table></div>";

    html += '<div class="stat-card-grid" style="margin-top:30px;">';
    html += '<div class="stat-card-mini"><span class="lab">Conc. Mais Concentrado</span><span class="val">#' + data.max_concentrado.conc + "</span></div>";
    html += '<div class="stat-card-mini"><span class="lab">Conc. Mais Distribuído</span><span class="val">#' + data.max_distribuido.conc + "</span></div>";
    html += "</div>";
    container.innerHTML = html;
  }
}

// Iniciar módulos
initModuleSwitcher();
initAnalysisEvents();

// Export Analysis
document.addEventListener("click", function (e) {
  var btn = e.target.closest(".export-analysis-btn");
  if (btn) {
    var type = btn.getAttribute("data-type");
    var format = btn.getAttribute("data-format");
    var select = document.querySelector('.period-selector[data-analise="' + type + '"]');
    var period = select ? select.value : "50";

    showToast("Preparando exportação " + format.toUpperCase() + "...");
    window.open(apiPath("/api/stats/export?type=" + type + "&period=" + period + "&format=" + format), "_blank");
  }
});
