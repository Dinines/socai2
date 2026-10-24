"""Pure network identity rules; source text and retained material stay intact."""
from __future__ import annotations

import ipaddress
from typing import Any


def canonical_ip(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("ip_address_string_required")
    address = ipaddress.ip_address(value)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return str(address.ipv4_mapped)
    return str(address)


def same_network_filter(key: str, supplied: Any, expected: Any) -> bool:
    """Keep exact types/other filters; only IP spellings have equivalences."""
    if type(supplied) is not type(expected):
        return False
    if key in {"source_ip", "dest_ip"}:
        try:
            return canonical_ip(supplied) == canonical_ip(expected)
        except ValueError:
            return False
    return supplied == expected
