"""Compare only configured semantic fields; no inference from titles or verdicts."""
from .knowledge_config import at


def normalize(value, facet):
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        return None
    value = str(value).strip()
    if facet.normalization == "basename_casefold":
        value = value.replace("\\", "/").rsplit("/", 1)[-1]
    return (value.casefold() if facet.normalization != "exact" else value) or None


def material_facets(material, profile):
    return {name: sorted({n for path in facet.paths if (n := normalize(at(material, path), facet))})
            for name, facet in profile.applicability.facets.items()
            if any(normalize(at(material, path), facet) for path in facet.paths)}


def historical_facets(card, profile):
    # Read the original observed fields of the card, never its verdict/title.
    material = {}
    for observation in card["observations"]:
        cursor = material
        parts = observation["source_path"].removeprefix("$.").split(".")
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = observation["value"]
    return material_facets(material, profile)


def check(key, doc, profile, card=None):
    cfg, tags = profile.applicability, doc.get("tags") or []
    generic = card is None and cfg.generic_tag in tags
    if card is not None:
        conditions = historical_facets(card, profile)
    else:
        conditions = {}
        for name, facet in cfg.facets.items():
            prefix = cfg.tag_prefix + name + "="
            values = {v for tag in tags if tag.startswith(prefix)
                      if (v := normalize(tag[len(prefix):], facet))}
            if values:
                conditions[name] = sorted(values)
    matched, conflicts, unknown = [], [], []
    for name, values in conditions.items():
        actual = key.get("facets", {}).get(name)
        (unknown if not actual else matched if set(actual) & set(values) else conflicts).append(name)
    topic_match = any(cfg.facets[name].topic for name in matched)
    reason = ("applicability_conflict" if conflicts else "required_condition_unknown" if unknown and not generic else
              "comparable_topic_missing" if not topic_match else None)
    return {"state": "excluded" if reason else "applicable", "reason": reason,
            "conditions": conditions, "matched": matched, "conflicts": conflicts, "unknown": unknown,
            "generic": generic, "query_facets": key.get("facets", {})}
