"""Retired synchronous stage endpoints; execution belongs to the core dispatcher.

The existing aggregate-router import may still include this empty router. No A/I
execution action or alternate submission path is provided by this module.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/socai2")
