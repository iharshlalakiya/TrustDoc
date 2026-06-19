from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import analyze, metadata, report, upload

load_dotenv()

app = FastAPI(
    title="TrustDoc API",
    description="Document forensics AI backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(analyze.router)
app.include_router(report.router)
app.include_router(metadata.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
