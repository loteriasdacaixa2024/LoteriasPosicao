# -*- coding: utf-8 -*-
"""URLs públicas para Central + modalidades (localhost e Port Forward / tunnels)."""
from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

try:
    from configuracoes.config import CENTRAL_PORT, MODALITIES
except Exception:  # pragma: no cover
    CENTRAL_PORT = 8083
    MODALITIES = {}


def _env_public_host() -> Optional[str]:
    h = (os.getenv("PUBLIC_HOST") or os.getenv("MODULE_HOST") or "").strip()
    return h or None


def is_local_host(host: str) -> bool:
    if not host:
        return True
    h = host.split(",")[0].strip().lower()
    hostname = h.split(":")[0]
    return hostname in ("localhost", "127.0.0.1", "::1")


def is_tunnel_or_remote_host(host: str) -> bool:
    """True quando só a Central está publicada (dev tunnels / share) — usar proxy /m/."""
    if not host:
        return False
    if is_local_host(host):
        return False
    h = host.split(",")[0].strip().lower()
    if "devtunnels.ms" in h:
        return True
    if "githubpreview.dev" in h or "github.dev" in h or "app.github.dev" in h:
        return True
    # qualquer host não-local → proxy path (compartilhamento)
    return True


def modality_proxy_prefix(key: str) -> str:
    return f"/m/{key}"


def normalize_script_prefix(script_root: str = "", forwarded_prefix: str = "") -> str:
    """Prefixo público do Nginx, ex. /centralmodalidades. Vazio no acesso direto :8083."""
    p = (forwarded_prefix or script_root or "").strip().rstrip("/")
    if p and not p.startswith("/"):
        p = "/" + p
    return p


def rewrite_html_public_prefix(text: str, prefix: str) -> str:
    """Reescreve paths absolutos /... para {prefix}/... (idempotente)."""
    p = (prefix or "").rstrip("/")
    if not p or not text:
        return text
    skip = re.escape(p.lstrip("/"))
    pairs = (
        (rf'(href=")(/)(?!{skip}/)', rf"\1{p}/"),
        (rf"(href=')(/)(?!{skip}/)", rf"\1{p}/"),
        (rf'(src=")(/)(?!{skip}/)', rf"\1{p}/"),
        (rf"(src=')(/)(?!{skip}/)", rf"\1{p}/"),
        (rf'(action=")(/)(?!{skip}/)', rf"\1{p}/"),
        (rf"(action=')(/)(?!{skip}/)", rf"\1{p}/"),
        (rf'(fetch\(")(/)(?!{skip}/)', rf"\1{p}/"),
        (rf"(fetch\(')(/)(?!{skip}/)", rf"\1{p}/"),
        (rf"(fetch\(`)(/)(?!{skip}/)", rf"\1{p}/"),
        (rf"(= ')(/)(?!{skip}/)", rf"\1{p}/"),
        (rf'(= ")(/)(?!{skip}/)', rf"\1{p}/"),
    )
    for pat, repl in pairs:
        text = re.sub(pat, repl, text)
    return text


def rewrite_host_port(host: str, from_port: int, to_port: int) -> str:
    """
    Reescreve o host para outro porto em cenários de tunnel multi-porta.

    Exemplos:
      xxx-8083.brs.devtunnels.ms → xxx-5158.brs.devtunnels.ms
    """
    if not host:
        return host
    pat = re.compile(rf"(?P<pre>^|-)({from_port})(?P<suf>\.|$)")
    if pat.search(host):
        return pat.sub(lambda m: f"{m.group('pre')}{to_port}{m.group('suf')}", host, count=1)
    return host


def public_base_for_port(
    port: int,
    *,
    request_host: Optional[str] = None,
    request_scheme: Optional[str] = None,
    central_port: int = CENTRAL_PORT,
) -> str:
    env_host = _env_public_host()
    if env_host:
        if "://" in env_host:
            parsed = urlparse(env_host)
            scheme = parsed.scheme or "http"
            netloc = parsed.netloc or parsed.path
            host_only = netloc.split(":")[0]
            return f"{scheme}://{host_only}:{port}"
        return f"http://{env_host}:{port}"

    scheme = (request_scheme or "http").split(",")[0].strip() or "http"
    host = (request_host or "").split(",")[0].strip()
    if not host:
        return f"http://localhost:{port}"

    if ":" in host and not host.startswith("["):
        hostname, _, cur_port = host.rpartition(":")
        if cur_port.isdigit():
            if int(cur_port) == port:
                return f"{scheme}://{host}"
            return f"{scheme}://{hostname}:{port}"

    rewritten = rewrite_host_port(host, central_port, port)
    if rewritten != host:
        return f"{scheme}://{rewritten}"

    return f"{scheme}://localhost:{port}"


def modality_public_url(
    key: str,
    path: str = "/",
    *,
    request_host: Optional[str] = None,
    request_scheme: Optional[str] = None,
    force_proxy: Optional[bool] = None,
    request_prefix: Optional[str] = None,
) -> str:
    """
    Local: http://localhost:5158/...
    Tunnel/remoto: /m/duplasena/...  (mesma origem da Central 8083)
    Nginx público: /centralmodalidades/m/duplasena/...
    """
    mod = MODALITIES.get(key) or {}
    port = int(mod.get("porta") or 0)
    if not port:
        return path or "/"

    if not path.startswith("/"):
        path = "/" + path

    root = normalize_script_prefix(forwarded_prefix=request_prefix or "")
    use_proxy = force_proxy
    if use_proxy is None:
        use_proxy = is_tunnel_or_remote_host(request_host or "") or bool(root)

    if use_proxy:
        prefix = root + modality_proxy_prefix(key)
        if path == "/":
            return prefix + "/"
        return prefix + path

    base = public_base_for_port(
        port,
        request_host=request_host,
        request_scheme=request_scheme,
    )
    return base.rstrip("/") + path


def modalities_public_map(
    *,
    request_host: Optional[str] = None,
    request_scheme: Optional[str] = None,
    request_prefix: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    root = normalize_script_prefix(forwarded_prefix=request_prefix or "")
    use_proxy = is_tunnel_or_remote_host(request_host or "") or bool(root)
    out: Dict[str, Dict[str, Any]] = {}
    for key, meta in MODALITIES.items():
        port = int(meta.get("porta") or 0)
        out[key] = {
            "key": key,
            "nome": meta.get("nome", key),
            "porta": port,
            "via_proxy": use_proxy,
            "url": modality_public_url(
                key, "/",
                request_host=request_host,
                request_scheme=request_scheme,
                force_proxy=use_proxy,
                request_prefix=root,
            ),
        }
    return out
