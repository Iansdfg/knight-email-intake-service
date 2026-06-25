from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings

settings = get_settings()
app = FastAPI(
    title="Commercial Auto Email Intake Service",
    root_path=settings.root_path,
)
app.include_router(router)
