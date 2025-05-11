import os
import dotenv

from fastapi import FastAPI
from oscopilot.utils.server_config import ConfigManager
dotenv.load_dotenv(dotenv_path='.env', override=True)
app = FastAPI()

# Import your services
from oscopilot.tool_repository.api_tools.bing.bing_service import router as bing_router
from oscopilot.tool_repository.api_tools.audio2text.audio2text_service import router as audio2text_router
from oscopilot.tool_repository.api_tools.image_caption.image_caption_service import router as image_caption_router
from oscopilot.tool_repository.api_tools.wolfram_alpha.wolfram_alpha import router as wolfram_alpha_router

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log incoming requests and outgoing responses, including errors.
    """
    async def dispatch(self, request: Request, call_next):
        print(f"Incoming request: {request.method} {request.url}")
        try:
            response = await call_next(request)
        except Exception as exc:
            print(f"Request error: {exc}")
            raise exc from None
        else:
            print(f"Outgoing response: {response.status_code}")
        return response


# Register the logging middleware
app.add_middleware(LoggingMiddleware)

# Map service names to routers
services = {
    "bing": bing_router,            # Provides Bing search, image search, and web loading
    "audio2text": audio2text_router,
    "image_caption": image_caption_router,
    "wolfram_alpha": wolfram_alpha_router,
}

# List of services to include in this server instance
enabled_services = ["bing", "audio2text", "image_caption"]

# Dynamically include only the enabled service routers
for name in enabled_services:
    router = services.get(name)
    if router:
        app.include_router(router)


if __name__ == "__main__":
    # Start the Uvicorn ASGI server
    uvicorn.run(app, host="0.0.0.0", port=8079)
