# 🎮 SEGA Assistant — Frontend

Interfaz de chat construida con **Angular 22** que permite a los usuarios interactuar con el agente RAG de soporte técnico de SEGA. La UI imita la experiencia de un asistente conversacional moderno, con dos vistas diferenciadas (bienvenida y chat), gestión de sesión automática y manejo de errores integrado.

---

## Tabla de Contenidos

- [Vista General](#vista-general)
- [Tecnologías](#tecnologías)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Requisitos Previos](#requisitos-previos)
- [Instalación](#instalación)
- [Ejecución](#ejecución)
- [Arquitectura de la App](#arquitectura-de-la-app)
- [ChatService](#chatservice)
- [Estilos y Diseño](#estilos-y-diseño)
- [Build de Producción](#build-de-producción)
- [Conexión con el Backend](#conexión-con-el-backend)

---

## Vista General

La aplicación tiene dos estados visuales principales:

**Vista de bienvenida** — se muestra al iniciar o al crear un nuevo chat. Presenta el logo de SEGA y un mensaje introductorio.

**Vista de chat** — se activa al enviar el primer mensaje. Muestra el historial de conversación con burbujas diferenciadas por rol (usuario / asistente), un indicador de escritura animado mientras el agente responde, y un botón para iniciar una nueva conversación.

---

## Tecnologías

| Categoría | Tecnología |
|---|---|
| Framework | Angular 22 (Standalone Components) |
| Lenguaje | TypeScript 6 |
| Estilos | SCSS (variables, animaciones, responsive) |
| Fuente tipográfica | Inter (Google Fonts) |
| HTTP Client | `@angular/common/http` con Fetch API |
| Gestión de estado | Angular Signals |
| Formato de código | Prettier |
| Build tool | `@angular/build` (Vite internamente) |

---

## Estructura del Proyecto

```
FrontEnd/
├── src/
│   ├── app/
│   │   ├── app.component.ts      # Componente raíz — lógica del chat
│   │   ├── app.component.html    # Template — vistas de bienvenida y chat
│   │   ├── app.component.scss    # Estilos del componente (burbujas, input, topbar)
│   │   ├── app.config.ts         # Configuración de la app (HttpClient, providers)
│   │   └── chat.service.ts       # Servicio HTTP — comunicación con la API
│   ├── index.html                # HTML raíz con meta tags y fuente Inter
│   ├── main.ts                   # Bootstrap de la aplicación
│   └── styles.scss               # Estilos globales (reset, body gradient, scrollbar)
├── public/
│   ├── SEGA-logo.png             # Logo principal de SEGA
│   ├── S-logo.png                # Favicon
│   └── aluraoracle-logo.png      # Logo Alura + Oracle (topbar)
├── angular.json                  # Configuración del workspace Angular CLI
├── package.json                  # Dependencias y scripts npm
├── tsconfig.json                 # Configuración base de TypeScript
└── tsconfig.app.json             # Configuración TypeScript para la app
```

---

## Requisitos Previos

- **Node.js** 20 o superior
- **npm** 11 o superior
- El **backend** corriendo en `http://localhost:8000` (ver `BackEnd/README.md`)

---

## Instalación

**1. Entra al directorio del frontend:**

```bash
cd FrontEnd
```

**2. Instala las dependencias:**

```bash
npm install
```

---

## Ejecución

**Servidor de desarrollo:**

```bash
npm start
# o equivalente:
ng serve
```

Abre el navegador en [http://localhost:4200](http://localhost:4200). La aplicación recarga automáticamente al guardar cualquier archivo fuente.

---

## Arquitectura de la App

El proyecto usa **Standalone Components** (sin NgModules). El componente raíz `App` centraliza toda la lógica de la UI.

### Estado con Signals

```typescript
readonly userMessage = signal('');         // Texto del input
readonly isLoading   = signal(false);      // Spinner mientras el agente responde
readonly viewState   = signal<'welcome' | 'chat'>('welcome');  // Vista activa
readonly mensajes    = signal<Mensaje[]>([]); // Historial de la conversación
```

### Interfaz `Mensaje`

```typescript
export interface Mensaje {
  rol: 'user' | 'assistant';
  contenido: string;
  fuentes?: string[];   // Documentos usados por el agente (solo en respuestas)
  error?: boolean;      // Aplica estilo de error a la burbuja
}
```

### Flujo de una interacción

```
Usuario escribe → onSendMessage()
    │
    ├── Agrega burbuja del usuario al historial
    ├── Activa isLoading (muestra typing indicator)
    └── ChatService.enviarPregunta()
            │
            ├── [éxito] → Agrega burbuja del asistente con respuesta y fuentes
            └── [error] → Agrega burbuja con mensaje de error (estilo rojo)
```

### Nuevo chat

Al hacer clic en el botón `+`, se llama a `ChatService.reiniciarChat()`, que envía `POST /reset-chat` al backend para limpiar el historial del servidor. Luego se limpia el estado local y se vuelve a la vista de bienvenida.

---

## ChatService

El servicio gestiona toda la comunicación HTTP y mantiene el `session_id` en memoria durante la sesión del navegador.

### Métodos

| Método | Endpoint | Descripción |
|---|---|---|
| `enviarPregunta(pregunta)` | `POST /chat` | Envía la pregunta y guarda el `session_id` devuelto |
| `verificarSalud()` | `GET /health` | Comprueba que el backend esté operativo |
| `reiniciarChat()` | `POST /reset-chat` | Limpia el historial en el servidor y resetea el `session_id` local |

### Gestión de sesión

El `session_id` (UUID) se recibe en la primera respuesta del backend y se reenvía en todas las peticiones siguientes mediante el header `x-session-id`. Esto garantiza que el historial de conversación sea exclusivo de cada usuario.

```
Primera petición  → sin header  →  backend genera y devuelve session_id
Peticiones siguientes → header x-session-id: <uuid> → backend mantiene contexto
```

### Manejo de errores HTTP

| Código | Mensaje al usuario |
|---|---|
| `0` (sin conexión) | No se pudo conectar con el servidor |
| `503` | El agente todavía está inicializando |
| Otro | Detalle del error devuelto por la API |

---

## Estilos y Diseño

### Paleta de colores (variables SCSS)

| Variable | Valor | Uso |
|---|---|---|
| `$blue-primary` | `#1a3a8f` | Burbujas de usuario, botones, acentos |
| `$blue-mid` | `#1e4fc8` | Subtítulos, gradientes |
| `$blue-light` | `#3b6cf8` | Efectos hover |
| `$gray-subtle` | `#8a95ad` | Placeholder, disclaimer, dots de typing |
| `$white` | `#ffffff` | Burbujas del asistente, input |

El fondo de la página es un gradiente suave: `#eef2fb → #e2eaf8 → #d6e3f7`.

### Animaciones

| Nombre | Descripción |
|---|---|
| `fadeInUp` | Entrada de cada nuevo mensaje desde abajo |
| `fadeIn` | Transición al cambiar de vista bienvenida → chat |
| `typing` | Tres puntos rebotando en el indicador de escritura |
| `spin` | Spinner circular en el botón de envío mientras carga |

### Responsive

El layout es fluido. En pantallas menores a `600px` se reduce el tamaño del título de bienvenida y el padding del input, manteniendo la usabilidad en móviles.

---

## Build de Producción

```bash
npm run build
```

Los artefactos se generan en `dist/sega-assistant/`. El build de producción activa optimizaciones automáticas (tree-shaking, minificación, hashing de assets).

**Límites de bundle configurados en `angular.json`:**

| Tipo | Warning | Error |
|---|---|---|
| Bundle inicial | 500 kB | 1 MB |
| Estilo por componente | 4 kB | 8 kB |

---

## Conexión con el Backend

La URL base de la API está definida en `chat.service.ts`:

```typescript
private readonly apiUrl = 'http://localhost:8000';
```

Para cambiarla (por ejemplo, en producción), edita esa constante o configúrala mediante un `environment` de Angular.

Asegúrate de que el backend tenga habilitado CORS para el origen del frontend. Por defecto, el backend permite `http://localhost:4200`.
