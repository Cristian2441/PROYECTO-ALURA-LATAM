import logging
from typing import List, TypedDict, Dict
import time
import asyncio


from google.api_core.exceptions import GoogleAPIError, ResourceExhausted
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import (
    GEMINI_API_KEY,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)
from app.prompts import ERROR_MESSAGE, NO_CONTEXT_MESSAGE
from app.vectorStore import VectorStoreManager

logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 5
MAX_PREGUNTA_LENGTH = 500
SESSION_TTL_SECONDS = 3600 
CLEANUP_INTERVAL_SECONDS = 600

class SessionData(TypedDict):
    messages: List
    last_access: float

def _format_docs(docs: List[Document]) -> str:
    """Convierte una lista de documentos en texto para el contexto del prompt."""
    return "\n\n---\n\n".join(
        f"[Fuente: {doc.metadata.get('fuente', 'Desconocido')}]\n{doc.page_content}"
        for doc in docs
    )


class AgenteRAG:
    """
    Agente de IA con capacidades RAG para soporte técnico SEGA.

    Flujo de una consulta (LCEL):
    1. El usuario envía una pregunta
    2. El retriever busca los fragmentos más relevantes en FAISS
    3. Se construye el prompt con el contexto recuperado + historial
    4. Gemini genera la respuesta en español
    5. Se devuelve la respuesta con las fuentes utilizadas

    Nota de escalabilidad: el historial vive en memoria del proceso (Dict).
    Si el servicio corre con múltiples workers (Gunicorn/Uvicorn con --workers > 1)
    o múltiples instancias en OCI, cada proceso tendrá su propio historial
    desincronizado. Para ese escenario, reemplazar self._historiales por un
    backend compartido (Redis) — ver notas al final del archivo.
    """

    def __init__(self, vector_store_manager: VectorStoreManager):
        self._vsm = vector_store_manager
        self._llm: ChatGoogleGenerativeAI | None = None
        self._prompt: ChatPromptTemplate | None = None
        self._historiales: Dict[str, SessionData] = {}
        self._initialized = False
        self._session_lock = asyncio.Lock()   # Protege lectura/escritura de historiales
        self._cleanup_lock = asyncio.Lock()   # Protege el ciclo de limpieza en background
        self._cleanup_task: asyncio.Task | None = None

    # ─────────────────────────────────────────────
    # Inicialización del agente
    # ─────────────────────────────────────────────
    async def initialize(self) -> None:
        """Construye los componentes base de la cadena RAG con LCEL."""
        logger.info(f"Inicializando agente RAG con modelo {LLM_MODEL}...")

 
        self._llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=LLM_TEMPERATURE,
            max_output_tokens=LLM_MAX_TOKENS,
        )
        self._prompt = ChatPromptTemplate.from_messages([
            (
                "system",
        """## Tu personalidad y forma de responder:

            Eres un agente de soporte amigable, cercano y profesional. Tu misión es ayudar
            a los usuarios con temas relacionados a SEGA: cuentas, juegos, problemas técnicos,
            etc. Siempre mantienes un tono cálido y natural, nunca frío ni robótico.

            ## Reglas que DEBES seguir:

            1. **Si el usuario saluda o se presenta** (como "hola", "buenas",
            etc.), responde de forma cálida y natural usando su nombre si lo menciona.
            Salúdalo de vuelta y con entusiasmo pregúntale en qué puedes ayudarle hoy
            en temas de SEGA. No necesitas documentos para esto.

            2. **Si el mensaje no es un saludo pero tampoco es una pregunta técnica de SEGA**,
            responde con amabilidad y redirige la conversación suavemente hacia los temas
            de soporte SEGA. Por ejemplo: "¡Interesante! Aunque mi especialidad es el
            soporte de SEGA, estaré encantado de ayudarte con cualquier duda sobre tus
            juegos, cuenta o consolas. ¿Tienes alguna pregunta al respecto?"

            3. **Para preguntas técnicas de SEGA**, usa ÚNICAMENTE la información del
            contexto proporcionado. No inventes respuestas ni uses conocimiento externo.

            4. **Si el contexto no tiene información relevante para una pregunta técnica**,
            díselo con amabilidad: "Hmm, no encontré información exacta sobre eso en mi
            base de conocimiento. Lo mejor sería contactar directamente al equipo de
            soporte oficial de SEGA, ellos podrán ayudarte mejor con este caso."

            5. **Responde siempre en español**, de forma clara y con un tono amigable.

            6. **No menciones que eres una IA** ni que estás "consultando documentos".
            Responde de manera natural como un agente de soporte humano.

            7. **Sin markdown excesivo.** Usa texto plano y listas numeradas simples
            cuando haya pasos. Nada de asteriscos, negritas ni sub-viñetas.
            
            ## Contexto de los documentos:
            {context}""",
            ),
            MessagesPlaceholder(variable_name="historial"),
            ("human", "{pregunta}"),
        ])
        self._initialized = True
        self._start_background_cleanup()
        logger.info("Agente RAG inicializado correctamente")

    async def shutdown(self) -> None:
        """
        Detiene ordenadamente la tarea de limpieza en background.
        Llamar desde el evento 'shutdown' de FastAPI.
        """
        if self._cleanup_task is not None and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Tarea de limpieza de sesiones cancelada correctamente")

    # ─────────────────────────────────────────────
    # Persistencia de Historial
    # ─────────────────────────────────────────────

    async def _get_session_history(self, session_id: str) -> List:
        """Obtiene y limita el historial específico de una sesión."""
        async with self._session_lock:
            if session_id not in self._historiales:
                self._historiales[session_id] = {"messages": [], "last_access": time.time()}
                
            self._historiales[session_id]["last_access"] = time.time()
            return list(self._historiales[session_id]["messages"][-MAX_HISTORY_TURNS * 2:])

    async def _save_session_historial(self, session_id: str, pregunta: str, respuesta: str) -> None:
        """Guarda la interacción en la sesión y recorta el exceso de memoria de forma segura."""
        async with self._session_lock:
            if session_id not in self._historiales:
                self._historiales[session_id] = {"messages": [], "last_access": time.time()}

            session = self._historiales[session_id]
            session["messages"].append(HumanMessage(content=pregunta))
            session["messages"].append(AIMessage(content=respuesta))
            session["last_access"] = time.time()
            
            if len(session["messages"]) > MAX_HISTORY_TURNS * 2:
                session["messages"] = session["messages"][-MAX_HISTORY_TURNS * 2:]

    def _start_background_cleanup(self) -> None:
        """Lanza un demonio que limpia la RAM de forma asíncrona cada cierto intervalo."""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                try:
                    ahora = time.time()
                    async with self._session_lock:
                        expiradas = [
                            sid for sid, data in self._historiales.items()
                            if ahora - data["last_access"] > SESSION_TTL_SECONDS
                        ]
                        for sid in expiradas:
                            del self._historiales[sid]
                    if expiradas:
                        logger.info(f"Recolector de basura: {len(expiradas)} sesiones inactivas eliminadas de la RAM.")
                except Exception as e:
                    logger.error(f"Error en el ciclo de limpieza de sesiones: {e}", exc_info=True)

        self._cleanup_task = asyncio.create_task(cleanup_loop())


    # ─────────────────────────────────────────────
    # Método principal de chat
    # ─────────────────────────────────────────────
    async def chat(self, pregunta: str, session_id: str) -> dict:
        """
        Procesa de forma asíncrona una pregunta aislada por ID de sesión.
 
        Args:
            pregunta: La consulta del usuario.
            session_id: Identificador único del usuario o chat.
 
        Returns:
            dict con 'respuesta' (str) y 'fuentes' (list[str])
        """
        if not self._initialized or self._llm is None or self._prompt is None:
            raise RuntimeError(
                "El agente no está inicializado. Llama a initialize() primero."
            )

        if not pregunta.strip():
            return {"respuesta": "Por favor, escribe tu pregunta.", "fuentes": []}
        
        if len(pregunta) > MAX_PREGUNTA_LENGTH:
            return {
                "respuesta": f"Tu pregunta es muy larga (máximo {MAX_PREGUNTA_LENGTH} caracteres). Intenta ser más breve.",
                "fuentes": []
             }

        try:
            logger.info(f"Procesando pregunta: {pregunta[:50]}...")

            retriever = self._vsm.get_retriever()
            # FAISS es CPU-bound: lo corremos en un thread para no bloquear
            # el event loop cuando haya múltiples usuarios simultáneos.
            docs = await asyncio.to_thread(retriever.invoke, pregunta)

            if not docs:
                # No hay documentos: igual llamamos al LLM para que maneje saludos
                # y preguntas fuera de tema de forma natural.
                contexto = "No hay información relevante en la base de conocimiento para este mensaje."
            else:
                contexto = _format_docs(docs)

            historial_usuario = await self._get_session_history(session_id)

            cadena = self._prompt | self._llm | StrOutputParser()

            respuesta = await cadena.ainvoke({
                "context": contexto,
                "historial": historial_usuario,
                "pregunta": pregunta,
            })

            await self._save_session_historial(session_id, pregunta, respuesta)

            fuentes = list(dict.fromkeys(
                doc.metadata.get("fuente", "Documento desconocido")
                for doc in docs
            ))

            return {"respuesta": respuesta, "fuentes": fuentes}

        except ResourceExhausted as e:
            logger.error(f"Cuota de la API de Gemini excedida: {e}")
            return {"respuesta": "Se alcanzó el límite de uso del servicio. Intenta en unos minutos.", "fuentes": []}
        except GoogleAPIError as e:
            logger.error(f"Error de la API de Gemini: {e}")
            return {"respuesta": ERROR_MESSAGE, "fuentes": []}
        except Exception as e:
            logger.error(f"Error inesperado al procesar pregunta: {e}", exc_info=True)
            return {"respuesta": ERROR_MESSAGE, "fuentes": []}

    # ─────────────────────────────────────────────
    # Limpiar historial de conversación
    # ─────────────────────────────────────────────
    async def reset_historial(self, session_id: str) -> None:
        """Borra explícitamente una sesión de memoria usando exclusión mutua."""
        async with self._session_lock:
            if session_id in self._historiales:
                del self._historiales[session_id]
                logger.info(f"Historial de la sesión {session_id} reiniciado")

    # ─────────────────────────────────────────────
    # Estado del agente
    # ─────────────────────────────────────────────
    @property
    def is_ready(self) -> bool:
        """Indica si el agente está listo para recibir preguntas."""
        return self._initialized and self._llm is not None
