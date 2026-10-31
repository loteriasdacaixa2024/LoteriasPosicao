import importlib
import threading


def _safe_sync_runner(app, service_module: str, service_class: str, sync_kwargs: dict | None = None):
    sync_kwargs = sync_kwargs or {}
    with app.app_context():
        try:
            mod = importlib.import_module(service_module)
            svc = getattr(mod, service_class)
            result = svc.sincronizar_banco(**sync_kwargs)
            app.logger.info("[AUTO_SYNC] Sincronizacao automatica concluida: %s.%s", service_module, service_class)
            news = 0
            if isinstance(result, dict):
                news = int(result.get("news") or result.get("sucessos") or 0)
            if news > 0:
                _agendar_melhores15(app, service_class)
        except Exception as exc:
            app.logger.exception("[AUTO_SYNC] Falha na sincronizacao automatica: %s", exc)


def _agendar_melhores15(app, service_class: str) -> None:
    try:
        from analises_gerais.sync_registry import SYNC_SERVICES
        chave = ""
        for key, meta in SYNC_SERVICES.items():
            if meta[1] == service_class:
                chave = key
                break
        if not chave:
            return
        from analise_comparar.melhores15 import agendar_melhores15
        agendar_melhores15(chave, app)
    except Exception:
        app.logger.exception("[AUTO_SYNC] Nao agendou a busca das melhores 15")


def start_auto_sync_once(app, service_module: str, service_class: str, sync_kwargs: dict | None = None):
    """
    Executa sincronizacao em background no startup sem bloquear o carregamento.
    Evita chamadas duplicadas por instancia de app usando flag interna.
    """
    if app.config.get("_AUTO_SYNC_STARTED"):
        return
    app.config["_AUTO_SYNC_STARTED"] = True
    th = threading.Thread(
        target=_safe_sync_runner,
        args=(app, service_module, service_class, sync_kwargs),
        daemon=True,
        name=f"auto-sync-{service_class.lower()}",
    )
    th.start()
