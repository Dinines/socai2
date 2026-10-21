"""Resolve the marker format actually requested and returned by the model."""
from copy import deepcopy

import pytest

from app.context import knowledge_base as kb
from app.investigator.knowledge_prompt import report_knowledge_references
from app.investigator.state import InvestigatorState


def read():
    citation = {"marker": "KB1", "doc_id": "351c3e7d-008a-4bd4-805a-a2bca754cad1",
                "title": "ATT&CK reference: T1110.003 Password Spraying", "chunk_index": 0,
                "chunk_total": 1, "source_url": "https://attack.mitre.org/techniques/T1110/003",
                "content_sha256": "4a907cb2937248bce16544f3ff3d4027d19bffc01bdae0a8b3c4d235789ef9a8"}
    return {"runbooks": [deepcopy(citation)], "citations": [deepcopy(citation)]}


@pytest.mark.parametrize("text", ["See [KB1].", "According to KB1, this is background guidance.",
                                  "Reference (KB1).", "*Citation*: kb1 confirms this technique."])
def test_supplied_bracketed_and_plain_marker_formats_resolve(text):
    material = read()
    kb.record_model_citations(material, text)
    assert material["model_citations"] == ["KB1"]
    assert material["unresolvable_citations"] == []
    assert material["cited_sources"] == material["citations"]


def test_unknown_marker_stays_unresolvable_without_partial_identifier_matches():
    material = read()
    text = "[KB1], KB99; fooKB1, KB1_extra, KB1000, KB1x are identifiers."
    kb.record_model_citations(material, text)
    assert material["model_citations"] == ["KB1", "KB99"]
    assert material["unresolvable_citations"] == ["KB99"]
    assert kb.unresolvable_citations(text, material) == ["KB99"]
    assert [row["marker"] for row in material["cited_sources"]] == ["KB1"]


def test_captured_plain_marker_maps_to_source_without_rewriting_original_run():
    # Literal visible citation from Run36bd18e0. No model rerun or PG edit.
    text = "*Citation*: KB1 confirms this technique uses common passwords against many accounts to bypass lockout mechanisms."
    material = read()
    kb.record_model_citations(material, text)
    material["model_citations_by_agent"] = {"ReportWriterAgent": {
        key: deepcopy(material[key]) for key in ("model_citations", "unresolvable_citations", "cited_sources")}}
    state = InvestigatorState(case_id="source-marker-probe", knowledge_base_read=material)
    references = report_knowledge_references(state)
    assert "[KB1]" in references and material["citations"][0]["doc_id"] in references
    assert material["citations"][0]["content_sha256"] in references


def test_no_marker_does_not_create_model_citations():
    material = read()
    kb.record_model_citations(material, "No knowledge source was cited.")
    assert material["model_citations"] == material["cited_sources"] == []
