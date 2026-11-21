"""Shared lake hostname policy; comparison matches ClickHouse lower(String)."""
from unicodedata import category

_ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def supported_hostname(value):
    return (isinstance(value, str) and 1 <= len(value) <= 253
            and all(char in "_.-" or category(char)[0] in "LNM" for char in value))


def hostname_key(value):
    """Fold ASCII only; retain all other code points and the stored original."""
    return value.translate(_ASCII_LOWER)
