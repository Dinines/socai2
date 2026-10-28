"""Current Alert/Incident/Case APIs, without legacy program gateway settings."""
from .alert_context_api import router as alert_router
from .case_analysis_api import router as case_router
from .case_links_api import router as links_router
from .incident_api import router as incident_router
from .execution_index import router as execution_router
from .query_api import create_app as create_query_app


def create_app():
    app = create_query_app()
    app.title = "Alert, incident and Case investigation"
    for router in (alert_router, incident_router, case_router, links_router, execution_router):
        app.include_router(router)

    @app.get("/livez", include_in_schema=False)
    async def live():
        return {"status": "alive", "service": "investigation-v2"}

    @app.get("/api/v2/investigation/openapi.json", include_in_schema=False)
    async def contract():
        return app.openapi()

    return app
