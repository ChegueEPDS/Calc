import asyncio
import azure.functions as func

from app.main import app as fastapi_app

# azure-functions' AsgiFunctionApp currently registers route "/{*route}".
# With the default host routePrefix ("api"), Azure ends up with "api//{*route}"
# which fails routing. Implement an explicit FunctionApp route without the
# leading slash to avoid the double-slash route template.
_asgi = func.AsgiMiddleware(fastapi_app)
_startup_done = False
_startup_lock = asyncio.Lock()

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


async def _ensure_startup() -> None:
    global _startup_done
    if _startup_done:
        return
    async with _startup_lock:
        if _startup_done:
            return
        ok = await _asgi.notify_startup()
        if not ok:
            raise RuntimeError("ASGI middleware startup failed.")
        _startup_done = True


@app.function_name(name="http_app_func")
@app.route(
    route="{*route}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
async def http_app_func(req: func.HttpRequest, context: func.Context):
    await _ensure_startup()
    return await _asgi.handle_async(req, context)
