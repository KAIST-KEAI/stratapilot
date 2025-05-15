from openai import OpenAI

class SpeechToTextEngine:
    def __init__(self) -> None:
        self._agent = OpenAI()

    def transcribe_audio(self, media_stream):
        # Use Whisper model to convert spoken audio into textual output
        result = self._agent.audio.transcriptions.create(
            model="whisper-1",
            file=media_stream
        )
        return result.texts
