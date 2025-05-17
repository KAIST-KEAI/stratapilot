import os
import dotenv

from fastapi import FastAPI
from strata.utils.server_config import ConfigManager as CfgMgr
dotenv.load_dotenv(dotenv_path=".env", override=True)

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Instantiate the API app
application = FastAPI()

# Plug-in imports
from strata.tool_repository.api_tools.bing.bing_service import router as mod_bing
from strata.tool_repository.api_tools.audio2text.audio2text_service import router as mod_audio
from strata.tool_repository.api_tools.image_caption.image_caption_service import router as mod_imgcap
from strata.tool_repository.api_tools.wolfram_alpha.wolfram_alpha import router as mod_math


class TrafficTracer(BaseHTTPMiddleware):
    """
    Captures inbound API activity and outbound replies, including fault cases.
    """
    async def dispatch(self, request: Request, call_next):
        print(f"[Trace] ➡️ {request.method} {request.url}")
        try:
            result = await call_next(request)
        except Exception as issue:
            print(f"[Error] ❌ {issue}")
            raise issue from None
        print(f"[Trace] ⬅️ Status {result.status_code}")
        return result


# Wire in middleware for tracing
application.add_middleware(TrafficTracer)

# Routing table for available plugins
plugin_routes = {
    "web_search": mod_bing,
    "speech_to_text": mod_audio,
    "caption_gen": mod_imgcap,
    "math_solver": mod_math,
}

# List of modules to activate
active_modules = ["web_search", "speech_to_text", "caption_gen"]

# Selectively register API endpoints
for plugin in active_modules:
    route = plugin_routes.get(plugin)
    if route:
        application.include_router(route)


if __name__ == "__main__":
    import uvicorn
    # Spin up the service
    uvicorn.run(application, host="0.0.0.0", port=8079)
