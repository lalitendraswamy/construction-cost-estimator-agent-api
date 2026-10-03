from __future__ import annotations

from fastapi import APIRouter, UploadFile

from estimator_agent.core.exceptions import NotConfiguredError

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/transcribe")
async def transcribe(audio: UploadFile) -> dict[str, str]:
    """Server-side STT. v1 uses the browser's Web Speech API, so this is a seam for an
    Indic STT provider (better Telugu accuracy). See agent/tools/language.py."""
    raise NotConfiguredError("Server-side transcription is not enabled in v1")
