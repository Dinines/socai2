"""Explicit local publication or read-only serving; no background execution."""
import argparse
import json
import sys

from pydantic import ValidationError

from .config import Config
from .store import LedgerError, Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve")
    serve.add_argument("--config", required=True)
    serve.add_argument("--upstream-config", help="Explicit single-environment read proxy profile")
    serve.add_argument("--viewer-config", help="Explicit read-viewer polling and pagination profile")
    publish = commands.add_parser("publish")
    publish.add_argument("--config", required=True)
    publish.add_argument("--document", required=True)
    publish.add_argument("--expected-revision", required=True, type=int)
    args = parser.parse_args()
    try:
        config = Config.load(args.config)
        if args.command == "publish":
            ledger = Store(config).publish(args.document, args.expected_revision)
            print(json.dumps({"batch_id": ledger.document.batch.id, "revision": ledger.revision,
                "execution_state": ledger.document.batch.execution_state}))
        else:
            import uvicorn

            from .api import create_app
            from .proxy import UpstreamConfig
            from .viewer import ViewerConfig
            upstream = UpstreamConfig.load(args.upstream_config) if args.upstream_config else None
            viewer = ViewerConfig.load(args.viewer_config) if args.viewer_config else None
            uvicorn.run(create_app(config, upstream, viewer=viewer), host=config.host, port=config.port)
        return 0
    except LedgerError as exc:
        print(json.dumps({"error": exc.code}), file=sys.stderr)
        return 1
    except (OSError, ValueError, ValidationError):
        print(json.dumps({"error": "invalid_test_service_configuration"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
