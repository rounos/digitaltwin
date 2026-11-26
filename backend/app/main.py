import os
from dotenv import load_dotenv
from fastapi import FastAPI
from app.ai.llm_client import configured_provider
from fastapi.middleware.cors import CORSMiddleware
load_dotenv()

from app.api.routes import router as api_router  # noqa: E402

app = FastAPI(title="EchoMind Digital Twin API", version="0.1.0")

origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8501",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "ok",
        "service": "echomind-backend",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "llm_configured": configured_provider() is not None,
        "provider": os.getenv("LLM_PROVIDER", "openai").lower(),
        "model": {
            "openai": os.getenv("OPENAI_MODEL", "gpt-6-luna"),
            "gemini": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5"),
        }.get(os.getenv("LLM_PROVIDER", "openai").lower(), "unknown"),
    }


app.include_router(api_router, prefix="/api")