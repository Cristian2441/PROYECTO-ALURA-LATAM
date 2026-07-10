import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agente import AgenteRAG
from app.prompts import WELCOME_MESSAGE
from app.vectorStore import VectorStoreManager

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Instancias globales
# ─────────────────────────────────────────────
vsm = VectorStoreManager()
agente = AgenteRAG(vsm)


# ─────────────────────────────────────────────
# Lifespan: startup y shutdown
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa el vector store y el agente al arrancar el servidor."""
    logger.info("Iniciando servidor del Agente RAG SEGA...")
    try:
        vsm.initialize()   
        agente.initialize()  
        logger.info("Servicio listo para recibir consultas")
    except Exception as e:
        logger.critical(f"Error crítico durante el arranque: {e}", exc_info=True)
        raise
    yield
    logger.info("Servidor detenido correctamente")


# ─────────────────────────────────────────────
# Aplicación FastAPI
# ─────────────────────────────────────────────
app = FastAPI(
    title="Agente RAG - Soporte Técnico SEGA",
    description=(
        "API de inteligencia artificial que responde preguntas en lenguaje natural "
        "sobre la documentación de soporte técnico de SEGA usando RAG (Gemini + FAISS)."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Modelos de datos (Pydantic)
# ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    pregunta: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Pregunta del usuario en lenguaje natural",
        examples=["¿Cómo puedo recuperar mi contraseña de SEGA?"],
    )


class ChatResponse(BaseModel):
    respuesta: str = Field(description="Respuesta generada por el agente")
    fuentes: list[str] = Field(description="Documentos utilizados para responder")


class HealthResponse(BaseModel):
    estado: str
    vector_store_listo: bool
    agente_listo: bool
    mensaje: str


class ResetResponse(BaseModel):
    exito: bool
    mensaje: str


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Estado del servicio",
    tags=["Sistema"],
)
async def health_check():
    """Verifica que el vector store y el agente estén operativos."""
    return HealthResponse(
        estado="activo" if agente.is_ready else "iniciando",
        vector_store_listo=vsm.is_ready,
        agente_listo=agente.is_ready,
        mensaje=(
            "Servicio completamente operativo"
            if agente.is_ready
            else "El servicio está iniciando, espera un momento"
        ),
    )


@app.post(
    "/chat",
    response_model=ChatResponse,
    summary="Enviar pregunta al agente",
    tags=["Chat"],
)
async def chat(request: ChatRequest):
    """
    Envía una pregunta al agente RAG y recibe una respuesta en español
    basada en la documentación de soporte técnico de SEGA.
    """
    if not agente.is_ready:
        raise HTTPException(
            status_code=503,
            detail="El agente todavía está inicializando. Intenta en unos segundos.",
        )

    resultado = agente.chat(request.pregunta)
    return ChatResponse(**resultado)


@app.post(
    "/reset-chat",
    response_model=ResetResponse,
    summary="Limpiar historial de conversación",
    tags=["Chat"],
)
async def reset_chat():
    """Reinicia el historial de conversación del agente (nueva sesión)."""
    agente.reset_historial()
    return ResetResponse(
        exito=True,
        mensaje="Historial de conversación limpiado correctamente",
    )


@app.post(
    "/reset-index",
    response_model=ResetResponse,
    summary="Regenerar índice FAISS",
    tags=["Sistema"],
)
async def reset_index():
    """
    Regenera el índice FAISS leyendo nuevamente los PDFs de la carpeta
    Documentacion/. Útil si se actualizan los documentos.
    """
    try:
        logger.info("Regenerando índice FAISS por solicitud del usuario...")
        vsm.build_index()
        agente.reset_historial()
        return ResetResponse(
            exito=True,
            mensaje="Índice regenerado correctamente. El agente está listo.",
        )
    except Exception as e:
        logger.error(f"Error regenerando índice: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al regenerar el índice: {str(e)}",
        )


@app.get(
    "/",
    summary="Bienvenida",
    tags=["Sistema"],
)
async def root():
    """Endpoint raíz con mensaje de bienvenida."""
    return {
        "servicio": "Agente RAG - Soporte Técnico SEGA",
        "version": "1.0.0",
        "mensaje": WELCOME_MESSAGE,
        "documentacion": "/docs",
        "estado": "/health",
    }


# ─────────────────────────────────────────────
# Punto de entrada directo
# ─────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
