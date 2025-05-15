from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel, Field
from typing import Optional
from .gpt4v_caption import VisualInsightGenerator
import base64

router = APIRouter()

vision_tool = VisualInsightGenerator()

async def extract_caption_args(
    task_prompt: Optional[str] = Form("Can you interpret this image?"),
    remote_url: Optional[str] = Form(None),
    uploaded_img: Optional[UploadFile] = File(None)
):
    return {"task_prompt": task_prompt, "remote_url": remote_url, "uploaded_img": uploaded_img}

@router.post(
    "/tools/visual_inspector",
    summary="Use this utility for interpreting a visual file or URL using GPT-4 Vision. It accepts either a local image (uploaded) or a remote link, alongside a user-defined task prompt. The prompt should express the full context of the task to ensure accurate interpretation."
)
async def analyze_image(input_data: dict = Depends(extract_caption_args)):
    try:
        if input_data["task_prompt"] is None:
            input_data["task_prompt"] = "Can you interpret this image?"

        if input_data["remote_url"] is None and input_data["uploaded_img"] is None:
            return {"error": "No valid image input provided."}

        visual_reference = ""

        if input_data["remote_url"] and not input_data["uploaded_img"]:
            visual_reference = input_data["remote_url"]
        elif input_data["uploaded_img"]:
            encoded_img = base64.b64encode(await input_data["uploaded_img"].read()).decode("utf-8")
            visual_reference = f"data:image/jpeg;base64,{encoded_img}"

        result = vision_tool.describe_image(image_url=visual_reference, prompt=input_data["task_prompt"])

    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err))

    return {"caption": result}
