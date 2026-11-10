"""Current-release job entry; selects the profile in the same frozen release."""
import json
import sys
from pathlib import Path

from production_processing import ProfileError, SetupError, main


def entry():
    release = Path(__file__).resolve().parents[2]
    profile = json.loads((release / "release.json").read_text())["processing"]["profile"]
    args = sys.argv[1:]
    if any(arg == "--profile" or arg.startswith("--profile=") for arg in args):
        raise SetupError("current_release_profile_cannot_be_overridden")
    args = ["--profile", profile, *args]
    sys.argv = [sys.argv[0], *args]
    return main()


if __name__ == "__main__":
    try:
        raise SystemExit(entry())
    except Exception as exc:  # noqa: BLE001 -- keep connection settings out of public errors
        print(json.dumps({"error": str(exc) if isinstance(exc, (SetupError, ProfileError)) else type(exc).__name__}))
        raise SystemExit(1) from None
