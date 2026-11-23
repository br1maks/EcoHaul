import { config } from '@/config/env';
import type { WsMessage } from '@/shared/types';
import { getAccessToken } from './tokens';

type Handler = (message: WsMessage) => void;

class WebSocketManager {
  private ws: WebSocket | null = null;
  private handlers = new Map<string, Set<Handler>>();
  private reconnectTimer: ReturnType<typeof setTimeout> | undefined;
  private attempts = 0;
  private stopped = true;

  connect(token: string) {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) return;
    this.stopped = false;
    const socket = new WebSocket(`${config.wsUrl}?token=${encodeURIComponent(token)}`);
    this.ws = socket;
    socket.onopen = () => { this.attempts = 0; };
    socket.onmessage = (event) => {
      try {
        const message: WsMessage = JSON.parse(event.data);
        if (typeof message.type !== 'string' || typeof message.data !== 'object') return;
        for (const handler of this.handlers.get(message.type) ?? []) handler(message);
        for (const handler of this.handlers.get('*') ?? []) handler(message);
      } catch { /* Ignore malformed messages; keep the connection available. */ }
    };
    socket.onclose = () => {
      if (this.ws === socket) this.ws = null;
      if (this.stopped || this.attempts >= 5) return;
      const delay = 1000 * 2 ** this.attempts++;
      this.reconnectTimer = setTimeout(() => {
        const currentToken = getAccessToken();
        if (!this.stopped && currentToken) this.connect(currentToken);
      }, delay);
    };
  }

  on(type: string, handler: Handler) {
    const handlers = this.handlers.get(type) ?? new Set<Handler>();
    handlers.add(handler);
    this.handlers.set(type, handlers);
    return () => { handlers.delete(handler); };
  }

  send(message: WsMessage) {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(message));
  }

  disconnect() {
    this.stopped = true;
    clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
    this.attempts = 0;
  }

  isConnected() { return this.ws?.readyState === WebSocket.OPEN; }
}
export const wsManager = new WebSocketManager();
