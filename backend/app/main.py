import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, budgets, categories, chat, dashboard, transactions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("askyourwallet")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle hook."""
    backend = "sqlite" if settings.DATABASE_URL.startswith("sqlite") else "postgresql"
    logger.info("%s API starting (database=%s)", settings.APP_NAME, backend)
    if settings.groq_enabled:
        logger.info("Groq assistant enabled (model=%s)", settings.GROQ_MODEL)
    else:
        logger.warning(
            "GROQ_API_KEY is not set -- the chat assistant and LLM categorization "
            "fallback are disabled. Everything else works."
        )
    yield


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description=(
        "AI-powered personal finance assistant. All AI answers are grounded in the "
        "signed-in user's own transaction data via backend tool calls."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS -- the Vite dev server plus whatever FRONTEND_URL is deployed to.
# allow_origin_regex covers the arbitrary localhost port Vite picks when 5173 is busy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(budgets.router)
app.include_router(dashboard.router)
app.include_router(chat.router)


@app.get("/health", tags=["meta"])
async def health():
    """Liveness probe. Also reports whether the AI assistant is configured."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "ai_enabled": settings.groq_enabled,
    }
