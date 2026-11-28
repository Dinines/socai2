"""Only synthetic opinion values; no production model output is rewritten."""


def opinion(source_ids=(), level="high"):
    return {"level": level, "reason": "Synthetic potential impact requires review.",
        "impact_basis": {"confirmed": [], "potential": ["Synthetic limited-scope impact."]},
        "source_refs": list(source_ids), "limitations": ["Synthetic structural test only."]}
