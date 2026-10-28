# Design

Keep `application:create_app` as the standalone entry. Add `/livez` for process liveness and `/api/v2/investigation/openapi.json` for the existing route contract; neither asserts database/model readiness. Do not mount the legacy main app or start its background tasks.

Use the currently inspected API image `sha256:5a1e1fd8cf08349438e7d1346a25c9599bff7937df5d22ea94426e77b33f2aa9` as the dependency base. Copy current Python sources into an isolated work directory. Start one independently named container on existing `socai2_default`, publishing only `127.0.0.1:18010`. Reuse core API environment and read-only CA/identity mounts; add only existing Agents model connection/key settings and role `aisoc-investigation`. Store the new environment file only on 21, mode0600; do not print values or modify current containers/credentials.

The caller reads its token from an environment variable, accepts one GET/POST and optional JSON file, and never retries a POST. Relative `/api/v2/investigation` links use the investigation base; `/api/v1` links use the core base. Disable redirects so credentials are not forwarded to another endpoint. The resident smoke check covers liveness, actual route schema and the existing unauthenticated rejection; it does not repeat model workflows or claim authenticated business HTTP acceptance.
