import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';

// ─────────────────────────────────────────────
// Interfaces que reflejan los modelos de FastAPI
// ─────────────────────────────────────────────
export interface ChatRequest {
  pregunta: string;
}

export interface ChatResponse {
  respuesta: string;
  fuentes: string[];
  session_id: string;
}

export interface HealthResponse {
  estado: string;
  vector_store_listo: boolean;
  agente_listo: boolean;
  mensaje: string;
}

export interface ResetResponse {
  exito: boolean;
  mensaje: string;
}

@Injectable({
  providedIn: 'root',
})
export class ChatService {
  private readonly apiUrl = 'http://localhost:8000';
  private readonly http = inject(HttpClient);
  private sessionId: string | null = null;

  /**
   * Envía una pregunta al agente RAG y recibe la respuesta con fuentes.
   */
  enviarPregunta(pregunta: string): Observable<ChatResponse> {
    const body: ChatRequest = { pregunta };
    
    let headers = new HttpHeaders();
    if (this.sessionId) {
      headers = headers.set('x-session-id', this.sessionId);
    }

    return this.http
      .post<ChatResponse>(`${this.apiUrl}/chat`, body, { headers })
      .pipe(
        tap((res) => {
          if (res.session_id) {
            this.sessionId = res.session_id;
          }
        }),
        catchError(this.handleError.bind(this))
      );
  }

  /**
   * Verifica que el backend esté operativo.
   */
  verificarSalud(): Observable<HealthResponse> {
    return this.http
      .get<HealthResponse>(`${this.apiUrl}/health`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Reinicia el historial de conversación en el backend.
   */
  reiniciarChat(): Observable<ResetResponse> {
    if (!this.sessionId) {
      return new Observable<ResetResponse>(subscriber => {
        subscriber.next({ exito: true, mensaje: 'No hay sesión activa.' });
        subscriber.complete();
      });
    }

    const headers = new HttpHeaders().set('x-session-id', this.sessionId);
    return this.http
      .post<ResetResponse>(`${this.apiUrl}/reset-chat`, {}, { headers })
      .pipe(
        tap(() => {
          this.sessionId = null;
        }),
        catchError(this.handleError.bind(this))
      );
  }

  // ─────────────────────────────────────────────
  // Manejo de errores HTTP
  // ─────────────────────────────────────────────
  private handleError(error: HttpErrorResponse): Observable<never> {
    let mensaje = 'Ocurrió un error inesperado. Inténtalo de nuevo.';

    if (error.status === 0) {
      mensaje = 'No se pudo conectar con el servidor. Verifica que el backend esté activo.';
    } else if (error.status === 503) {
      mensaje = 'El agente todavía está inicializando. Espera unos segundos e inténtalo de nuevo.';
    } else if (error.error?.detail) {
      mensaje = error.error.detail;
    }

    return throwError(() => new Error(mensaje));
  }
}
