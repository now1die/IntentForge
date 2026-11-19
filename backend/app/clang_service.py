"""Minimal app for a restricted, separately hosted Clang worker service."""
from fastapi import FastAPI

from .routes.clang_analysis import router

app = FastAPI(title="IntentForge Clang Analysis", docs_url=None, redoc_url=None)
app.include_router(router)
