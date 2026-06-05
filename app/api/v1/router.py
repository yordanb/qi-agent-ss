from fastapi import APIRouter
from app.routers.ss import router as ss_router
from app.routers.auth import router as auth_router
from app.routers.esic import router as esic_router
from app.routers.upload import router as upload_router
from app.routers.manpower import router as manpower_router

api_router = APIRouter()
api_router.include_router(ss_router, prefix="")
api_router.include_router(auth_router, prefix="")
api_router.include_router(esic_router, prefix="")
api_router.include_router(upload_router, prefix="")
api_router.include_router(manpower_router, prefix="")
