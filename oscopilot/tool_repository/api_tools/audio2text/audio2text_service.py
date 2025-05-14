from fastapi import APIRouter, UploadFile, HTTPException, File, Depends
from pydantic import BaseModel, Field
from typing import Optional
from .audio2text import Audio2TextTool
import tempfile
import os

api = APIRouter()

speech_decoder = Audio2TextTool()

class InputAudioPayload(BaseModel):
    audio_clip: UploadFile = File(...)

@api.post("/tools/audio2text", summary="Transcribes spoken audio into readable sentences.")
async def transcribe_audio(data: InputAudioPayload = Depends()):
    try:
        # Save incoming audio to a temporary location
        temp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(temp_dir, data.audio_clip.filename)
        with open(tmp_path, "wb") as tmp_file:
            tmp_file.write(await data.audio_clip.read())

        # Generate transcription from the saved file
        with open(tmp_path, "rb") as source_audio:
            output_text = speech_decoder.caption(audio_file=source_audio)

        os.remove(tmp_path)  # Remove the file after processing
        return {"text": output_text}
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
