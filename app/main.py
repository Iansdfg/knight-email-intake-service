from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.utils.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(
    title="Knight Email Intake Service",
    root_path=settings.root_path,
)
app.include_router(router)
