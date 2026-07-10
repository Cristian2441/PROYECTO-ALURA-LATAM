import logging
import json
from typing import List

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import (
    GEMINI_API_KEY,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    HISTORY_FILE_PATH,
)
from app.prompts import ERROR_MESSAGE
from app.vectorStore import VectorStoreManager

logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 5

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
    4. Gemini 1.5 Pro genera la respuesta en español
    5. Se devuelve la respuesta con las fuentes utilizadas
    """

    def __init__(self, vector_store_manager: VectorStoreManager):
        self._vsm = vector_store_manager
        self._llm: ChatGoogleGenerativeAI | None = None
        self._chain = None
        self._historial: List = []  
        self._initialized = False

    # ─────────────────────────────────────────────
    # Inicialización del agente
    # ─────────────────────────────────────────────
    def initialize(self) -> None:
        """Construye la cadena RAG con LCEL (LangChain 1.x)."""
        logger.info(" Inicializando agente RAG con Gemini 1.5 Pro...")

        self._llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=LLM_TEMPERATURE,
            max_output_tokens=LLM_MAX_TOKENS,
        )
        self._prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """Eres un asistente virtual especializado en soporte técnico de SEGA.
    Tu función es ayudar a los usuarios respondiendo sus preguntas basándote ÚNICAMENTE 
    en la documentación oficial de SEGA que tienes disponible.

    ## Reglas que DEBES seguir:

    1. **Solo usa la información del contexto proporcionado.** No inventes respuestas 
    ni uses conocimiento externo.

    2. **Si la información no está en los documentos**, responde:
    "Lo siento, no encontré información sobre eso en la documentación de soporte 
    de SEGA. Te recomiendo contactar directamente al equipo de soporte oficial."

    3. **Responde siempre en español**, de forma clara, amable y profesional.

    4. **Sé conciso pero completo.** Si hay pasos a seguir, enuméralos claramente.

    5. **No menciones que eres una IA** ni que estás "consultando documentos". 
    Responde de manera natural como un agente de soporte.

## Contexto de los documentos:
{context}""",
            ),
            MessagesPlaceholder(variable_name="historial"),
            ("human", "{pregunta}"),
        ])

        self._load_historial()
        self._initialized = True
        logger.info("Agente RAG inicializado correctamente")

    # ─────────────────────────────────────────────
    # Persistencia de Historial
    # ─────────────────────────────────────────────
    def _save_historial(self) -> None:
        """Guarda el historial de conversación en un archivo JSON."""
        try:
            # Mantener solo los últimos MAX_HISTORY_TURNS
            historial_reducido = self._historial[-MAX_HISTORY_TURNS * 2:]
            self._historial = historial_reducido

            datos = []
            for msg in self._historial:
                tipo = "human" if isinstance(msg, HumanMessage) else "ai"
                datos.append({"type": tipo, "content": msg.content})

            with open(HISTORY_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando historial: {e}")

    def _load_historial(self) -> None:
        """Carga el historial de conversación desde un archivo JSON."""
        self._historial = []
        if not HISTORY_FILE_PATH.exists():
            return

        try:
            with open(HISTORY_FILE_PATH, "r", encoding="utf-8") as f:
                datos = json.load(f)
            
            for item in datos:
                if item["type"] == "human":
                    self._historial.append(HumanMessage(content=item["content"]))
                elif item["type"] == "ai":
                    self._historial.append(AIMessage(content=item["content"]))
            logger.info(f"Historial cargado: {len(self._historial)} mensajes")
        except Exception as e:
            logger.error(f"Error cargando historial: {e}")

    # ─────────────────────────────────────────────
    # Método principal de chat
    # ─────────────────────────────────────────────
    def chat(self, pregunta: str) -> dict:
        """
        Procesa una pregunta del usuario y devuelve la respuesta del agente.

        Args:
            pregunta: La pregunta del usuario en lenguaje natural

        Returns:
            dict con 'respuesta' (str) y 'fuentes' (list[str])
        """
        if not self._initialized or self._llm is None:
            raise RuntimeError(
                "El agente no está inicializado. Llama a initialize() primero."
            )

        if not pregunta.strip():
            return {"respuesta": "Por favor, escribe tu pregunta.", "fuentes": []}

        try:
            logger.info(f"💬 Procesando pregunta: {pregunta[:80]}...")

            retriever = self._vsm.get_retriever()
            docs = retriever.invoke(pregunta)
            contexto = _format_docs(docs)

            cadena = self._prompt | self._llm | StrOutputParser()

            respuesta = cadena.invoke({
                "context": contexto,
                "historial": self._historial[-MAX_HISTORY_TURNS * 2:],
                "pregunta": pregunta,
            })

            self._historial.append(HumanMessage(content=pregunta))
            self._historial.append(AIMessage(content=respuesta))
            self._save_historial()

            fuentes = list({
                doc.metadata.get("fuente", "Documento desconocido")
                for doc in docs
            })

            logger.info(f"Respuesta generada — Fuentes: {fuentes}")
            return {"respuesta": respuesta, "fuentes": fuentes}

        except Exception as e:
            logger.error(f"Error al procesar pregunta: {e}", exc_info=True)
            return {"respuesta": ERROR_MESSAGE, "fuentes": []}

    # ─────────────────────────────────────────────
    # Limpiar historial de conversación
    # ─────────────────────────────────────────────
    def reset_historial(self) -> None:
        """Limpia el historial de conversación en memoria y en disco."""
        self._historial.clear()
        self._save_historial()
        logger.info("Historial de conversación reiniciado")

    # ─────────────────────────────────────────────
    # Estado del agente
    # ─────────────────────────────────────────────
    @property
    def is_ready(self) -> bool:
        """Indica si el agente está listo para recibir preguntas."""
        return self._initialized and self._llm is not None
