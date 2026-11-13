"""Compatibility entrypoint for the external investigation HTTP application."""
import sys

from investigation_http import main as _implementation

sys.modules[__name__] = _implementation
