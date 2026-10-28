# Serve the verified investigation API

The current investigation functions work in temporary processes, while the resident core API has neither the new routes nor model configuration. Add a separate loopback investigation service, expose its actual OpenAPI contract, and provide a small HTTP caller that resolves investigation and core links to their corresponding API bases. Prepare and verify locally before requesting authorization to start the resident service.
