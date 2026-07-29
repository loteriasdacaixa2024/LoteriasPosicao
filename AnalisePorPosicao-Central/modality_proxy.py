# -*- coding: utf-8 -*-
"""Proxy reverso path-based — Central /m/<modalidade>/ → localhost:515x."""
from __future__ import annotations

import re
from typing import Dict, Iterable, Optional, Tuple
from urllib.parse import urljoin, urlparse

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


def _rewrite_html(body: bytes, prefix: str, backend_port: int) -> bytes:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = body.decode("latin-1")
        except Exception:
            return body

    # atributos e fetch com path absoluto /
    for attr in ("href", "src", "action", "data-api", "data-href"):
        text = re.sub(
            rf'({attr}\s*=\s*["\'])/(?!/|m/)',
            rf"\1{prefix}/",
            text,
            flags=re.IGNORECASE,
        )
    text = re.sub(
        r"""(fetch\s*\(\s*["'])/(?!/|m/)""",
        rf"\1{prefix}/",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"""(url\(\s*["']?)/(?!/|m/)""",
        rf"\1{prefix}/",
        text,
        flags=re.IGNORECASE,
    )
    # backends absolutos locais
    for host in (f"127.0.0.1:{backend_port}", f"localhost:{backend_port}"):
        text = text.replace(f"http://{host}", prefix)
        text = text.replace(f"https://{host}", prefix)

    # base href ajuda paths relativos
    if re.search(r"(?i)<head[^>]*>", text) and f'href="{prefix}/"' not in text[:800]:
        text = re.sub(
            r"(?i)<head([^>]*)>",
            rf'<head\1><base href="{prefix}/">',
            text,
            count=1,
        )

    return text.encode("utf-8")


def proxy_modality_request(
    mod_id: str,
    backend_port: int,
    subpath: str,
    flask_request: Optional[Request] = None,
) -> Response:
    req = flask_request or request
    prefix = f"/m/{mod_id}"
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
    if "text/html" in content_type.lower():
        content = _rewrite_html(content, prefix, backend_port)
        # content-length mudou — remove se existir
        out_headers = [(k, v) for k, v in out_headers if k.lower() != "content-length"]

    return Response(content, status=upstream.status_code, headers=out_headers)
