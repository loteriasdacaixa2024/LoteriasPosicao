# -*- coding: utf-8 -*-
"""Registro — Construtor de Construções."""
from __future__ import annotations

from typing import Any, Optional, Type

from .construtor_modalidades import CONSTRUTOR_REGISTRY, MODALIDADES_CONSTRUTOR


def get_construtor_service(modality_key: str) -> Optional[Type[Any]]:
    return CONSTRUTOR_REGISTRY.get(modality_key)


def tem_construtor(modality_key: str) -> bool:
    return modality_key in MODALIDADES_CONSTRUTOR
