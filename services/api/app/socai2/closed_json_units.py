"""Locate explicitly selected closed JSON units; never repair or skip syntax."""
import json
import math

from .baseline_analysis_contract import AnalysisRejected


class Incomplete(Exception):
    pass


def unit_path(path):
    return "$" + "".join(f"[{key}]" if isinstance(key, int) else "." + key for key in path)


def branch(path):
    return path[:2] if len(path) > 1 and isinstance(path[1], int) else path[:1]


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise AnalysisRejected("duplicate_json_key")
        result[key] = value
    return result


class Reader:
    def __init__(self, text, fields, arrays):
        self.text, self.pos, self.path = text, 0, ()
        self.fields, self.arrays = set(fields), set(arrays)
        self.targets = self.fields | self.arrays
        self.values, self.spans, self.units = {}, {}, []
        self.invalid, self.closed_sections = [], []

    def peek(self):
        return self.text[self.pos:self.pos + 1]

    def space(self):
        while self.peek() and self.peek() in " \t\r\n":
            self.pos += 1

    def need(self, char):
        self.space()
        if not self.peek():
            raise Incomplete
        if self.peek() != char:
            raise AnalysisRejected("json_syntax_invalid")
        self.pos += 1

    def string(self):
        start = self.pos
        self.need('"')
        while self.peek():
            char = self.peek()
            self.pos += 1
            if char == '"':
                value = json.loads(self.text[start:self.pos])
                if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
                    raise AnalysisRejected("json_string_surrogate_invalid")
                return value
            if ord(char) < 32:
                raise AnalysisRejected("json_syntax_invalid")
            if char == "\\":
                if not self.peek():
                    raise Incomplete
                escape = self.peek()
                self.pos += 1
                if escape == "u":
                    for _ in range(4):
                        if not self.peek():
                            raise Incomplete
                        if self.peek() not in "0123456789abcdefABCDEF":
                            raise AnalysisRejected("json_syntax_invalid")
                        self.pos += 1
                elif escape not in '"\\/bfnrt':
                    raise AnalysisRejected("json_syntax_invalid")
        raise Incomplete

    def scalar_end(self):
        # A scalar ending at EOF could still be the prefix of another value.
        end = self.pos
        self.space()
        if not self.peek():
            raise Incomplete
        if self.peek() not in ",]}":
            raise AnalysisRejected("json_scalar_boundary_invalid")
        self.pos = end

    def number(self):
        start = self.pos
        if self.peek() == "-":
            self.pos += 1
        if not self.peek():
            raise Incomplete
        if self.peek() == "0":
            self.pos += 1
        elif self.peek() in "123456789":
            while self.peek() and self.peek() in "0123456789":
                self.pos += 1
        else:
            raise AnalysisRejected("json_number_invalid")
        for marker in (".", "eE"):
            if self.peek() and self.peek() in marker:
                self.pos += 1
                if marker == "eE" and self.peek() and self.peek() in "+-":
                    self.pos += 1
                if not self.peek():
                    raise Incomplete
                if self.peek() not in "0123456789":
                    raise AnalysisRejected("json_number_invalid")
                while self.peek() and self.peek() in "0123456789":
                    self.pos += 1
        self.scalar_end()
        value = json.loads(self.text[start:self.pos])
        if isinstance(value, float) and not math.isfinite(value):
            raise AnalysisRejected("json_number_invalid")
        return value

    def emit(self, path, value, start, kind):
        self.units.append({"path": unit_path(path), "kind": kind, "value": value,
                           "value_span": [start, self.pos]})

    def value(self, path):
        self.path = path
        self.space()
        start, char = self.pos, self.peek()
        if not char:
            raise Incomplete
        if char == '"':
            return self.string()
        if char == "{":
            return self.object(path)
        if char == "[":
            self.pos += 1
            self.space()
            result = []
            target = path in self.arrays
            if self.peek() == "]":
                self.pos += 1
                if target:
                    self.emit(path, [], start, "empty_array")
                return result
            while True:
                self.space()
                index, offset = len(result), self.pos
                value = self.value((*path, index))
                result.append(value)
                if target:
                    self.emit((*path, index), value, offset, str(path[-1]))
                self.space()
                if self.peek() == "]":
                    self.pos += 1
                    return result
                self.path = (*path, len(result))
                self.need(",")
        if char in "-0123456789":
            return self.number()
        literal = {"t": "true", "f": "false", "n": "null"}.get(char)
        if literal is None:
            raise AnalysisRejected("json_syntax_invalid")
        tail = self.text[self.pos:self.pos + len(literal)]
        if not literal.startswith(tail):
            raise AnalysisRejected("json_syntax_invalid")
        if len(tail) < len(literal):
            raise Incomplete
        self.pos += len(literal)
        self.scalar_end()
        return json.loads(literal)

    def object(self, path=()):
        self.need("{")
        self.space()
        if self.peek() == "}":
            self.pos += 1
            return {}
        result = {}
        while True:
            self.path = path
            self.space()
            key = self.string()
            self.path = (*path, key)
            if key in result:
                conflict = unit_path(branch(self.path))
                self.units = [u for u in self.units if u["path"] != conflict and not u["path"].startswith((conflict + "[", conflict + "."))]
                if not path:
                    for label in list(self.values):
                        if label == conflict or label.startswith((conflict + "[", conflict + ".")):
                            self.values.pop(label, None)
                            self.spans.pop(label, None)
                            self.closed_sections.remove(label)
                raise AnalysisRejected("duplicate_json_key")
            self.need(":")
            self.space()
            start = self.pos
            result[key] = self.value((*path, key))
            selected = (*path, key)
            if selected in self.targets:
                label = unit_path(selected)
                self.values[label], self.spans[label] = result[key], [start, self.pos]
                self.closed_sections.append(label)
                if selected in self.fields or not isinstance(result[key], list):
                    self.emit(selected, result[key], start, str(key))
            elif any(target[:len(selected)] == selected for target in self.targets):
                if not isinstance(result[key], dict):
                    self.invalid.append({"path": unit_path(selected), "reason_code": "container_type_invalid"})
            elif not path or any(target[:-1] == path for target in self.targets):
                self.invalid.append({"path": unit_path(selected), "reason_code": "unknown_section"})
            self.space()
            if self.peek() == "}":
                self.pos += 1
                return result
            self.path = path
            self.need(",")


def read_units(content, *, fields, arrays):
    if not isinstance(content, str) or not content.strip():
        return {"units": [], "closed_sections": [], "missing_units": [{"path": "$", "reason_code": "no_content"}],
                "invalid_units": [], "parse_state": "unusable", "truncated": False, "reasons": ["no_content"],
                "retained": {}, "value_spans": {}}
    # Strict decoding is attempted first, including duplicate keys and constants.
    complete = False
    try:
        complete = isinstance(json.loads(content, object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(AnalysisRejected("json_number_invalid"))), dict)
    except (ValueError, RecursionError):
        pass
    reader, missing, reasons, truncated = Reader(content, fields, arrays), [], [], False
    try:
        reader.object()
        reader.space()
        if reader.peek():
            raise AnalysisRejected("json_trailing_content")
    except Incomplete:
        truncated = True
        reasons.append("json_incomplete")
        missing.append({"path": unit_path(branch(reader.path)), "reason_code": "json_incomplete"})
    except (AnalysisRejected, ValueError, RecursionError) as exc:
        reason = str(exc) if isinstance(exc, AnalysisRejected) else "json_syntax_invalid"
        reasons.append(reason)
        reader.invalid.append({"path": unit_path(branch(reader.path)), "reason_code": reason})
        complete = False
    for target in (*fields, *arrays):
        key = unit_path(target)
        if key not in reader.closed_sections and not any(u["path"].startswith(key) for u in missing):
            missing.append({"path": key, "reason_code": "section_not_complete"})
    return {"units": reader.units, "closed_sections": reader.closed_sections, "missing_units": missing,
            "invalid_units": reader.invalid, "parse_state": "complete_json" if complete else "closed_units" if reader.units else "unusable",
            "truncated": truncated, "reasons": reasons, "retained": reader.values, "value_spans": reader.spans}
