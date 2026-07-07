from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import alerts, auth, dashboard, reports, residents, upload

app = FastAPI(
    title="COMP9900 Sleep Monitor API",
    description="Sleep monitoring dashboard backend API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(residents.router)
app.include_router(dashboard.router)
app.include_router(upload.router)
app.include_router(alerts.router)
app.include_router(reports.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "comp9900-backend"}
