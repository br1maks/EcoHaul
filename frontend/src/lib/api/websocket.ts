import { config } from '@/config/env';
import type { WsMessage } from '@/shared/types';
import { getAccessToken } from './tokens';
import { apiClient } from './client';

type Handler = (message: WsMessage) => void;

class WebSocketManager {
  private ws: WebSocket | null = null;
  private handlers = new Map<string, Set<Handler>>();
  private reconnectTimer: ReturnType<typeof setTimeout> | undefined;
  private attempts = 0;
  private stopped = true;
  private opening = false;
  private generation = 0;
  private seenEventIds = new Set<string>();

  private reconnect() {
    if (this.stopped || this.attempts >= 5) return;
    clearTimeout(this.reconnectTimer);
    const delay = 1000 * 2 ** this.attempts++;
    this.reconnectTimer = setTimeout(() => {
      const token = getAccessToken();
      if (!this.stopped && token) void this.connect(token);
    }, delay);
  }

  async connect(token: string) {
    if (this.opening || this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) return;
    this.stopped = false;
    this.opening = true;
    const generation = ++this.generation;
    try {
      const { data } = await apiClient.post<{ ticket: string }>('/auth/ws-ticket');
      if (this.stopped || generation !== this.generation || getAccessToken() !== token) return;
      const url = new URL(config.wsUrl);
      url.searchParams.set('ticket', data.ticket);
      const socket = new WebSocket(url.toString());
      this.ws = socket;
      socket.onopen = () => { this.attempts = 0; };
      socket.onmessage = (event) => {
        if (this.ws !== socket || this.stopped) return;
        try {
          const message: WsMessage = JSON.parse(event.data);
          if (typeof message.type !== 'string' || !message.data || typeof message.data !== 'object') return;
          if (typeof message.event_id === 'string') {
            if (this.seenEventIds.has(message.event_id)) return;
            this.seenEventIds.add(message.event_id);
            if (this.seenEventIds.size > 1024) this.seenEventIds.delete(this.seenEventIds.values().next().value!);
          }
          for (const handler of this.handlers.get(message.type) ?? []) handler(message);
          for (const handler of this.handlers.get('*') ?? []) handler(message);
        } catch { /* Ignore malformed messages; authoritative state comes from HTTP. */ }
      };
      socket.onclose = () => {
        if (this.ws !== socket) return;
        this.ws = null;
        this.reconnect();
      };
    } catch {
      if (generation === this.generation) this.reconnect();
    } finally {
      if (generation === this.generation) this.opening = false;
    }
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
    this.generation++;
    this.opening = false;
    clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
    this.attempts = 0;
  }

  isConnected() { return this.ws?.readyState === WebSocket.OPEN; }
}
export const wsManager = new WebSocketManager();
