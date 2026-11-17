"""Object matching policy for candidate reads only; never rewrites source objects."""
import json
import os
import re
from pathlib import Path

from .exploration_contracts import ExplorationObject

TYPES = {"host", "user", "ip", "domain", "url", "hash"}
HASH_LENGTHS = {"MD5": 32, "SHA1": 40, "SHA256": 64, "SHA512": 128}


def window_hours():
    path = Path(os.environ.get("SOCAI2_EXPLORATION_CONFIG_FILE", Path(__file__).with_name("exploration-query.json")))
    value = json.loads(path.read_text())["default_window_hours"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= 8760:
        raise ValueError("invalid_exploration_window_configuration")
    return value


def matching_value(obj):
    if obj["object_type"] not in TYPES:
        return None, None, "unsupported_object_type"
    value = obj["normalized_value"]
    if obj["object_type"] != "hash":
        return value, None, None
    algorithm = (obj.get("attributes") or {}).get("algorithm")
    algorithm = algorithm.upper().replace("-", "").replace("_", "") if isinstance(algorithm, str) else None
    if algorithm not in HASH_LENGTHS or not re.fullmatch(rf"[0-9a-fA-F]{{{HASH_LENGTHS[algorithm]}}}", value):
        return None, None, "hash_algorithm_or_value_invalid"
    return value.lower(), algorithm, None


def object_view(obj, algorithm):
    return ExplorationObject(**{key: obj[key] for key in ExplorationObject.model_fields if key != "algorithm"},
        algorithm=algorithm)
