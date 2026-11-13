"""Compatibility import; external HTTP implementation lives in investigation_http."""
import sys

from investigation_http.external_routes import analysis as _implementation

sys.modules[__name__] = _implementation
