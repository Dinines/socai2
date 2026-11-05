"""C6 compatibility does not weaken the strict parser or rewrite saved replies."""
import copy
import hashlib
import json

import pytest
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_delivery_compat import POLICY, normalize
from test_socai2_delivery_shape_rejections import candidate, parse


def test_known_null_extension_is_audited_then_passes_the_unchanged_parser():
    packet, context, value = candidate()
    value["analysis"]["conflicts_note"] = None
    raw = json.dumps(value, ensure_ascii=False)
    original = copy.deepcopy(value)
    with pytest.raises(AnalysisRejected, match="delivery_shape_invalid"):
        parse(packet, context, value)
    normalized, receipt = normalize(raw)
    result = parse(packet, context, json.loads(normalized))
    assert result.conclusion.text == value["conclusion"]["text"]
    assert receipt["policy"] == POLICY
    assert receipt["removed"] == [{"path": ["analysis", "conflicts_note"], "value": None}]
    assert receipt["original_content_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert receipt["normalized_content_sha256"] == hashlib.sha256(normalized.encode()).hexdigest()
    assert receipt["normalized_content"] == normalized
    assert value == original and json.loads(raw)["analysis"]["conflicts_note"] is None


@pytest.mark.parametrize("key,value", [("conflicts_note", "meaningful note"), ("conflicts_note", []),
    ("conflicts_note", False), ("another_extra", None)])
def test_other_extra_values_are_not_stripped(key, value):
    packet, context, answer = candidate()
    answer["analysis"][key] = value
    raw = json.dumps(answer)
    assert normalize(raw) == (raw, None)
    with pytest.raises(AnalysisRejected, match="delivery_shape_invalid"):
        parse(packet, context, answer)


def test_compatibility_does_not_fill_required_fields_or_bypass_citation_checks():
    packet, context, value = candidate()
    value["analysis"]["conflicts_note"] = None
    del value["analysis"]["followups"]
    normalized, _ = normalize(json.dumps(value))
    with pytest.raises(AnalysisRejected, match="delivery_shape_invalid"):
        parse(packet, context, json.loads(normalized))
    packet, context, value = candidate()
    value["analysis"]["conflicts_note"] = None
    value["conclusion"]["support_ids"] = ["not-in-this-request"]
    normalized, _ = normalize(json.dumps(value))
    with pytest.raises(AnalysisRejected, match="delivery_source_not_visible_or_duplicate"):
        parse(packet, context, json.loads(normalized))


@pytest.mark.parametrize("raw,error", [('{"analysis":{"conflicts_note":null,"conflicts_note":null}}',
    "duplicate_json_key"), ('{"analysis":{"conflicts_note":null},"value":NaN}', "invalid_json_number"),
    ('{"analysis":', "delivery_shape_invalid")])
def test_invalid_json_is_rejected_before_normalization(raw, error):
    with pytest.raises(AnalysisRejected, match=error):
        normalize(raw)
