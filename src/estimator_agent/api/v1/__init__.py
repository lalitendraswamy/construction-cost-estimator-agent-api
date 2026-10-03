from fastapi import APIRouter

from estimator_agent.api.v1 import admin, chat, threads, voice

router = APIRouter()
router.include_router(chat.router)
router.include_router(threads.router)
router.include_router(voice.router)
router.include_router(admin.router)
