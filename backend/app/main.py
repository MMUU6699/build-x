from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio

from app.core.config import get_settings
from app.infrastructure.storage.postgres import initialize as init_postgres
from app.infrastructure.storage.postgres import shutdown as shutdown_postgres
from app.interfaces.dependencies import get_agent_service
from app.interfaces.api.routes import router
from app.interfaces.api.openai_routes import router as openai_router
from app.infrastructure.logging import setup_logging
from app.interfaces.errors.exception_handlers import register_exception_handlers

# Initialize logging system
setup_logging()
logger = logging.getLogger(__name__)

# Load configuration
settings = get_settings()


# Create lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code executed on startup
    logger.info("Application startup - Build X AI Agent initializing")

    # Initialize PostgreSQL (SQLAlchemy engine + tables on dev)
    await init_postgres()
    logger.info("Successfully initialized PostgreSQL")

    try:
        yield
    finally:
        # Code executed on shutdown
        logger.info("Application shutdown - Build X AI Agent terminating")
        # Disconnect from PostgreSQL
        await shutdown_postgres()

        logger.info("Cleaning up AgentService instance")
        try:
            await asyncio.wait_for(get_agent_service().shutdown(), timeout=30.0)
            logger.info("AgentService shutdown completed successfully")
        except asyncio.TimeoutError:
            logger.warning("AgentService shutdown timed out after 30 seconds")
        except Exception as e:
            logger.error(f"Error during AgentService cleanup: {str(e)}")

app = FastAPI(title="Build X AI Agent", lifespan=lifespan)

allowed_origins = [url.strip() for url in (settings.frontend_url or "").split(",") if url.strip()]
if not allowed_origins:
    allowed_origins = ["http://localhost:5173"]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Register routes
app.include_router(router, prefix="/api/v1")
# OpenAI-compatible proxy (used by OpenClaw containers for LLM requests)
app.include_router(openai_router)
