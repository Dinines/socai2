- [x] Inspect current runtime image, networks, mounts, model configuration presence and candidate port.
- [x] Add liveness/schema entry, caller and explicit deployment files.
- [x] Perform minimal local entry/caller verification and prepare a source-only upload bundle (475 files; no runtime environment).
- [x] Obtain authorization and start only the new loopback investigation container (`socai2-investigation-api`, image2fde05d5).
- [x] Record HTTP entry checks and caller limitations; leave current business containers intact (18 OpenAPI paths, liveness200, unauthenticated401, core/Agents ID and start time unchanged).

OpenSpec CLI unavailable; no strict CLI validation or archive is claimed. No deployment is authorized by this task file itself.

Evidence: `docs/investigation/resident-api-20261028.md`, `docs/operations/investigation-api-entry-local-20261028.json` and `docs/operations/investigation-api-resident-20261028.json`. Normal-user authenticated resident business HTTP remains unverified without an operator-supplied existing token; no users/permissions were created for the check.
