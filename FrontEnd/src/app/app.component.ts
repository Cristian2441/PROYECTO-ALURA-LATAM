import { Component, signal, ElementRef, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  imports: [FormsModule, CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class App {
  userMessage = signal('');

  viewState = signal<'welcome' | 'chat'>('welcome');
  readonly inputPlaceholder = 'Escribe un mensaje a SEGA Assistant...';

  onSendMessage(): void {
    const msg = this.userMessage().trim();
    if (!msg) return;
    this.viewState.set('chat');
    this.userMessage.set('');
  }

  onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.onSendMessage();
    }
  }
}
