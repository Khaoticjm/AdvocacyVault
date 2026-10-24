from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.modules.complaints.router import router as complaints_router
from app.modules.adjuster.router import router as adjuster_router
from app.modules.verifier.router import router as verifier_router

app = FastAPI(
    title="Advocacy Vault API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


app.include_router(complaints_router, prefix="/api/v1")
app.include_router(adjuster_router, prefix="/api/v1")
app.include_router(verifier_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
