"""API v1 main router — aggregates all module routers.
Module routers already define their own prefix.
"""
from fastapi import APIRouter
from app.modules.auth.router import router as auth_router
from app.modules.ss.router import router as ss_router
from app.routers.esic import router as esic_router
from app.routers.upload import router as upload_router
from app.routers.manpower import router as manpower_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(ss_router)
api_router.include_router(esic_router)
api_router.include_router(upload_router)
api_router.include_router(manpower_router)
