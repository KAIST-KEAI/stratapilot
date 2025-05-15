from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import wolframalpha
import os
from dotenv import load_dotenv

# Load API credentials
load_dotenv(dotenv_path=".env", override=True)
_WOLFRAM_KEY = os.getenv("WOLFRAMALPHA_APP_ID")

router = APIRouter()

# Initialize external client
solver = wolframalpha.Client(_WOLFRAM_KEY)

# Input schema
class PromptInput(BaseModel):
    query: str

@router.post("/tools/compute_engine", summary="Execute a symbolic or numeric computation via WolframAlpha.")
async def compute_math_expression(payload: PromptInput):
    response = solver.query(payload.query)

    if response.get("@success") == "false":
        return {"result": "Unable to process the request."}

    try:
        first_result = next(response.results).text
    except Exception:
        return {"result": "No valid output returned."}

    return {"result": first_result}
