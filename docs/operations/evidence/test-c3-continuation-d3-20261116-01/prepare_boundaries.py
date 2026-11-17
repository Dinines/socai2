"""Explicit C3 edge fixtures; expected exclusions are declared before receiver tests."""
import argparse
import copy
import json

from prepare import HERE, ROOT, complete_spans, save, sha


def main(out):
    mother = (HERE / "fixtures-01/mother.txt").read_text()
    raw = json.loads(mother)
    original = (HERE / "fixtures-01/manifest.json").read_text()
    out.mkdir(exist_ok=False)
    cases = []

    def add(name, content, *, retain=(), exclude=(), forbidden_sections=(), dispatch=None, derivation,
            lexical_units=None, finish="stop"):
        (out / (name + ".txt")).write_text(content)
        expected = {"name": name, "finish_reason": finish, "fragment_sha256": sha(content),
                    "must_retain_business_paths": list(retain), "must_not_retain_paths": list(exclude),
                    "forbidden_sections": list(forbidden_sections), "dispatch_paths": dispatch,
                    "derivation": derivation, "lexical_units": lexical_units,
                    "expected_source": "explicit boundary contract and complete derived mother; no product parser",
                    "provenance": "controlled_fixture derived from real-02 C3; not real model output"}
        save(out / (name + ".expected.json"), expected)
        cases.append({"name": name, "sha256": sha(content), "finish_reason": finish})

    add("whitespace", " \n\t ", forbidden_sections=list(raw), dispatch=[], derivation="Replace whole response with whitespace")

    special = copy.deepcopy(raw)
    special["findings"][2]["statement"] = '原文包含括号{}[]、引号"、反斜杠\\和换行\n中文。'
    special_text = json.dumps(special, ensure_ascii=True)
    _, units = complete_spans(special_text)
    add("string-brackets-escaped-complete", special_text, retain=[u["path"] for u in units],
        derivation="Replace only F3 statement with literal brackets and escaped characters; reserialize as ASCII JSON",
        lexical_units=units)
    f3 = next(u for u in units if u["path"] == "$.findings[2]")
    statement = special_text.index('"statement"', f3["value_span"][0], f3["value_span"][1])
    cut = special_text.index("\\u", statement, f3["value_span"][1]) + 4
    add("half-unicode-escape", special_text[:cut], retain=[u["path"] for u in units if u["value_span"][1] <= cut],
        exclude=["$.findings[2]"], forbidden_sections=["questions", "domains", "conflicts", "followups"], dispatch=[],
        derivation={"mother": "string-brackets-escaped-complete.txt", "cut_offset": cut,
                    "offset_unit": "Unicode_code_point", "reason": "EOF inside four-digit Unicode escape"},
        lexical_units=[u for u in units if u["value_span"][1] <= cut], finish="length")

    prefix = '{"summary":' + json.dumps(raw["summary"], ensure_ascii=False) + ','
    # C3 has no legitimate numeric identity: the number must not become a member,
    # whether incomplete or complete. This also covers the terminal-number lexer.
    add("unterminated-number", prefix + '"members":[{"alert_id":12', retain=["$.summary"],
        forbidden_sections=["members"], dispatch=[], derivation="Follow a valid summary with EOF in numeric member identity",
        finish="length")

    _, mother_units = complete_spans(mother)
    first_member = next(u for u in mother_units if u["path"] == "$.members[0]")
    _start, end = first_member["value_span"]
    alias = raw["members"][0]["alert_id"]
    duplicate_member = mother[:end - 1] + ',"alert_id":' + json.dumps(alias) + mother[end - 1:]
    add("duplicate-member-key", duplicate_member, retain=["$.summary"], exclude=["$.members[0]"],
        derivation="Append the same alert_id key inside first member; duplicate is invalid even with equal values")
    members_end = mother.index("]", next(u for u in mother_units if u["path"] == "$.members[3]")["value_span"][1]) + 1
    duplicate_section = mother[:members_end] + ',"members":[]' + mother[members_end:]
    add("duplicate-members-section", duplicate_section, retain=["$.summary"], forbidden_sections=["members"],
        derivation="Insert conflicting root members=[] after original members; neither value may win")

    unknown = copy.deepcopy(raw)
    unknown["members"][0]["alert_id"] = "foreign-member"
    text = json.dumps(unknown, ensure_ascii=False)
    _, units = complete_spans(text)
    add("unknown-member", text, retain=["$.summary", "$.members[1]", "$.members[2]", "$.members[3]"],
        exclude=["$.members[0]"], derivation="Change only first member alias to an unknown identity", lexical_units=units)

    for empty in (True, False):
        value = copy.deepcopy(raw)
        if empty:
            value["followups"] = []
        else:
            value.pop("followups")
        text = json.dumps(value, ensure_ascii=False)
        _, units = complete_spans(text)
        add("explicit-empty-followups" if empty else "missing-followups", text,
            retain=["$.followups"] if empty else ["$.summary"], forbidden_sections=[] if empty else ["followups"],
            dispatch=[], derivation="Replace followups with explicit []" if empty else "Remove followups field entirely",
            lexical_units=units)

    value = copy.deepcopy(raw)
    value.pop("questions")
    text = json.dumps(value, ensure_ascii=False)
    _, units = complete_spans(text)
    add("followups-without-retained-question", text, retain=["$.followups[0]", "$.followups[1]"],
        forbidden_sections=["questions"], dispatch=[],
        derivation="Remove question section, keep both originally complete followups; no question may be invented",
        lexical_units=units)
    manifest = {"status": "prepared_not_executed", "mother_manifest_sha256": sha(original),
                "mother_manifest": str((HERE / "fixtures-01/manifest.json").relative_to(ROOT)),
                "fixtures": cases, "model_calls": 0, "database_calls": 0, "product_parser_calls": 0,
                "pending": "receiver interface/diagnostics and D3b completion-failure/C6 execution checks"}
    save(out / "manifest.json", manifest)
    print(json.dumps({"status": manifest["status"], "fixtures": len(cases)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=type(HERE), required=True)
    main(parser.parse_args().output)
