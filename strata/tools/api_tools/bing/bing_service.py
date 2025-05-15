from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from .bing_api_v2 import SmartWebSearchAgent
from .image_search_api import VisualSearchService
import tiktoken
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env', override=True)

# Load API credential for external services
BING_KEY = os.getenv("BING_SUBSCRIPTION_KEY")

# Token size checker for adaptive model use
def estimate_token_count(text: str) -> int:
    """Estimate token usage in input string."""
    tokenizer = tiktoken.encoding_for_model("gpt-4-1106-preview")
    return len(tokenizer.encode(text))

router = APIRouter()

web_explorer = SmartWebSearchAgent()
image_engine = VisualSearchService(BING_KEY)

# Request schemas
class SearchInput(BaseModel):
    query: str
    top_k: Optional[int] = Field(None)

class PageDetailRequest(BaseModel):
    url: str
    query: Optional[str] = Field(None)

@router.get("/tools/bing/image_lookup", summary="Fetch image assets using Bing. Returns list of image metadata including preview thumbnails and source URLs.")
async def fetch_images(data: SearchInput):
    try:
        if data.top_k is None:
            data.top_k = 10
        results = image_engine.search_image(data.query, data.top_k)
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err))
    return results

@router.get("/tools/bing/query_web", summary="Run a simplified Bing keyword search. Returns top content excerpts. Avoid complex query operators (e.g., 'site:').")
async def basic_web_search(data: SearchInput):
    try:
        if data.top_k is None:
            data.top_k = 5
        results = web_explorer.query_web(data.query, data.top_k)
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err))
    return results

@router.get("/tools/bing/extract_page", summary="Scrapes and condenses relevant content from a URL. If page is too long, it either summarizes or filters content via query relevance.")
async def get_page_details(payload: PageDetailRequest):
    output = {"page_content": ""}
    try:
        raw_content = web_explorer.fetch_site_content(payload.url)
        token_estimate = estimate_token_count(raw_content)

        if token_estimate <= 4096:
            output["page_content"] = raw_content
        elif payload.query is None:
            output["page_content"] = web_explorer.generate_summary(raw_content)
        else:
            output["page_content"] = web_explorer.extract_relevant_passages(raw_content, payload.query)
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err))
    return output
