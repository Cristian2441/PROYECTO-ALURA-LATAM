import { Component, signal, inject, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ChatService } from './chat.service';

export interface Mensaje {
  rol: 'user' | 'assistant';
  contenido: string;
  fuentes?: string[];
  error?: boolean;
}

@Component({
  selector: 'app-root',
  imports: [FormsModule, CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class App implements AfterViewChecked {
  // ── Servicios ──────────────────────────────────────
  private readonly chatService = inject(ChatService);

  // ── Estado de la UI ────────────────────────────────
  readonly userMessage = signal('');
  readonly isLoading = signal(false);
  readonly viewState = signal<'welcome' | 'chat'>('welcome');

  // ── Historial de mensajes ──────────────────────────
  readonly mensajes = signal<Mensaje[]>([]);

  // ── Scroll al final ────────────────────────────────
  @ViewChild('messagesEnd') private messagesEnd?: ElementRef;
  private shouldScroll = false;

  readonly inputPlaceholder = 'Escribe un mensaje a SEGA Assistant...';

  // ── AfterViewChecked: auto-scroll ──────────────────
  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  // ── Enviar mensaje ─────────────────────────────────
  onSendMessage(): void {
    const texto = this.userMessage().trim();
    if (!texto || this.isLoading()) return;

    // Cambiar a vista chat si estamos en welcome
    this.viewState.set('chat');

    // Agregar mensaje del usuario
    this.mensajes.update(msgs => [...msgs, { rol: 'user', contenido: texto }]);
    this.userMessage.set('');
    this.isLoading.set(true);
    this.shouldScroll = true;

    // Llamar al backend
    this.chatService.enviarPregunta(texto).subscribe({
      next: (res) => {
        this.mensajes.update(msgs => [
          ...msgs,
          {
            rol: 'assistant',
            contenido: res.respuesta,
            fuentes: res.fuentes,
          },
        ]);
        this.isLoading.set(false);
        this.shouldScroll = true;
      },
      error: (err: Error) => {
        this.mensajes.update(msgs => [
          ...msgs,
          {
            rol: 'assistant',
            contenido: err.message,
            error: true,
          },
        ]);
        this.isLoading.set(false);
        this.shouldScroll = true;
      },
    });
  }

  // ── Nuevo chat ─────────────────────────────────────
  onNuevoChat(): void {
    this.chatService.reiniciarChat().subscribe({
      next: () => {
        this.mensajes.set([]);
        this.viewState.set('welcome');
        this.userMessage.set('');
      },
      error: () => {
        // Si falla el reset del backend, limpiar igualmente la UI
        this.mensajes.set([]);
        this.viewState.set('welcome');
        this.userMessage.set('');
      },
    });
  }

  // ── Keyboard: Enter para enviar ────────────────────
  onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.onSendMessage();
    }
  }

  // ── Scroll al último mensaje ───────────────────────
  private scrollToBottom(): void {
    this.messagesEnd?.nativeElement?.scrollIntoView({ behavior: 'smooth' });
  }
}
