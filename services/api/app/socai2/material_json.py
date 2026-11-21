"""Exact JSON content reads and the fusion.first-result.v2 digest format."""
import json
from decimal import Decimal


def loads(value):
    return json.loads(value, parse_float=Decimal) if value is not None else None


def dumps(value):
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non_finite_material_number")
        return str(value)
    if isinstance(value, list):
        return "["+",".join(dumps(v) for v in value)+"]"
    if isinstance(value, dict):
        return "{"+",".join(dumps(k)+":"+dumps(value[k]) for k in sorted(value))+"}"
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)


def canonical_numbers(value):
    if isinstance(value, bool) or value is None:
        return dumps(value)
    if isinstance(value, (int,float,Decimal)):
        number=Decimal(str(value))
        if not number.is_finite():
            raise ValueError("non_finite_material_number")
        sign,digits,exponent=number.as_tuple()
        digits=list(digits)
        if not any(digits):
            return "0"
        while digits[-1]==0:
            digits.pop();exponent+=1
        return ("-" if sign else "")+"".join(map(str,digits))+"e"+str(exponent)
    if isinstance(value,list):
        return "["+",".join(canonical_numbers(v) for v in value)+"]"
    if isinstance(value,dict):
        return "{"+",".join(dumps(k)+":"+canonical_numbers(value[k]) for k in sorted(value))+"}"
    return dumps(value)
