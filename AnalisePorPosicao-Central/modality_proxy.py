# -*- coding: utf-8 -*-
"""Proxy reverso path-based — Central /m/<modalidade>/ → localhost:515x."""
from __future__ import annotations

import json
import re
from typing import Optional
from urllib.parse import urljoin

import requests
from flask import Request, Response, request

_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
    "content-length",
}


def _rewrite_location(location: str, prefix: str, backend_port: int) -> str:
    if not location:
        return location
    # absoluto apontando para backend local
    for host in (f"127.0.0.1:{backend_port}", f"localhost:{backend_port}"):
        for scheme in ("http://", "https://"):
            base = f"{scheme}{host}"
            if location.startswith(base):
                rest = location[len(base):] or "/"
                if not rest.startswith("/"):
                    rest = "/" + rest
                return prefix + rest
    # path absoluto na origem
    if location.startswith("/") and not location.startswith("//"):
        if location.startswith(prefix + "/") or location == prefix:
            return location
        return prefix + location
    return location


def _rewrite_set_cookie(value: str, prefix: str) -> str:
    # Path=/ → Path=/m/duplasena/
    if re.search(r"(?i)path=/", value):
        value = re.sub(r"(?i)path=/", f"Path={prefix}/", value, count=1)
    return value


def _rewrite_urls(text: str, prefix: str, backend_port: int) -> str:
    skip = re.escape(prefix.lstrip("/"))
    neg = rf"(?!/|{skip}/|m/)"
    for attr in ("href", "src", "action", "data-api", "data-href"):
        text = re.sub(
            rf'({attr}\s*=\s*["\'])/{neg}',
            rf"\1{prefix}/",
            text,
            flags=re.IGNORECASE,
        )
    text = re.sub(
        rf"""(fetch\s*\(\s*["'`])/{neg}""",
        rf"\1{prefix}/",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        rf"""((?<![A-Za-z0-9_])url\(\s*["']?)/{neg}""",
        rf"\1{prefix}/",
        text,
        flags=re.IGNORECASE,
    )
    # JS externo: "/api/...", '/caixa-excel/...' (não passa pelo rewrite de HTML)
    for folder in ("api", "caixa-excel", "static", "analise", "modelos", "geradores-elite"):
        text = re.sub(
            rf"""(['"`])/{neg}{re.escape(folder)}/""",
            rf"\1{prefix}/{folder}/",
            text,
            flags=re.IGNORECASE,
        )
    for host in (f"127.0.0.1:{backend_port}", f"localhost:{backend_port}"):
        text = text.replace(f"http://{host}", prefix)
        text = text.replace(f"https://{host}", prefix)
    return text


def _prefix_runtime_script(prefix: str) -> str:
    """Intercepta fetch/XHR com path absoluto — só no acesso via proxy (remoto)."""
    p = json.dumps(prefix.rstrip("/"))
    return (
        '<script data-remote-prefix="1">'
        "(function(){"
        f"var P={p};"
        "window.__APP_ROOT__=P;"
        "function fix(u){"
        "if(typeof u!=='string')return u;"
        "if(!u||u.charAt(0)!=='/'||u.charAt(1)==='/')return u;"
        "if(u===P||u.indexOf(P+'/')===0)return u;"
        "return P+u;"
        "}"
        "if(window.fetch){var f=window.fetch;"
        "window.fetch=function(i,n){"
        "if(typeof i==='string')i=fix(i);"
        "return f.call(this,i,n);};}"
        "var o=XMLHttpRequest.prototype.open;"
        "XMLHttpRequest.prototype.open=function(){"
        "if(arguments.length>1)arguments[1]=fix(arguments[1]);"
        "return o.apply(this,arguments);};"
        "})();"
        "</script>"
    )


def _rewrite_html(body: bytes, prefix: str, backend_port: int) -> bytes:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = body.decode("latin-1")
        except Exception:
            return body

    text = _rewrite_urls(text, prefix, backend_port)

    if re.search(r"(?i)<head[^>]*>", text):
        inject = ""
        if 'data-remote-prefix="1"' not in text:
            inject += _prefix_runtime_script(prefix)
        if f'href="{prefix}/"' not in text[:1200]:
            inject += f'<base href="{prefix}/">'
        if inject:
            text = re.sub(
                r"(?i)<head([^>]*)>",
                rf"<head\1>{inject}",
                text,
                count=1,
            )

    return text.encode("utf-8")


def _rewrite_js(body: bytes, prefix: str, backend_port: int) -> bytes:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = body.decode("latin-1")
        except Exception:
            return body
    return _rewrite_urls(text, prefix, backend_port).encode("utf-8")


def proxy_modality_request(
    mod_id: str,
    backend_port: int,
    subpath: str,
    flask_request: Optional[Request] = None,
) -> Response:
    req = flask_request or request
    root = (req.headers.get("X-Forwarded-Prefix") or req.script_root or "").rstrip("/")
    # Evita /m/lotofacil/m/lotofacil se o header já vier com o prefixo da modalidade
    marker = f"/m/{mod_id}"
    if root.endswith(marker):
        prefix = root
    else:
        prefix = f"{root}{marker}" if root else marker
    path = (subpath or "").lstrip("/")
    target = f"http://127.0.0.1:{backend_port}/"
    if path:
        target = urljoin(target, path)

    qs = req.query_string.decode("utf-8", errors="ignore")
    if qs:
        target = target + ("&" if "?" in target else "?") + qs

    headers = {}
    for key, value in req.headers:
        lk = key.lower()
        if lk in _HOP_BY_HOP or lk == "host":
            continue
        headers[key] = value
    headers["Host"] = f"127.0.0.1:{backend_port}"
    headers["X-Forwarded-Prefix"] = prefix
    headers["X-Forwarded-Host"] = req.host
    headers["X-Forwarded-Proto"] = req.headers.get("X-Forwarded-Proto") or req.scheme

    try:
        upstream = requests.request(
            method=req.method,
            url=target,
            headers=headers,
            data=req.get_data(),
            cookies=req.cookies,
            allow_redirects=False,
            timeout=180,
        )
    except requests.exceptions.RequestException as e:
        return Response(
            f"Modalidade offline na porta {backend_port}: {e}",
            status=502,
            content_type="text/plain; charset=utf-8",
        )

    out_headers = []
    content_type = upstream.headers.get("Content-Type", "")
    for key, value in upstream.headers.items():
        lk = key.lower()
        if lk in _HOP_BY_HOP:
            continue
        if lk == "location":
            value = _rewrite_location(value, prefix, backend_port)
        elif lk == "set-cookie":
            value = _rewrite_set_cookie(value, prefix)
        out_headers.append((key, value))

    content = upstream.content
    ct = content_type.lower()
    path_l = (subpath or "").lower()
    rewritten = False
    if "text/html" in ct:
        content = _rewrite_html(content, prefix, backend_port)
        rewritten = True
    elif "javascript" in ct or "ecmascript" in ct or path_l.endswith(".js"):
        content = _rewrite_js(content, prefix, backend_port)
        rewritten = True
    if rewritten:
        out_headers = [(k, v) for k, v in out_headers if k.lower() != "content-length"]

    return Response(content, status=upstream.status_code, headers=out_headers)
