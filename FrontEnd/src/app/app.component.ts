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

  private readonly chatService = inject(ChatService);

  readonly userMessage = signal('');
  readonly isLoading = signal(false);
  readonly viewState = signal<'welcome' | 'chat'>('welcome');

  readonly mensajes = signal<Mensaje[]>([]);

  @ViewChild('messagesEnd') private messagesEnd?: ElementRef;
  private shouldScroll = false;

  readonly inputPlaceholder = 'Escribe un mensaje a SEGA Assistant...';

  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  onSendMessage(): void {
    const texto = this.userMessage().trim();
    if (!texto || this.isLoading()) return;
    this.viewState.set('chat');

    this.mensajes.update(msgs => [...msgs, { rol: 'user', contenido: texto }]);
    this.userMessage.set('');
    this.isLoading.set(true);
    this.shouldScroll = true;

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
        this.mensajes.set([]);
        this.viewState.set('welcome');
        this.userMessage.set('');
      },
    });
  }

  onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.onSendMessage();
    }
  }

  private scrollToBottom(): void {
    this.messagesEnd?.nativeElement?.scrollIntoView({ behavior: 'smooth' });
  }
}
