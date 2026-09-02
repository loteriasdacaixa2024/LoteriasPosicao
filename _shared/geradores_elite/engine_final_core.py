"""
Engine Final — gerador pensante (aditivo).
Usa análises estatísticas já existentes em cada app (freq, atraso, convergência).
"""
import importlib
import math
import random
from typing import Any, Dict, List, Optional, Tuple

from .modality_config import MESES_ABREV, MODALITIES
from geradores_elite.comportamento.specs import MESES_NOME
from geradores_elite.comportamento.conferencia_estrategias import conferir_apostas_pontual


def get_config(modality_key: str) -> Dict[str, Any]:
    if modality_key not in MODALITIES:
        raise ValueError(f"Modalidade desconhecida: {modality_key}")
    return MODALITIES[modality_key]


def _import_service(cfg: Dict[str, Any]):
    mod_path, cls_name, method = cfg["service_import"]
    mod = importlib.import_module(mod_path)
    cls = getattr(mod, cls_name)
    return cls, method


def _norm_map(values: Dict[int, float]) -> Dict[int, float]:
    if not values:
        return {}
    mx = max(values.values()) or 1.0
    return {k: (v / mx) if mx else 0.0 for k, v in values.items()}


def _lotofacil_global_scores(cls) -> Dict[int, float]:
    """Agrega atraso posicional em score global 1–25 (sem inventar API inexistente)."""
    from models.shared import db
    from models.sorteio_lotofacil import SorteioLotofacil
    from sqlalchemy import desc

    sorteios = db.session.query(SorteioLotofacil).order_by(desc(SorteioLotofacil.concurso)).all()
    if not sorteios:
        return {}
    ultimo = sorteios[0].concurso
    total = len(sorteios)
    visto = {d: 0 for d in range(1, 26)}
    freq = {d: 0 for d in range(1, 26)}
    for s in sorteios:
        for i in range(1, 16):
            d = getattr(s, f"posicao_{i}")
            if d is None:
                continue
            freq[d] = freq.get(d, 0) + 1
            if visto.get(d, 0) == 0:
                visto[d] = s.concurso
    scores = {}
    for d in range(1, 26):
        atraso = (ultimo - visto[d]) if visto.get(d, 0) else total
        scores[d] = (freq.get(d, 0) / max(total * 15, 1)) * 40 + (atraso / max(total, 1)) * 60
    return scores


def build_dezena_scores(modality_key: str) -> Tuple[Dict[int, float], Optional[Dict[str, Any]]]:
    cfg = get_config(modality_key)
    meta: Dict[str, Any] = {"modo_scores": "inteligente"}

    if cfg["loader"] == "supersete_colunas":
        cls, method = _import_service(cfg)
        data = getattr(cls, method)()
        if not data:
            return {}, None
        col_scores = {}
        for col in range(1, 8):
            col_data = data.get(col) or data.get(str(col))
            if not col_data:
                continue
            freq = col_data.get("freq", {})
            atraso = col_data.get("atraso", {})
            sc = {}
            for d in range(0, 10):
                sc[d] = freq.get(d, 0) * 0.45 + atraso.get(d, 0) * 0.55
            col_scores[col] = sc
        meta["supersete_colunas"] = col_scores
        return {}, meta

    if cfg["loader"] == "lotofacil":
        scores = _lotofacil_global_scores(None)
        return scores, meta

    cls, method = _import_service(cfg)
    raw = getattr(cls, method)()
    if not raw:
        return {}, None

    dados = raw.get("dados") or raw.get("dados_dezenas") or []
    scores: Dict[int, float] = {}
    for row in dados:
        d = row.get("dezena")
        if d is None:
            d = row.get("numero")
        if d is None:
            continue
        freq = float(row.get("freq", 0))
        atraso = float(row.get("atraso", 0))
        pct = float(row.get("pct", 0))
        scores[int(d)] = freq * 0.35 + atraso * 0.45 + pct * 0.2

    if cfg["loader"] == "diadesorte":
        meta["meses_stats"] = raw.get("dados_meses") or []
    if cfg["loader"] == "timemania":
        meta["times_stats"] = raw.get("dados_times") or []
    if cfg["loader"] == "maismilionaria":
        meta["trevos_stats"] = raw.get("dados_trevos") or []

    ultimos = None
    try:
        ultimos = cls.ultimos_sorteios()
    except Exception:
        pass
    if ultimos and len(ultimos) > 0:
        u = ultimos[0]
        nums = u.get("dezenas") or u.get("numeros") or []
        for n in nums:
            nn = int(n)
            if nn in scores:
                scores[nn] += cfg["sorteadas"] * 0.8

    return scores, meta


def _pick_extra_mes(meta: Dict[str, Any], criterio: str) -> Tuple[int, str, str]:
    meses = meta.get("meses_stats") or []
    if not meses:
        return 1, "Janeiro", "#868e96"
    if criterio == "frequente":
        best = max(meses, key=lambda m: m.get("freq", 0))
    else:
        best = max(meses, key=lambda m: m.get("atraso", 0))
    num = int(best.get("mes_num", 1))
    nome = best.get("mes_nome", MESES_ABREV.get(num, str(num)))
    return num, nome, "#868e96"


def _pick_extra_time(meta: Dict[str, Any], criterio: str) -> Tuple[int, str]:
    times = meta.get("times_stats") or []
    if not times:
        return 1, "Time 1"
    if criterio == "frequente":
        best = max(times, key=lambda t: t.get("freq", 0))
    else:
        best = max(times, key=lambda t: t.get("atraso", 0))
    return int(best.get("time_num", 1)), best.get("time_nome", "Time")


def _pick_extra_trevos(meta: Dict[str, Any], qtd: int = 2) -> List[int]:
    trevos = meta.get("trevos_stats") or []
    if not trevos:
        return sorted(random.sample(range(1, 7), min(qtd, 6)))
    ranked = sorted(
        trevos,
        key=lambda t: float(t.get("atraso", 0)) * 0.55 + float(t.get("freq", 0)) * 0.45,
        reverse=True,
    )
    out = []
    for t in ranked:
        tr = int(t.get("trevo", t.get("dezena", 0)))
        if tr and tr not in out:
            out.append(tr)
        if len(out) >= qtd:
            break
    while len(out) < qtd:
        c = random.randint(1, 6)
        if c not in out:
            out.append(c)
    return sorted(out)


def _fmt_dezena(n: int, cfg: Dict[str, Any]) -> str:
    # Super Sete / colunas: dígito único 0–9 (nunca "00", "05"…)
    if cfg.get("export_is_columns") or cfg.get("loader") == "supersete_colunas":
        return str(int(n))
    if cfg.get("dezena_min") == 0 and cfg.get("total") == 100:
        return f"{int(n):02d}"
    return f"{int(n):02d}"


def _arrays_equal(a: List[int], b: List[int]) -> bool:
    return len(a) == len(b) and all(x == y for x, y in zip(a, b))


def _montar_aposta(
    scores: Dict[int, float],
    cfg: Dict[str, Any],
    k: int,
    idx: int,
    anteriores: List[List[int]],
    candidatos: Optional[List[int]] = None,
) -> List[int]:
    dmin, dmax = cfg["dezena_min"], cfg["dezena_max"]
    universo = sorted(candidatos) if candidatos else list(range(dmin, dmax + 1))
    ranked = sorted(
        ((d, scores.get(d, 0.0)) for d in universo),
        key=lambda x: (-x[1], x[0]),
    )
    if idx == 0:
        return sorted([d for d, _ in ranked[:k]])

    pool_size = min(len(ranked), max(k + 8, k + 4 + idx * 4))
    pool = [d for d, _ in ranked[:pool_size]]
    jitter = 22 + idx * 10

    for _ in range(50):
        chosen = []
        remaining = list(pool)
        for _j in range(k):
            if not remaining:
                break
            wts = [max(0.05, scores.get(n, 0) + random.random() * jitter) for n in remaining]
            s = sum(wts)
            r = random.random() * s
            pick_i = 0
            for i, w in enumerate(wts):
                r -= w
                if r <= 0:
                    pick_i = i
                    break
            chosen.append(remaining.pop(pick_i))
        chosen = sorted(chosen)
        if not any(_arrays_equal(chosen, p) for p in anteriores):
            return chosen

    trial = sorted([d for d, _ in ranked[:k]])
    for s in range(k):
        for d, _ in ranked:
            if d in trial:
                continue
            alt = list(trial)
            alt[s] = d
            alt.sort()
            if not any(_arrays_equal(alt, p) for p in anteriores):
                return alt
    return trial


def _montar_supersete(meta: Dict[str, Any], idx: int, anteriores: List[List[int]]) -> List[int]:
    cols = meta.get("supersete_colunas") or {}
    aposta = []
    for col in range(1, 8):
        sc = cols.get(col) or cols.get(str(col)) or {}
        ranked = sorted(sc.items(), key=lambda x: (-x[1], x[0]))
        if idx == 0 and ranked:
            aposta.append(int(ranked[0][0]))
        else:
            top = [int(d) for d, _ in ranked[:4]] or list(range(10))
            aposta.append(random.choice(top))
    if idx > 0 and any(_arrays_equal(aposta, p) for p in anteriores):
        c = random.randint(1, 7)
        aposta[c - 1] = (aposta[c - 1] + 1 + idx) % 10
    return aposta


def _payload_mes(num: int, nome: Optional[str] = None) -> Dict[str, Any]:
    mn = int(num)
    nome_full = (nome or MESES_NOME.get(mn, str(mn))).strip()
    return {
        "tipo": "mes",
        "num": mn,
        "label": MESES_ABREV.get(mn, nome_full[:3]),
        "mes_nome": nome_full,
    }


def _extra_mes_comportamento(aposta_idx: int) -> Optional[Dict[str, Any]]:
    """Mês da Sorte — pool dos ausentes nos últimos 10 concursos (coluna MS)."""
    from diadesorte.meses_indicados import carregar_meses_indicados, extra_mes_ciclo
    from models.sorteio_diadesorte import SorteioDiaDeSorte

    analise = carregar_meses_indicados(SorteioDiaDeSorte)
    if not analise.get("sucesso"):
        return None
    ciclo = extra_mes_ciclo(analise, aposta_idx)
    if not ciclo:
        return None
    return _payload_mes(ciclo["mes_num"], ciclo.get("mes_nome"))


def _meses_indicados_analise_ds() -> Dict[str, Any]:
    from diadesorte.meses_indicados import carregar_meses_indicados
    from models.sorteio_diadesorte import SorteioDiaDeSorte

    return carregar_meses_indicados(SorteioDiaDeSorte)


def _resolver_conjunto_base(
    modality_key: str,
    sessao_id: Optional[int],
    k: int,
) -> Tuple[List[int], Optional[str]]:
    """Pool fixo de 16 dezenas salvo no Construtor."""
    from geradores_elite.construtor import get_construtor_service

    svc = get_construtor_service(modality_key)
    if not svc:
        return [], "Construtor de Construções indisponível nesta modalidade."
    if not sessao_id:
        return [], "Selecione uma sessão do Construtor."

    data = svc.buscar_sessao(int(sessao_id))
    if not data:
        return [], f"Sessão #{sessao_id} não encontrada."

    pool = sorted(int(d) for d in (data.get("conjunto_base") or []))
    if not pool:
        return [], "Salve o conjunto-base no Construtor antes de gerar."

    if len(pool) < k:
        return [], (
            f"Cada aposta pede {k} dezenas, mas o conjunto-base tem {len(pool)}."
        )

    return pool, None


def _filtrar_scores_conjunto(scores: Dict[int, float], pool: List[int]) -> Dict[int, float]:
    out = {d: float(scores.get(d, 0.1)) for d in pool}
    return out


def gerar_apostas(
    modality_key: str,
    quantidade: int,
    qtd_dezenas: Optional[int] = None,
    modo: str = "convergencia",
    extra_criterio: str = "atrasado",
    mes_manual: Optional[int] = None,
    sessao_id: Optional[int] = None,
) -> Dict[str, Any]:
    cfg = get_config(modality_key)
    qtd = max(1, min(50, int(quantidade)))
    k = int(qtd_dezenas or cfg["pick_default"])
    k = max(cfg["pick_min"], min(cfg["pick_max"], k))

    scores, meta = build_dezena_scores(modality_key)
    if meta is None:
        meta = {}

    conjunto_base_info: Optional[Dict[str, Any]] = None
    pool_conjunto: Optional[List[int]] = None

    if modo == "conjunto_base":
        pool, err_cb = _resolver_conjunto_base(modality_key, sessao_id, k)
        if err_cb:
            return {"sucesso": False, "erro": err_cb}
        pool_conjunto = pool
        scores = _filtrar_scores_conjunto(scores, pool)
        conjunto_base_info = {
            "sessao_id": int(sessao_id),
            "dezenas": pool,
            "qtd": len(pool),
        }
        meta["conjunto_base"] = conjunto_base_info

    if modo == "cobertura" and scores:
        ranked_keys = sorted(scores.keys(), key=lambda d: -scores[d])
        nucleus = ranked_keys[: min(9, len(ranked_keys))]
        for d in nucleus:
            scores[d] = scores.get(d, 0) * 1.35

    apostas_out = []
    anteriores: List[List[int]] = []

    usar_mes_comportamento = (
        cfg.get("extra") == "mes"
        and modality_key == "diadesorte"
        and extra_criterio == "comportamento"
        and not mes_manual
    )
    ms_analise: Optional[Dict[str, Any]] = None
    if usar_mes_comportamento:
        ms_analise = _meses_indicados_analise_ds()
        if not ms_analise.get("sucesso"):
            return {
                "sucesso": False,
                "erro": ms_analise.get("erro") or "Não foi possível calcular meses indicados.",
            }
        if ms_analise.get("sem_indicados"):
            return {
                "sucesso": False,
                "erro": (
                    "Nenhum mês indicado: todos os 12 meses saíram nos últimos 10 concursos. "
                    "Use outro critério de mês ou o modo Fixo."
                ),
                "meses_indicados": ms_analise,
            }

    extra_payload: Dict[str, Any] = {}
    if cfg.get("extra") == "mes" and meta and not usar_mes_comportamento:
        mn = int(mes_manual) if mes_manual else None
        if mn:
            meses = meta.get("meses_stats") or []
            nome = next(
                (m.get("mes_nome") for m in meses if int(m.get("mes_num", 0)) == mn),
                MESES_NOME.get(mn, str(mn)),
            )
            extra_payload = _payload_mes(mn, nome)
        else:
            num, nome, _ = _pick_extra_mes(meta, extra_criterio)
            extra_payload = _payload_mes(num, nome)
    elif cfg.get("extra") == "time" and meta:
        num, nome = _pick_extra_time(meta, extra_criterio)
        extra_payload = {"tipo": "time", "num": num, "label": nome}
    elif cfg.get("extra") == "trevo" and meta:
        trevos = _pick_extra_trevos(meta, cfg.get("trevo_pick", 2))
        extra_payload = {"tipo": "trevo", "numeros": trevos, "label": " ".join(str(t) for t in trevos)}

    for i in range(qtd):
        if cfg["loader"] == "supersete_colunas":
            nums = _montar_supersete(meta, i, anteriores)
        else:
            if not scores:
                scores = {d: random.random() for d in range(cfg["dezena_min"], cfg["dezena_max"] + 1)}
            nums = _montar_aposta(scores, cfg, k, i, anteriores, candidatos=pool_conjunto)
        anteriores.append(nums)

        ap_extra = dict(extra_payload)
        if usar_mes_comportamento:
            comp = _extra_mes_comportamento(i)
            if not comp:
                return {
                    "sucesso": False,
                    "erro": "Falha ao atribuir mês do histórico comportamental.",
                    "meses_indicados": ms_analise,
                }
            ap_extra = comp

        apostas_out.append({"dezenas": nums, "extras": ap_extra})

    out: Dict[str, Any] = {
        "sucesso": True,
        "modalidade": cfg["nome"],
        "modo": modo,
        "quantidade": qtd,
        "dezenas_por_aposta": k if cfg["loader"] != "supersete_colunas" else 7,
        "apostas": apostas_out,
        "extra": extra_payload,
        "extra_criterio": extra_criterio,
        "cfg_ui": {
            "pick_min": cfg["pick_min"],
            "pick_max": cfg["pick_max"],
            "pick_default": cfg["pick_default"],
            "extra": cfg.get("extra"),
            "dezena_badge_style": cfg.get("dezena_badge_style", ""),
            "trevo_badge_style": cfg.get("trevo_badge_style", ""),
        },
    }
    if ms_analise:
        out["meses_indicados"] = ms_analise
    if conjunto_base_info:
        out["conjunto_base"] = conjunto_base_info
    try:
        from geradores_elite.validacao.validador_global import ValidadorGeradoresElite
        out = ValidadorGeradoresElite.aplicar(
            out, origem="engine_final", modality_key=modality_key, campo="apostas",
        )
    except Exception:
        pass
    return out


def formatar_export_txt(modality_key: str, apostas: List[Dict], extra: Dict) -> str:
    cfg = get_config(modality_key)
    lines = []
    joiner = cfg.get("export_join", " ")
    for ap in apostas:
        nums = ap.get("dezenas") or []
        if cfg.get("export_is_columns"):
            dez = "".join(str(n) for n in nums)
        else:
            dez = joiner.join(_fmt_dezena(n, cfg) for n in nums)
        ex = ap.get("extras") or extra or {}
        suffix = ""
        if ex.get("tipo") == "mes":
            suffix = f" {MESES_ABREV.get(int(ex.get('num', 1)), ex.get('label', '')[:3])}"
        elif ex.get("tipo") == "time":
            suffix = f" {ex.get('label', '')}"
        elif ex.get("tipo") == "trevo":
            tr = ex.get("numeros") or []
            suffix = f" T{'-'.join(str(t) for t in tr)}"
        lines.append(f"{dez}{suffix}".strip())
    return "\n".join(lines)


def _conferencia_svc(modality_key: str):
    from geradores_elite.construtor import get_construtor_service

    return get_construtor_service(modality_key)


def _extra_acertou(ex: Dict[str, Any], sorteio: Any) -> Optional[bool]:
    if not ex or not ex.get("tipo"):
        return None
    if ex.get("tipo") == "mes":
        mn = getattr(sorteio, "mes_num", None)
        if mn is None:
            return None
        return int(ex.get("num", 0)) == int(mn)
    if ex.get("tipo") == "time":
        tn = getattr(sorteio, "time_num", None) or getattr(sorteio, "time", None)
        if tn is None:
            return None
        return int(ex.get("num", 0)) == int(tn)
    if ex.get("tipo") == "trevo":
        tr = ex.get("numeros") or []
        if not tr:
            return None
        s1 = getattr(sorteio, "trevo1", None) or getattr(sorteio, "t1", None)
        s2 = getattr(sorteio, "trevo2", None) or getattr(sorteio, "t2", None)
        if s1 is None or s2 is None:
            return None
        sort_tr = {int(s1), int(s2)}
        return sort_tr == set(int(t) for t in tr)
    return None


def conferir_apostas_engine(
    modality_key: str,
    apostas: List[Dict[str, Any]],
    concurso: int,
) -> Dict[str, Any]:
    svc = _conferencia_svc(modality_key)
    if not svc:
        return {"sucesso": False, "erro": "Conferência indisponível para esta modalidade."}

    from models.shared import db

    sorteio = db.session.get(svc._model(), int(concurso))
    if not sorteio:
        return {"sucesso": False, "erro": f"Concurso {concurso} não encontrado."}

    # Super Sete: lista ordenada (nunca set — repetições e posição importam).
    positional = modality_key == "supersete" or (
        get_config(modality_key).get("loader") == "supersete_colunas"
    )
    sorteadas = list(svc._dezenas_from_sorteio(sorteio))
    cfg = get_config(modality_key)
    max_ac = int(cfg.get("sorteadas") or svc._spec().acertos_max_possivel)

    scores = []
    for i, ap in enumerate(apostas or [], start=1):
        dz = list(ap.get("dezenas") or [])
        ac = svc._contar_acertos(dz, sorteadas)
        ex = dict(ap.get("extras") or {})
        ac_extra = _extra_acertou(ex, sorteio)
        if positional:
            acertadas = [
                dz[j]
                for j in range(min(len(dz), len(sorteadas)))
                if dz[j] == sorteadas[j]
            ]
        else:
            acertadas = sorted(set(dz) & set(sorteadas))
        scores.append({
            "numero": ap.get("numero", i),
            "dezenas": dz,
            "extras": ex,
            "acertos": ac,
            "acertadas": acertadas,
            "acerto_extra": ac_extra,
        })

    base = conferir_apostas_pontual(
        [{"numero": s["numero"], "dezenas": s["dezenas"]} for s in scores],
        sorteadas if positional else sorted(set(sorteadas)),
        max_ac,
        positional=positional,
    )
    base["sucesso"] = True
    base["concurso"] = int(concurso)
    base["data"] = getattr(sorteio, "data", "") or ""
    base["sorteadas"] = list(sorteadas) if positional else sorted(set(sorteadas))
    base["apostas"] = scores
    base["max_acertos_possivel"] = max_ac
    base.update(svc._extras_ultimo_sorteio(sorteio))
    return base


def backtest_apostas_engine(
    modality_key: str,
    apostas: List[Dict[str, Any]],
    limite: int = 30,
) -> Dict[str, Any]:
    svc = _conferencia_svc(modality_key)
    if not svc:
        return {"sucesso": False, "erro": "Backtest indisponível para esta modalidade."}

    from models.shared import db
    from sqlalchemy import desc

    lim = max(5, min(int(limite), 200))
    rows = (
        db.session.query(svc._model())
        .order_by(desc(svc._model().concurso))
        .limit(lim)
        .all()
    )
    if not rows:
        return {"sucesso": False, "erro": "Nenhum sorteio no banco."}

    cfg = get_config(modality_key)
    extra_tipo = cfg.get("extra")
    positional = modality_key == "supersete" or cfg.get("loader") == "supersete_colunas"
    dist: Dict[int, int] = {3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
    total_max = 0
    extras_ok = 0
    destaques: List[Dict[str, Any]] = []

    for sorteio in rows:
        sorteadas = list(svc._dezenas_from_sorteio(sorteio))
        sorteadas_cmp = sorteadas if positional else set(sorteadas)
        best_ac = 0
        teve_extra = False
        for ap in apostas or []:
            ac = svc._contar_acertos(ap.get("dezenas") or [], sorteadas_cmp)
            if ac > best_ac:
                best_ac = ac
            ex = ap.get("extras") or {}
            ok = _extra_acertou(ex, sorteio)
            if ok:
                teve_extra = True

        if best_ac in dist:
            dist[best_ac] += 1
        total_max += best_ac
        if teve_extra:
            extras_ok += 1
        if best_ac >= (3 if positional else 4):
            destaques.append({
                "concurso": sorteio.concurso,
                "data": getattr(sorteio, "data", "") or "",
                "max_acertos": best_ac,
                "acerto_extra": teve_extra,
            })

    destaques.sort(key=lambda x: (-x["max_acertos"], -x["concurso"]))
    n = len(rows)

    # Melhor concurso: devolve acertadas por aposta para destacar em verde na UI
    melhor: Dict[str, Any] = {}
    if rows:
        melhor_row = max(
            rows,
            key=lambda s: max(
                (
                    svc._contar_acertos(
                        ap.get("dezenas") or [],
                        list(svc._dezenas_from_sorteio(s))
                        if positional
                        else set(svc._dezenas_from_sorteio(s)),
                    )
                    for ap in (apostas or [])
                ),
                default=0,
            ),
        )
        sorteadas_m = list(svc._dezenas_from_sorteio(melhor_row))
        sorteadas_m_cmp = sorteadas_m if positional else set(sorteadas_m)
        apostas_det = []
        for i, ap in enumerate(apostas or [], start=1):
            dz = list(ap.get("dezenas") or [])
            ac = svc._contar_acertos(dz, sorteadas_m_cmp)
            if positional:
                acertadas = [
                    dz[j]
                    for j in range(min(len(dz), len(sorteadas_m)))
                    if dz[j] == sorteadas_m[j]
                ]
            else:
                acertadas = sorted(set(dz) & set(sorteadas_m))
            apostas_det.append({
                "numero": ap.get("numero", i),
                "dezenas": dz,
                "acertos": ac,
                "acertadas": acertadas,
            })
        melhor = {
            "concurso": int(melhor_row.concurso),
            "data": getattr(melhor_row, "data", "") or "",
            "sorteadas": list(sorteadas_m) if positional else sorted(set(sorteadas_m)),
            "max_acertos": max((a["acertos"] for a in apostas_det), default=0),
            "apostas": apostas_det,
        }

    out: Dict[str, Any] = {
        "sucesso": True,
        "limite": lim,
        "concursos_analisados": n,
        "concurso_de": rows[-1].concurso,
        "concurso_ate": rows[0].concurso,
        "dist_3": dist[3],
        "dist_4": dist[4],
        "dist_5": dist[5],
        "dist_6": dist[6],
        "dist_7": dist[7],
        "media_max_acertos": round(total_max / n, 2) if n else 0.0,
        "destaques": destaques[:8],
        "melhor": melhor,
    }
    if extra_tipo == "mes":
        out["extras_acertados"] = extras_ok
        out["extra_label"] = "Mês"
    elif extra_tipo == "time":
        out["extras_acertados"] = extras_ok
        out["extra_label"] = "Time"
    elif extra_tipo == "trevo":
        out["extras_acertados"] = extras_ok
        out["extra_label"] = "Trevos"
    return out
