/* Tabela Sorteios e premiação — padrão Dia de Sorte (Excel complementar). */
(function () {
    const CFG = window.PREMIACAO_UI || {};
    function apiPath(path) {
        const raw = String(path || "");
        const root = String(
            (typeof window.__APP_ROOT__ === "string" && window.__APP_ROOT__)
            || document.querySelector("base[href]")?.getAttribute("href")
            || ""
        ).replace(/\/$/, "");
        if (/^https?:\/\//i.test(raw)) return raw;
        if (root && (raw === root || raw.startsWith(root + "/"))) return raw;
        const p = raw.startsWith("/") ? raw : "/" + raw;
        return root ? root + p : p;
    }
    const N = Number(CFG.nBolas) || 6;
    const PAD = Number(CFG.pad) || 2;
    const LABEL = CFG.labelBola || "P";
    const EXTRA = CFG.extra || null;
    const ORDENAR = CFG.ordenar !== false;
    const FAIXA_NOMES = Array.isArray(CFG.faixas) ? CFG.faixas : [];

    let PAGE = 1, SIZE = 0, CRESCENTE = false;
    let LINHAS = [], SORT = { key: "concurso", dir: "desc" };
    let FILTERS = {}, BUSCA_CONCURSO = "", ULTIMO = null, MENU = null, COLS = [];

    function esc(s) {
        return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    }
    function fmtDez(n) {
        if (n == null || n === "") return "";
        const s = String(n);
        return PAD > 1 ? s.padStart(PAD, "0") : s;
    }
    function htmlBola(n) {
        if (n == null || n === "") return "—";
        return `<span class="dez-ball">${esc(fmtDez(n))}</span>`;
    }
    function htmlDezenas(nums) {
        const balls = (nums || []).filter(n => n != null).map(d => `<span class="dez-ball">${esc(fmtDez(d))}</span>`).join("");
        return `<div class="ud-bolas">${balls}</div>`;
    }
    function htmlLoc(locs, campo) {
        const vals = (locs || []).map(l => String((l && l[campo]) || "").trim());
        if (!vals.some(Boolean)) return "";
        return vals.map(v => esc(v)).join("<br>");
    }
    function htmlRateio(txt) {
        if (!txt || txt === "—") return "—";
        return `<span class="rateio-val">${esc(txt)}</span>`;
    }
    function dezDaLinha(l) {
        if (EXTRA === "dupla") return CRESCENTE ? (l.s1 || []) : (l.s1ordem || l.s1 || []);
        return CRESCENTE ? (l.dezenas || []) : (l.dezenas_ordem || l.dezenas || []);
    }
    function s2DaLinha(l) {
        return CRESCENTE ? (l.s2 || []) : (l.s2ordem || l.s2 || []);
    }
    function dataSortKey(s) {
        const m = String(s || "").match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
        if (!m) return String(s || "");
        return `${m[3]}${m[2].padStart(2, "0")}${m[1].padStart(2, "0")}`;
    }
    function colDef(key) { return COLS.find(c => c.key === key); }

    function montarCols() {
        const cols = [
            { key: "concurso", label: "Concurso", cls: "col-num", type: "num" },
            { key: "data", label: "Data", cls: "col-num", type: "text" },
        ];
        for (let i = 0; i < N; i++) {
            cols.push({ key: "b" + i, label: LABEL + (i + 1), cls: "", type: "bola", idx: i, set: "s1" });
        }
        if (EXTRA === "dupla") {
            for (let i = 0; i < N; i++) {
                cols.push({ key: "s2b" + i, label: "S2" + (i + 1), cls: "", type: "bola", idx: i, set: "s2" });
            }
        }
        if (EXTRA === "time") cols.push({ key: "extra", label: "Time", cls: "", type: "text" });
        if (EXTRA === "trevos") cols.push({ key: "extra", label: "Trevos", cls: "", type: "text" });
        cols.push({ key: "cidade", label: "Cidade", cls: "col-cidade", type: "text" });
        cols.push({ key: "uf", label: "UF", cls: "col-uf", type: "text" });
        FAIXA_NOMES.forEach((nome, i) => {
            cols.push({ key: "g" + i, label: "Ganh. " + nome, cls: "col-num", type: "num" });
            cols.push({ key: "r" + i, label: "", cls: "col-reais", type: "money", filterTitle: "Valor " + nome });
        });
        COLS = cols;
    }

    function valorFiltro(l, key) {
        const col = colDef(key);
        if (!col) return "";
        if (col.type === "bola") {
            const arr = col.set === "s2" ? s2DaLinha(l) : dezDaLinha(l);
            const n = arr[col.idx];
            return n == null ? "" : String(n);
        }
        if (key === "concurso") return String(l.concurso ?? "");
        if (key === "data") return String(l.data || "");
        if (key === "extra") return String(l.extra || "") || "(vazio)";
        if (key === "cidade") return String(l.cidade || "").trim() || "(vazio)";
        if (key === "uf") return String(l.uf || "").trim() || "(vazio)";
        if (key.startsWith("g")) return String(l[key] ?? 0);
        if (key.startsWith("r")) return String(l[key] || "—");
        return "";
    }
    function valorSort(l, key) {
        const col = colDef(key);
        if (col && col.type === "bola") {
            const arr = col.set === "s2" ? s2DaLinha(l) : dezDaLinha(l);
            const n = arr[col.idx];
            return n == null ? -1 : Number(n);
        }
        if (key === "concurso") return Number(l.concurso) || 0;
        if (key === "data") return dataSortKey(l.data);
        if (key === "extra" || key === "cidade" || key === "uf") return String(l[key] || "").toLowerCase();
        if (key.startsWith("g")) return Number(l[key]) || 0;
        if (key.startsWith("r")) return Number(l[key + "n"]) || 0;
        return "";
    }
    function linhasFiltradas() {
        let rows = LINHAS.slice();
        if (BUSCA_CONCURSO) {
            const alvo = BUSCA_CONCURSO;
            return rows.filter(l => String(l.concurso) === alvo);
        }
        Object.keys(FILTERS).forEach(key => {
            const allowed = FILTERS[key];
            if (!allowed) return;
            rows = rows.filter(l => allowed.has(valorFiltro(l, key)));
        });
        return rows;
    }
    function setBuscaMsg(texto, isErro) {
        const el = document.getElementById("premiacaoBuscaMsg");
        if (!el) return;
        el.textContent = texto || "";
        el.classList.toggle("erro", !!isErro);
    }
    function pesquisarConcurso() {
        const input = document.getElementById("premiacaoBuscaConcurso");
        const raw = String(input?.value || "").trim();
        if (!raw) {
            BUSCA_CONCURSO = "";
            PAGE = 1;
            setBuscaMsg("");
            render();
            return;
        }
        const num = String(parseInt(raw, 10));
        if (!num || num === "NaN") {
            setBuscaMsg("Informe o número do concurso.", true);
            return;
        }
        const found = LINHAS.find(l => String(l.concurso) === num);
        if (!found) {
            setBuscaMsg("Concurso não encontrado.", true);
            return;
        }
        BUSCA_CONCURSO = String(found.concurso);
        PAGE = 1;
        setBuscaMsg("");
        render();
    }
    function resetarPesquisaConcurso() {
        const input = document.getElementById("premiacaoBuscaConcurso");
        if (input) input.value = "";
        BUSCA_CONCURSO = "";
        PAGE = 1;
        setBuscaMsg("");
        render();
    }
    function linhasExibicao() {
        const rows = linhasFiltradas();
        const { key, dir } = SORT;
        if (!key) return rows;
        const mul = dir === "asc" ? 1 : -1;
        rows.sort((a, b) => {
            const va = valorSort(a, key), vb = valorSort(b, key);
            if (typeof va === "number" && typeof vb === "number") return (va - vb) * mul;
            return String(va).localeCompare(String(vb), "pt-BR", { numeric: true, sensitivity: "base" }) * mul;
        });
        return rows;
    }
    function fecharMenu() {
        if (MENU) { MENU.remove(); MENU = null; }
        document.querySelectorAll(".px-filter-btn.open").forEach(b => b.classList.remove("open"));
    }
    function valoresUnicos(key) {
        const set = new Set();
        LINHAS.forEach(l => set.add(valorFiltro(l, key)));
        const arr = [...set];
        const col = colDef(key);
        arr.sort((a, b) => {
            if (col && (col.type === "bola" || col.type === "num")) {
                const na = Number(a), nb = Number(b);
                if (Number.isFinite(na) && Number.isFinite(nb)) return na - nb;
            }
            return String(a).localeCompare(String(b), "pt-BR", { numeric: true, sensitivity: "base" });
        });
        return arr;
    }
    function abrirMenu(th, key) {
        fecharMenu();
        const btn = th.querySelector(".px-filter-btn");
        if (btn) btn.classList.add("open");
        const rect = (btn || th).getBoundingClientRect();
        const values = valoresUnicos(key);
        const current = FILTERS[key] ? new Set(FILTERS[key]) : new Set(values);
        const menu = document.createElement("div");
        menu.className = "px-excel-menu";
        const colLabel = colDef(key)?.label || key;
        menu.innerHTML = `
            <button type="button" class="px-m-item" data-act="asc"><span>↑</span> Classificar do Menor para o Maior</button>
            <button type="button" class="px-m-item" data-act="desc"><span>↓</span> Classificar do Maior para o Menor</button>
            <div class="px-m-sep"></div>
            <button type="button" class="px-m-item" data-act="clear" ${FILTERS[key] ? "" : "disabled"}><span>✕</span> Limpar Filtro de "${esc(colLabel)}"</button>
            <div class="px-m-sep"></div>
            <div class="px-m-search"><input type="search" placeholder="Pesquisar" autocomplete="off"></div>
            <div class="px-m-list"></div>
            <div class="px-m-actions">
                <button type="button" class="btn btn-sm btn-primary" data-act="ok">OK</button>
                <button type="button" class="btn btn-sm btn-outline-secondary" data-act="cancel">Cancelar</button>
            </div>`;
        const list = menu.querySelector(".px-m-list");
        const search = menu.querySelector(".px-m-search input");
        function paintList(q) {
            const qq = String(q || "").trim().toLowerCase();
            const visible = values.filter(v => !qq || String(v).toLowerCase().includes(qq));
            const allOn = visible.length > 0 && visible.every(v => current.has(v));
            list.innerHTML = `<label class="px-m-check"><input type="checkbox" data-all ${allOn ? "checked" : ""}> (Selecionar Tudo)</label>` +
                visible.map(v => {
                    const label = (colDef(key)?.type === "bola" && v !== "") ? fmtDez(v) : v;
                    return `<label class="px-m-check"><input type="checkbox" data-v="${esc(v)}" ${current.has(v) ? "checked" : ""}> ${esc(label)}</label>`;
                }).join("");
        }
        paintList("");
        document.body.appendChild(menu);
        MENU = menu;
        let left = rect.left, top = rect.bottom + 4;
        if (left + menu.offsetWidth > window.innerWidth - 8) left = Math.max(8, window.innerWidth - menu.offsetWidth - 8);
        if (top + menu.offsetHeight > window.innerHeight - 8) top = Math.max(8, rect.top - menu.offsetHeight - 4);
        menu.style.left = left + "px";
        menu.style.top = top + "px";
        if (SORT.key === key) menu.querySelector(`[data-act="${SORT.dir}"]`)?.classList.add("active");
        menu.addEventListener("click", (ev) => {
            const checkRow = ev.target.closest(".px-m-check");
            if (checkRow) {
                const all = checkRow.querySelector("input[data-all]");
                const one = checkRow.querySelector("input[data-v]");
                if (all) {
                    const checks = [...list.querySelectorAll("input[data-v]")];
                    const vis = new Set(checks.map(c => c.dataset.v));
                    checks.forEach(c => { c.checked = all.checked; });
                    values.forEach(v => { if (!vis.has(v)) return; if (all.checked) current.add(v); else current.delete(v); });
                    return;
                }
                if (one) {
                    if (one.checked) current.add(one.dataset.v);
                    else current.delete(one.dataset.v);
                    return;
                }
            }
            const actBtn = ev.target.closest("[data-act]");
            if (!actBtn) return;
            const act = actBtn.getAttribute("data-act");
            if (act === "asc" || act === "desc") { SORT = { key, dir: act }; PAGE = 1; fecharMenu(); render(); return; }
            if (act === "clear") { delete FILTERS[key]; PAGE = 1; fecharMenu(); render(); return; }
            if (act === "cancel") { fecharMenu(); return; }
            if (act === "ok") {
                const qq = String(search.value || "").trim().toLowerCase();
                let selected = new Set(current);
                if (qq) {
                    const visible = values.filter(v => String(v).toLowerCase().includes(qq));
                    selected = new Set(visible.filter(v => current.has(v)));
                }
                if (!selected.size) FILTERS[key] = new Set();
                else if (selected.size >= values.length) delete FILTERS[key];
                else FILTERS[key] = selected;
                PAGE = 1; fecharMenu(); render();
            }
        });
        search.addEventListener("input", () => paintList(search.value));
        search.focus();
    }

    function pageSizeAtual() {
        const el = document.getElementById("premiacaoPageSize");
        if (!el) return SIZE;
        const n = Number(el.value);
        return Number.isFinite(n) ? n : 0;
    }
    function renderCabecalho() {
        const tr = document.getElementById("premiacaoCaixaHeadRow");
        if (!tr) return;
        tr.innerHTML = COLS.map(col => {
            const filtered = !!FILTERS[col.key];
            const sorted = SORT.key === col.key;
            const ind = sorted ? (SORT.dir === "asc" ? "▲" : "▼") : "";
            const cls = ["px-th", col.cls || "", sorted ? "px-sort-on" : "", filtered ? "px-filter-on" : ""].filter(Boolean).join(" ");
            const filterTitle = col.filterTitle || col.label || col.key;
            return `<th class="${cls}" data-key="${col.key}"><span class="px-th-inner"><span class="px-th-label">${esc(col.label)}</span>${ind ? `<span class="px-sort-ind">${ind}</span>` : ""}<button type="button" class="px-filter-btn" data-filter="${col.key}" title="Filtrar / classificar ${esc(filterTitle)}">▼</button></span></th>`;
        }).join("");
    }
    function atualizarBotoesOrdem() {
        const bS = document.getElementById("btnOrdemSorteio");
        const bC = document.getElementById("btnOrdemCresc");
        [bS, bC].forEach(b => { if (!b) return; b.classList.remove("btn-primary", "active"); b.classList.add("btn-outline-secondary"); });
        const on = CRESCENTE ? bC : bS;
        if (on) { on.classList.add("btn-primary", "active"); on.classList.remove("btn-outline-secondary"); }
    }
    function htmlExtra(l) {
        if (EXTRA === "time") return esc(l.extra || "");
        if (EXTRA === "trevos") return (l.trevos || []).map(htmlBola).join(" ");
        return "";
    }
    function renderUltimo() {
        const box = document.getElementById("ultimoResultadoDestaque");
        if (!box) return;
        const r = ULTIMO;
        if (!r) {
            box.innerHTML = '<div class="text-muted small text-center">Sincronize os dados para ver o último resultado.</div>';
            return;
        }
        const dez = dezDaLinha(r);
        let extra = "";
        if (EXTRA === "dupla") extra = `<span class="ud-sep">-</span>${htmlDezenas(s2DaLinha(r))}`;
        else if (EXTRA === "time" && r.extra) extra = `<span class="ud-sep">-</span><strong>${esc(r.extra)}</strong>`;
        else if (EXTRA === "trevos") extra = `<span class="ud-sep">-</span>${(r.trevos || []).map(htmlBola).join("")}`;
        box.innerHTML = `<div class="ud-inline"><div class="ud-titulo">${esc(r.concurso)}</div><span class="ud-sep">-</span>${htmlDezenas(dez)}${extra}</div>`;
    }
    function htmlPager(p, pages) {
        let start = Math.max(1, p - 2);
        let end = Math.min(pages, start + 4);
        start = Math.max(1, end - 4);
        const nums = [];
        for (let i = start; i <= end; i++) nums.push(i);
        return `<button type="button" class="btn btn-sm btn-outline-secondary" ${p <= 1 ? "disabled" : ""} data-px="${p - 1}">‹ Anterior</button>` +
            nums.map(n => `<button type="button" class="btn btn-sm btn-outline-secondary px-page${n === p ? " active" : ""}" data-px="${n}">${n}</button>`).join("") +
            `<button type="button" class="btn btn-sm btn-outline-secondary" ${p >= pages ? "disabled" : ""} data-px="${p + 1}">Próximo ›</button>`;
    }
    function celulasLinha(l) {
        const dez = dezDaLinha(l);
        const cells = [
            `<td class="td-num"><strong>${esc(l.concurso)}</strong></td>`,
            `<td class="td-num">${esc(l.data)}</td>`,
        ];
        for (let i = 0; i < N; i++) cells.push(`<td class="td-bola">${htmlBola(dez[i])}</td>`);
        if (EXTRA === "dupla") {
            const s2 = s2DaLinha(l);
            for (let i = 0; i < N; i++) cells.push(`<td class="td-bola">${htmlBola(s2[i])}</td>`);
        }
        if (EXTRA === "time" || EXTRA === "trevos") cells.push(`<td class="td-extra">${htmlExtra(l)}</td>`);
        cells.push(`<td class="td-cidade">${htmlLoc(l.locs, "cidade")}</td>`);
        cells.push(`<td class="td-uf">${htmlLoc(l.locs, "uf")}</td>`);
        FAIXA_NOMES.forEach((_, i) => {
            cells.push(`<td class="td-num">${esc(l["g" + i] ?? 0)}</td>`);
            cells.push(`<td class="td-reais">${htmlRateio(l["r" + i])}</td>`);
        });
        return cells.join("");
    }
    function render() {
        const tbody = document.querySelector("#premiacaoCaixaTabela tbody");
        const status = document.getElementById("premiacaoCaixaStatus");
        const pager = document.getElementById("premiacaoCaixaPager");
        if (!tbody) return;
        renderCabecalho();
        atualizarBotoesOrdem();
        renderUltimo();
        const all = linhasExibicao();
        SIZE = pageSizeAtual();
        const size = SIZE > 0 ? SIZE : Math.max(all.length, 1);
        const pages = Math.max(1, Math.ceil(all.length / size) || 1);
        if (PAGE > pages) PAGE = pages;
        const pageRows = SIZE > 0 ? all.slice((PAGE - 1) * SIZE, (PAGE - 1) * SIZE + SIZE) : all;
        if (!LINHAS.length) {
            tbody.innerHTML = `<tr><td colspan="${COLS.length}" class="text-muted text-center py-3">Sincronize os dados para ver os sorteios e a premiação.</td></tr>`;
            if (pager) pager.innerHTML = "";
            return;
        }
        if (!pageRows.length) {
            tbody.innerHTML = `<tr><td colspan="${COLS.length}" class="text-muted text-center py-3">Nenhum concurso com os filtros atuais.</td></tr>`;
        } else {
            tbody.innerHTML = pageRows.map(l => `<tr>${celulasLinha(l)}</tr>`).join("");
        }
        const nFiltros = Object.keys(FILTERS).length;
        const modo = !ORDENAR ? "posição" : (CRESCENTE ? "crescente" : "ordem do sorteio");
        if (status) {
            status.textContent = `${all.length} de ${LINHAS.length} concursos`
                + (BUSCA_CONCURSO
                    ? ` · concurso ${BUSCA_CONCURSO}`
                    : (nFiltros ? ` · ${nFiltros} filtro(s)` : ""))
                + ` · bolas em ${modo}`
                + (SIZE > 0 ? ` · pág. ${PAGE}/${pages}` : " · todos");
        }
        if (pager) {
            if (SIZE > 0 && pages > 1) {
                pager.innerHTML = htmlPager(PAGE, pages);
                pager.querySelectorAll("[data-px]").forEach(b => b.addEventListener("click", () => { PAGE = +b.dataset.px; render(); }));
            } else pager.innerHTML = "";
        }
    }
    function mapLinhas(registros) {
        const rows = [];
        const seen = new Set();
        (registros || []).forEach(r => {
            const conc = r.concurso;
            if (conc == null || seen.has(conc)) return;
            seen.add(conc);
            const ordem = r.dezenas_ordem || r.dezenas || [];
            const sorted = (r.dezenas && r.dezenas.length) ? r.dezenas : [...ordem].filter(n => n != null).sort((a, b) => a - b);
            const locs = r.localidades || [];
            const byNome = {};
            (r.faixas || []).forEach(f => { byNome[f.nome] = f; });
            const row = {
                concurso: conc,
                data: r.data || "",
                dezenas: sorted,
                dezenas_ordem: ordem,
                s1: r.sorteio1 || sorted,
                s1ordem: r.sorteio1 || ordem,
                s2: r.sorteio2 || [],
                s2ordem: r.sorteio2 || [],
                trevos: r.trevos || (r.extras && r.extras.trevos) || [],
                extra: r.time_nome || (r.extras && r.extras.time_nome) || "",
                locs,
                cidade: locs.map(l => l.cidade || "").filter(Boolean).join(" "),
                uf: locs.map(l => l.uf || "").filter(Boolean).join(" "),
            };
            FAIXA_NOMES.forEach((nome, i) => {
                const f = byNome[nome] || {};
                row["g" + i] = f.ganhadores ?? 0;
                row["r" + i] = f.rateio_fmt || "—";
                row["r" + i + "n"] = Number(f.rateio) || 0;
            });
            rows.push(row);
        });
        return rows;
    }

    async function reload() {
        const tbody = document.querySelector("#premiacaoCaixaTabela tbody");
        const status = document.getElementById("premiacaoCaixaStatus");
        if (!tbody) return;
        montarCols();
        tbody.innerHTML = `<tr><td colspan="${COLS.length}" class="text-muted text-center py-3">Carregando…</td></tr>`;
        try {
            const r = await fetch(apiPath("/api/premiacao-caixa?all=1"));
            const d = await r.json();
            if (d.status !== "success") throw new Error(d.message || "Falha");
            LINHAS = mapLinhas(d.registros || []);
            FILTERS = {};
            BUSCA_CONCURSO = "";
            PAGE = 1;
            setBuscaMsg("");
            const buscaInput = document.getElementById("premiacaoBuscaConcurso");
            if (buscaInput) buscaInput.value = "";
            ULTIMO = LINHAS.length ? LINHAS.reduce((a, b) => Number(a.concurso) > Number(b.concurso) ? a : b) : null;
            if (status) {
                const excelMax = d.excel_concurso_maximo || 0;
                const excelN = d.excel_concursos || 0;
                let extra = `Histórico: ${d.total || LINHAS.length} concursos.`;
                if (excelN) {
                    extra += ` Premiação Excel: ${excelN} concurso(s), até #${excelMax}.`;
                    if (excelMax && (d.total || 0) > excelMax) {
                        extra += ` Concursos acima de #${excelMax} ainda não estão no arquivo.`;
                    }
                } else {
                    extra += " Sem premiação no Excel — clique em Atualizar premiação (Excel).";
                }
                status.textContent = extra;
            }
            render();
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="${COLS.length}" class="text-danger text-center py-3">${esc(e.message || e)}</td></tr>`;
        }
    }
    async function atualizarExcel() {
        const btn = document.getElementById("btnPremiacaoCaixa");
        const status = document.getElementById("premiacaoCaixaStatus");
        const labelOk = '<i class="fas fa-file-excel me-1"></i>Atualizar premiação (Excel)';
        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Lendo Excel…'; }
        if (status) status.textContent = "Importando premiação do Excel CAIXA (sem alterar dezenas)…";
        try {
            const r = await fetch(apiPath("/api/premiacao-caixa/atualizar"), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ fonte: "excel", baixar: true }),
            });
            const d = await r.json();
            if (d.status === "error") throw new Error(d.message || "Falha ao atualizar");
            if (status) status.textContent = d.message || "Atualizado.";
            await reload();
            await carregarRanking();
        } catch (e) {
            if (status) status.textContent = "Erro: " + (e.message || e);
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = labelOk; }
        }
    }
    async function carregarRanking() {
        const tabela = document.getElementById("rankingUfTabela");
        const tbody = tabela?.querySelector("tbody");
        const toggleWrap = document.getElementById("rankingUfToggleWrap");
        const btnToggle = document.getElementById("btnRankingUfToggle");
        if (!tbody) return;
        try {
            const r = await fetch(apiPath("/api/ranking-uf-pagamentos"));
            const d = await r.json();
            if (d.status !== "success") throw new Error(d.message || "Falha");
            const itens = d.ranking || [];
            if (!itens.length) {
                tbody.innerHTML = '<tr><td colspan="3" class="text-muted text-center py-3">Sem cidade/UF no Excel complementar. Clique em Atualizar premiação (Excel).</td></tr>';
                if (toggleWrap) toggleWrap.classList.add("d-none");
                return;
            }
            tabela?.classList.remove("uf-expandido");
            tbody.innerHTML = itens.map(it => {
                const pos = Number(it.posicao) || 0;
                const topCls = pos === 1 ? "uf-top1" : (pos === 2 ? "uf-top2" : (pos === 3 ? "uf-top3" : "uf-rest"));
                const trophy = pos >= 1 && pos <= 3 ? `<i class="fas fa-trophy uf-trophy" title="${pos}º lugar"></i>` : "";
                return `<tr class="${topCls}"><td>${trophy}${esc(it.posicao)}º</td><td><strong>${esc(it.uf)}</strong></td><td>${esc(it.quantidade)}</td></tr>`;
            }).join("");
            const restos = itens.filter(it => (Number(it.posicao) || 0) > 3).length;
            if (toggleWrap && btnToggle) {
                if (restos > 0) {
                    toggleWrap.classList.remove("d-none");
                    btnToggle.setAttribute("aria-expanded", "false");
                    btnToggle.innerHTML = `Ver demais UFs (${restos}) <i class="fas fa-chevron-down"></i>`;
                } else toggleWrap.classList.add("d-none");
            }
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="3" class="text-danger text-center py-3">${esc(e.message || e)}</td></tr>`;
            if (toggleWrap) toggleWrap.classList.add("d-none");
        }
    }
    function definirOrdem(modo) {
        CRESCENTE = modo === "crescente";
        COLS.filter(c => c.type === "bola").forEach(c => { delete FILTERS[c.key]; });
        if (String(SORT.key || "").startsWith("b") || String(SORT.key || "").startsWith("s2")) {
            SORT = { key: "concurso", dir: "desc" };
        }
        PAGE = 1;
        render();
    }
    function bind() {
        document.getElementById("btnPremiacaoCaixa")?.addEventListener("click", atualizarExcel);
        document.getElementById("btnOrdemSorteio")?.addEventListener("click", () => definirOrdem("sorteio"));
        document.getElementById("btnOrdemCresc")?.addEventListener("click", () => definirOrdem("crescente"));
        document.getElementById("premiacaoPageSize")?.addEventListener("change", () => { PAGE = 1; SIZE = pageSizeAtual(); render(); });
        document.getElementById("btnPremiacaoBuscaConcurso")?.addEventListener("click", pesquisarConcurso);
        document.getElementById("btnPremiacaoLimparBusca")?.addEventListener("click", resetarPesquisaConcurso);
        document.getElementById("premiacaoBuscaConcurso")?.addEventListener("keydown", (ev) => {
            if (ev.key === "Enter") { ev.preventDefault(); pesquisarConcurso(); }
        });
        document.querySelector("#premiacaoCaixaTabela thead")?.addEventListener("click", (ev) => {
            const fbtn = ev.target.closest(".px-filter-btn");
            if (!fbtn) return;
            ev.preventDefault();
            ev.stopPropagation();
            const th = fbtn.closest("th");
            if (fbtn.dataset.filter && th) abrirMenu(th, fbtn.dataset.filter);
        });
        document.getElementById("btnRankingUfToggle")?.addEventListener("click", () => {
            const tabela = document.getElementById("rankingUfTabela");
            const btn = document.getElementById("btnRankingUfToggle");
            if (!tabela || !btn) return;
            const aberto = tabela.classList.toggle("uf-expandido");
            const restos = tabela.querySelectorAll("tr.uf-rest").length;
            btn.setAttribute("aria-expanded", aberto ? "true" : "false");
            btn.innerHTML = aberto ? `Ocultar demais UFs <i class="fas fa-chevron-up"></i>` : `Ver demais UFs (${restos}) <i class="fas fa-chevron-down"></i>`;
        });
        document.addEventListener("click", (ev) => {
            if (!MENU) return;
            if (ev.target.closest(".px-excel-menu") || ev.target.closest(".px-filter-btn")) return;
            fecharMenu();
        });
        document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") fecharMenu(); });
        window.addEventListener("scroll", (ev) => {
            if (!MENU) return;
            if (MENU.contains(ev.target)) return;
            fecharMenu();
        }, true);
        window.addEventListener("resize", () => { if (MENU) fecharMenu(); });
    }

    window.PremiacaoCaixa = { reload, init: bind };
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", async () => { bind(); await reload(); await carregarRanking(); });
    } else {
        bind();
        reload().then(carregarRanking);
    }
})();
