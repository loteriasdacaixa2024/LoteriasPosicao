# -*- coding: utf-8 -*-
"""
Proxy de modalidades pela Central (uma porta só — Dev Tunnels / Port Forward).

Ex.: /m/duplasena/analise/  →  http://127.0.0.1:5158/analise/
"""
from __future__ import annotations

import re
from typing import Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from flask import Request, Response, request

# Headers hop-by-hop que não devem ser repassados
_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "content-encoding",
    "content-length", "host",
}


def is_tunnel_or_remote_host(host: str) -> bool:
    h = (host or "").lower().split(":")[0]
    if not h or h in ("localhost", "127.0.0.1", "::1"):
        return False
    markers = (
        "devtunnels.ms",
        "githubpreview.dev",
        "app.github.dev",
        "ngrok",
        "loca.lt",
        "cloudflared",
        "trycloudflare.com",
    )
    return any(m in h for m in markers) or (not h.endswith(".local") and h.count(".") >= 1)


def modality_proxy_prefix(mod_id: str) -> str:
    return f"/m/{mod_id}"


def rewrite_absolute_urls(text: str, prefix: str, backend_port: int) -> str:
    """Reescreve paths absolutos e URLs localhost da modalidade para o prefixo /m/<mod>/."""
    p = prefix.rstrip("/")
    # URLs absolutas apontando para o backend local
    for host in ("127.0.0.1", "localhost"):
        text = re.sub(
            rf"https?://{host}:{backend_port}",
            p,
            text,
            flags=re.IGNORECASE,
        )
    # Já prefixados — não tocar
    # href="/..." src="/..." action="/..." fetch("/..." etc. (não começar com /m/)
    def _path_sub(match: re.Match) -> str:
        quote = match.group(1)
        path = match.group(2)
        if path.startswith(p + "/") or path == p or path.startswith(p + "?"):
            return match.group(0)
        if path.startswith("//"):  # protocol-relative CDN
            return match.group(0)
        if not path.startswith("/"):
            return match.group(0)
        return f"{match.group(0)[: match.start(2) - match.start()]}{p}{path}{quote}"

    # Mais simples e seguro: substituir padrões conhecidos
    patterns = [
        (r'(href=")(/)(?!m/)', rf'\1{p}/'),
        (r"(href=')(/)(?!m/)", rf"\1{p}/"),
        (r'(src=")(/)(?!m/)', rf'\1{p}/'),
        (r"(src=')(/)(?!m/)", rf"\1{p}/"),
        (r'(action=")(/)(?!m/)', rf'\1{p}/'),
        (r"(action=')(/)(?!m/)", rf"\1{p}/"),
        (r'(content=")(/)(?!m/)', rf'\1{p}/'),  # meta refresh
        (r'(url\(")(/)(?!m/)', rf'\1{p}/'),
        (r"(url\(')(/)(?!m/)", rf"\1{p}/"),
        (r'(url\()(/)(?!m/)', rf'\1{p}/'),
        (r'(fetch\(")(/)(?!m/)', rf'\1{p}/'),
        (r"(fetch\(')(/)(?!m/)", rf"\1{p}/"),
        (r'(axios\.[a-z]+\(")(/)(?!m/)', rf'\1{p}/'),
        (r'(["\'])(/static/)(?!)', rf'\1{p}/static/'),
        (r'(["\'])(/analise/)(?!)', rf'\1{p}/analise/'),
        (r'(["\'])(/geradores-elite/)(?!)', rf'\1{p}/geradores-elite/'),
        (r'(["\'])(/modelos/)(?!)', rf'\1{p}/modelos/'),
        (r'(["\'])(/desdobramento/)(?!)', rf'\1{p}/desdobramento/'),
        (r'(["\'])(/configuracoes/)(?!)', rf'\1{p}/configuracoes/'),
        (r'(["\'])(/central-conferencias/)(?!)', rf'\1{p}/central-conferencias/'),
        (r'(["\'])(/api/)(?!)', rf'\1{p}/api/'),
    ]
    for pat, repl in patterns:
        text = re.sub(pat, repl, text)
    # Corrige "//" duplo acidental após prefix (exceto http)
    text = text.replace(p + "//", p + "/")
    return text


def rewrite_location(location: str, prefix: str, backend_port: int) -> str:
    if not location:
        return location
    p = prefix.rstrip("/")
    # Absolute backend URL
    for host in ("127.0.0.1", "localhost"):
        for scheme in ("http", "https"):
            base = f"{scheme}://{host}:{backend_port}"
            if location.startswith(base):
                rest = location[len(base):] or "/"
                return p + (rest if rest.startswith("/") else "/" + rest)
    if location.startswith("/"):
        if location.startswith(p + "/") or location == p:
            return location
        return p + location
    return location


def proxy_modality(
    mod_id: str,
    port: int,
    subpath: str,
    req: Optional[Request] = None,
) -> Response:
    req = req or request
    prefix = modality_proxy_prefix(mod_id)
    path = subpath or ""
    if path and not path.startswith("/"):
        # Flask path: "analise/" without leading slash
        path = "/" + path
    if not path:
        path = "/"

    target = f"http://127.0.0.1:{port}{path}"
    qs = req.query_string.decode("utf-8", errors="ignore")
    if qs:
        target = target + "?" + qs

    headers = {
        k: v for k, v in req.headers
        if k.lower() not in _HOP
    }
    headers["Host"] = f"127.0.0.1:{port}"
    headers["X-Forwarded-Prefix"] = prefix
    headers["X-Forwarded-Proto"] = req.headers.get("X-Forwarded-Proto") or req.scheme
    headers["X-Forwarded-Host"] = req.headers.get("X-Forwarded-Host") or req.host

    try:
        upstream = requests.request(
            method=req.method,
            url=target,
            headers=headers,
            data=req.get_data(),
            cookies=req.cookies,
            allow_redirects=False,
            timeout=120,
            stream=True,
        )
    except requests.exceptions.RequestException as e:
        return Response(
            f"Modalidade offline ({mod_id} porta {port}): {e}",
            status=502,
            content_type="text/plain; charset=utf-8",
        )

    excluded = set(_HOP) | {"content-security-policy"}
    out_headers: Dict[str, str] = {}
    for k, v in upstream.headers.items():
        if k.lower() in excluded:
            continue
        if k.lower() == "location":
            out_headers[k] = rewrite_location(v, prefix, port)
        else:
            out_headers[k] = v

    content_type = (upstream.headers.get("Content-Type") or "").lower()
    raw = upstream.content

    rewriteable = any(
        x in content_type
        for x in ("text/html", "javascript", "css", "json", "text/plain", "xml")
    )
    if rewriteable and raw:
        try:
            text = raw.decode("utf-8")
            text = rewrite_absolute_urls(text, prefix, port)
            # Injeta <base> em HTML para links relativos de página
            if "text/html" in content_type and "<base " not in text.lower():
                base_tag = f'<base href="{prefix}/">'
                if "<head>" in text.lower():
                    text = re.sub(
                        r"(<head[^>]*>)",
                        rf"\1{base_tag}",
                        text,
                        count=1,
                        flags=re.IGNORECASE,
                    )
                else:
                    text = base_tag + text
            raw = text.encode("utf-8")
            out_headers.pop("Content-Length", None)
        except Exception:
            pass

    return Response(raw, status=upstream.status_code, headers=out_headers)
