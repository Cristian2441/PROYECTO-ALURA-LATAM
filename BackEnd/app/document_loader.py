"""
document_loader.py
──────────────────
Primera etapa del pipeline RAG: carga y extracción de texto
desde los documentos PDF de soporte técnico de SEGA.

Usa PyMuPDF (fitz) para una extracción de texto precisa,
y devuelve objetos Document de LangChain listos para el siguiente
paso del pipeline (chunking → embeddings → vector store).
"""

import logging
from pathlib import Path
from typing import List

import fitz  # PyMuPDF
from langchain_core.documents import Document

from app.config import DOCS_DIR

logger = logging.getLogger(__name__)


class DocumentLoader:
    """
    Carga los archivos PDF de la carpeta Documentacion/ y los convierte
    en objetos Document de LangChain con metadatos enriquecidos.

    Pipeline RAG:
        [DocumentLoader] → Chunking → Embeddings → VectorStore → Retriever
    """

    def __init__(self, docs_dir: Path | str = DOCS_DIR):
        self.docs_dir = Path(docs_dir)

    # ─────────────────────────────────────────────
    # Carga de un solo PDF
    # ─────────────────────────────────────────────
    def _load_pdf(self, pdf_path: Path) -> Document | None:
        """
        Lee un archivo PDF página por página y lo convierte en un Document.

        Args:
            pdf_path: Ruta al archivo PDF.

        Returns:
            Document con el texto completo y metadatos, o None si falla.
        """
        try:
            doc = fitz.open(str(pdf_path))
            pages_text: List[str] = []

            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text")
                if text.strip():
                    pages_text.append(f"[Página {page_num}]\n{text.strip()}")

            doc.close()

            if not pages_text:
                logger.warning("⚠️  %s — no contiene texto extraíble", pdf_path.name)
                return None

            full_text = "\n\n".join(pages_text)

            return Document(
                page_content=full_text,
                metadata={
                    "fuente": pdf_path.name,
                    "ruta": str(pdf_path),
                    "num_paginas": len(pages_text),
                    "tipo": "soporte_tecnico_sega",
                },
            )

        except Exception as e:
            logger.error("❌ Error leyendo %s: %s", pdf_path.name, e)
            return None

    # ─────────────────────────────────────────────
    # Carga de todos los PDFs
    # ─────────────────────────────────────────────
    def load(self) -> List[Document]:
        """
        Carga todos los archivos PDF de la carpeta Documentacion/.

        Returns:
            Lista de Documents listos para el siguiente paso del pipeline.

        Raises:
            FileNotFoundError: Si la carpeta no existe o no hay PDFs.
        """
        if not self.docs_dir.exists():
            raise FileNotFoundError(
                f"❌ La carpeta de documentos no existe: {self.docs_dir}"
            )

        pdf_files = sorted(self.docs_dir.glob("*.pdf"))

        if not pdf_files:
            raise FileNotFoundError(
                f"❌ No se encontraron archivos PDF en: {self.docs_dir}"
            )

        logger.info("📂 Carpeta de documentos: %s", self.docs_dir)
        logger.info("📄 Archivos encontrados: %d PDFs", len(pdf_files))

        documents: List[Document] = []

        for pdf_path in pdf_files:
            logger.info("   🔍 Procesando: %s", pdf_path.name)
            doc = self._load_pdf(pdf_path)
            if doc is not None:
                documents.append(doc)
                logger.info(
                    "   ✅ %s — %d páginas cargadas",
                    pdf_path.name,
                    doc.metadata["num_paginas"],
                )

        if not documents:
            raise ValueError(
                "❌ No se pudo extraer texto de ningún documento PDF."
            )

        logger.info(
            "✅ Carga completada: %d/%d documentos listos para el pipeline",
            len(documents),
            len(pdf_files),
        )
        return documents
