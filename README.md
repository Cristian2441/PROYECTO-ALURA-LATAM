#  SEGA Assistant

Asistente de soporte técnico conversacional para SEGA, desarrollado como proyecto del programa **Oracle Next Education + Alura Latam**. Permite a los usuarios hacer preguntas en lenguaje natural sobre cuentas, problemas técnicos y preparación para soporte, obteniendo respuestas basadas exclusivamente en la documentación oficial de SEGA.

El sistema está compuesto por dos partes independientes que trabajan juntas:

- **BackEnd** — API de inteligencia artificial con un pipeline RAG (Python + FastAPI + Gemini + FAISS)
- **FrontEnd** — Interfaz de chat web (Angular 22)
  
🔗 https://sega-front.onrender.com/


Nota: al usar el plan gratuito de Render, el servicio puede tardar 20-30 segundos
en responder la primera vez si estuvo inactivo (cold start). Las siguientes
peticiones son instantáneas.



Podés probar directamente:


Chat: https://sega-front.onrender.com/
Documentación interactiva (Swagger): https://sega-front.onrender.com/docs
Estado del servicio: https://sega-front.onrender.com/health
---

##  Tabla de Contenidos

- [Arquitectura General](#arquitectura-general)
- [Stack Tecnológico](#stack-tecnológico)
- [Estructura del Repositorio](#estructura-del-repositorio)
- [Requisitos Previos](#requisitos-previos)
- [Puesta en Marcha](#puesta-en-marcha)
- [Cómo Funciona el Pipeline RAG](#cómo-funciona-el-pipeline-rag)
- [Flujo Completo de una Conversación](#flujo-completo-de-una-conversación)
- [Documentación Detallada](#documentación-detallada)

---

## Arquitectura General

```
┌─────────────────────────────────────────────────────────┐
│                        FRONTEND                         │
│           Angular 22  ·  http://localhost:4200          │
│                                                         │
│   ┌─────────────┐        ┌───────────────────────────┐  │
│   │ Welcome View│        │       Chat View           │  │
│   │  SEGA logo  │ ─────► │  Burbujas + Typing dots   │  │
│   │  subtítulo  │        │  Botón nuevo chat (+)     │  │
│   └─────────────┘        └───────────────────────────┘  │
│                ChatService (HTTP + session_id)           │
└───────────────────────┬─────────────────────────────────┘
                        │  POST /chat  (x-session-id)
                        │  POST /reset-chat
                        │  GET  /health
                        ▼
┌─────────────────────────────────────────────────────────┐
│                        BACKEND                          │
│           FastAPI  ·  http://localhost:8000             │
│                                                         │
│   ┌──────────┐    ┌──────────────┐    ┌─────────────┐  │
│   │ AgenteRAG│───►│VectorStore   │    │  Documentos │  │
│   │  (LCEL)  │    │Manager(FAISS)│◄───│  PDF SEGA   │  │
│   └────┬─────┘    └──────────────┘    └─────────────┘  │
│        │                                                │
│        ▼                                                │
│   Gemini 2.5 Flash  ·  gemini-embedding-001             │
└─────────────────────────────────────────────────────────┘
```

---

## Stack Tecnológico

### Backend

| Categoría | Tecnología |
|---|---|
| Framework API | FastAPI + Uvicorn |
| Lenguaje | Python 3.11+ |
| LLM | Google Gemini 2.5 Flash |
| Embeddings | `gemini-embedding-001` |
| Orquestación RAG | LangChain (LCEL) |
| Vector Store | FAISS (local, persistido en disco) |
| Lectura de PDFs | PyMuPDF (`fitz`) |
| Rate Limiting | SlowAPI |
| Validación | Pydantic v2 |

### Frontend

| Categoría | Tecnología |
|---|---|
| Framework | Angular 22 (Standalone Components) |
| Lenguaje | TypeScript 6 |
| Estilos | SCSS + Google Fonts (Inter) |
| Estado | Angular Signals |
| HTTP | `@angular/common/http` con Fetch API |
| Build tool | `@angular/build` (Vite internamente) |

---

## Estructura del Repositorio

```
/
├── BackEnd/
│   ├── app/
│   │   ├── main.py             # API FastAPI — endpoints y middleware
│   │   ├── agente.py           # AgenteRAG — lógica de chat con historial
│   │   ├── vectorStore.py      # VectorStoreManager — FAISS + embeddings
│   │   ├── document_loader.py  # DocumentLoader — parseo de PDFs
│   │   ├── config.py           # Configuración global y variables de entorno
│   │   └── prompts.py          # System prompt y mensajes predefinidos
│   ├── Documentacion/          # PDFs de soporte técnico de SEGA
│   ├── faiss_index/            # Índice vectorial (auto-generado al arrancar)
│   ├── static/
│   │   ├── requirements.txt    # Dependencias Python
│   │   └── .env.example        # Plantilla de variables de entorno
│   ├── .env                    # Claves secretas (no subir al repo)
│   └── README.md               # Documentación detallada del backend
│
├── FrontEnd/
│   ├── src/
│   │   ├── app/
│   │   │   ├── app.component.ts    # Componente raíz — lógica del chat
│   │   │   ├── app.component.html  # Template — vistas bienvenida y chat
│   │   │   ├── app.component.scss  # Estilos de burbujas, input, animaciones
│   │   │   ├── app.config.ts       # Providers de la aplicación
│   │   │   └── chat.service.ts     # Servicio HTTP y gestión de session_id
│   │   ├── index.html              # HTML raíz
│   │   ├── main.ts                 # Bootstrap de Angular
│   │   └── styles.scss             # Estilos globales y gradiente de fondo
│   ├── public/                     # Assets estáticos (logos, favicon)
│   ├── package.json
│   └── README.md                   # Documentación detallada del frontend
│
└── README.md                       # Este archivo
```

---

## Requisitos Previos

| Herramienta | Versión mínima | Para qué |
|---|---|---|
| Python | 3.11 | Backend |
| Node.js | 20 | Frontend |
| npm | 11 | Frontend |
| API Key de Gemini | — | Backend — [obtener gratis](https://aistudio.google.com/app/apikey) |

---

## Puesta en Marcha

### 1 · Clonar el repositorio

```bash
git clone <url-del-repo>
cd <nombre-del-repo>
```

### 2 · Configurar y levantar el Backend

```bash
cd BackEnd

# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

# Instalar dependencias
pip install -r static/requirements.txt

# Crear el archivo de variables de entorno
cp static/.env.example .env
```

Edita `BackEnd/.env` y rellena los valores:

```env
# Obtén la tuya en: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=tu_clave_aqui

# Genera un token seguro con:
# python -c "import secrets; print(secrets.token_urlsafe(32))"
ADMIN_TOKEN=tu_token_aqui
```

Arranca el servidor:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> Al iniciar por primera vez, el backend procesará automáticamente los PDFs de `Documentacion/` y construirá el índice FAISS. Las siguientes veces lo cargará desde disco.

Verifica que esté activo en [http://localhost:8000/health](http://localhost:8000/health).

---

### 3 · Configurar y levantar el Frontend

Abre una nueva terminal:

```bash
cd FrontEnd

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm start
```

Abre el navegador en [http://localhost:4200](http://localhost:4200).

---

### Resumen de puertos

| Servicio | URL | Descripción |
|---|---|---|
| Frontend | http://localhost:4200 | Interfaz de chat |
| Backend API | http://localhost:8000 | API REST |
| Swagger UI | http://localhost:8000/docs | Documentación interactiva |
| ReDoc | http://localhost:8000/redoc | Documentación alternativa |

---

## Cómo Funciona el Pipeline RAG

RAG (Retrieval-Augmented Generation) combina búsqueda semántica con generación de texto. En lugar de que el modelo invente respuestas, primero recupera fragmentos relevantes de los documentos oficiales y luego genera la respuesta basándose exclusivamente en ese contexto.

```
PDFs de SEGA (Documentacion/)
         │
         ▼
  DocumentLoader            ← PyMuPDF extrae texto página por página
         │
         ▼
  Chunking                  ← fragmentos de 1200 chars, overlap 100
         │
         ▼
  Embeddings Gemini         ← cada chunk se convierte en un vector numérico
         │
         ▼
  Índice FAISS              ← guardado en disco en faiss_index/
         │
    [por cada /chat]
         │
         ▼
  Retriever (top-5)         ← busca los 5 fragmentos más similares a la pregunta
         │
         ▼
  Prompt = contexto + historial de sesión + pregunta del usuario
         │
         ▼
  Gemini 2.5 Flash          ← genera la respuesta en español
         │
         ▼
  Respuesta + Fuentes       ← devuelto al frontend
```

Si el retriever no encuentra fragmentos relevantes, el agente responde directamente con un mensaje estándar en lugar de inventar información.

---

## Flujo Completo de una Conversación

```
Usuario escribe en el input
        │
        ▼
Angular (onSendMessage)
  ├── Muestra burbuja del usuario
  ├── Activa indicador de escritura (tres puntos animados)
  └── ChatService.enviarPregunta()
            │
            │  POST /chat
            │  Body: { "pregunta": "..." }
            │  Header: x-session-id (UUID, si ya existe)
            │
            ▼
       FastAPI /chat
         ├── Valida longitud (max 500 chars)
         ├── Rate limit: 15 req/min por IP
         ├── Recupera historial de la sesión (en memoria)
         ├── AgenteRAG.chat()
         │       ├── Retriever → top-5 fragmentos FAISS
         │       ├── Construye prompt con contexto + historial
         │       └── Gemini 2.5 Flash genera respuesta
         └── Devuelve { respuesta, fuentes, session_id }
                    │
                    ▼
       ChatService guarda session_id
                    │
                    ▼
       Angular muestra burbuja del asistente
```

La sesión persiste en memoria del proceso durante **1 hora** de inactividad. El botón `+` del frontend limpia tanto el estado local como el historial del servidor (`POST /reset-chat`).

---

## Documentación Detallada

Cada parte del proyecto tiene su propio README con información exhaustiva:

- **[BackEnd/README.md](./BackEnd/README.md)** — endpoints, pipeline RAG, parámetros de configuración, gestión de sesiones y seguridad
- **[FrontEnd/README.md](./FrontEnd/README.md)** — arquitectura Angular, ChatService, estilos SCSS, animaciones y build de producción
