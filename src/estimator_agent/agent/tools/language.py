"""detect_language, speech_to_text, text_to_speech.

v1 voice runs in the browser (Web Speech API, te-IN / hi-IN / en-IN), so STT/TTS here
are seams for a later Indic speech API (e.g. Sarvam, Bhashini, Google STT).
"""

from __future__ import annotations

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from estimator_agent.core.exceptions import NotConfiguredError
from estimator_agent.domain import Language
from estimator_agent.services.language import detect_script_language


class DetectLanguageInput(BaseModel):
    text: str = Field(description="User message")


@tool("detect_language", args_schema=DetectLanguageInput)
def detect_language(text: str) -> str | None:
    """Detect en/te/hi from the Unicode script. Returns null for Latin-script text."""
    lang = detect_script_language(text)
    return lang.value if lang else None


class SpeechToTextInput(BaseModel):
    audio_b64: str
    language: Language


@tool("speech_to_text", args_schema=SpeechToTextInput)
async def speech_to_text(audio_b64: str, language: Language) -> str:
    """Transcribe audio to text."""
    # TODO(phase-5+): call an Indic STT provider here.
    raise NotConfiguredError("Server-side STT not configured; the browser transcribes in v1.")


class TextToSpeechInput(BaseModel):
    text: str
    language: Language


@tool("text_to_speech", args_schema=TextToSpeechInput)
async def text_to_speech(text: str, language: Language) -> str | None:
    """Synthesize speech; returns a URL to the stored audio, or null if TTS is client-side."""
    # TODO(phase-5+): synthesize, upload to object storage, return a signed URL.
    return None
