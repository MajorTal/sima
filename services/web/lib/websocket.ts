/**
 * WebSocket client for real-time event streaming.
 */

import type { WebSocketMessage, Stream, Event } from './types';

type EventCallback = (event: Event) => void;
type StatusCallback = (connected: boolean) => void;

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8001';

class WebSocketClient {
  private ws: WebSocket | null = null;
  private stream: Stream | 'all' = 'all';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval: ReturnType<typeof setInterval> | null = null;

  private eventCallbacks: EventCallback[] = [];
  private statusCallbacks: StatusCallback[] = [];

  connect(stream: Stream | 'all' = 'all') {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.stream = stream;
    const url = `${WS_BASE}/ws/events?stream=${stream}`;

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.notifyStatus(true);
        this.startPing();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.notifyStatus(false);
        this.stopPing();
        this.scheduleReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
      this.scheduleReconnect();
    }
  }

  disconnect() {
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnect
    this.stopPing();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private handleMessage(message: WebSocketMessage) {
    switch (message.type) {
      case 'connected':
        console.log(`Connected to stream: ${message.stream}`);
        break;
      case 'event':
        if (message.data) {
          this.notifyEvent(message.data as Event);
        }
        break;
      case 'heartbeat':
      case 'pong':
        // Connection alive
        break;
    }
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      this.connect(this.stream);
    }, delay);
  }

  private startPing() {
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
      }
    }, 25000);
  }

  private stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  onEvent(callback: EventCallback) {
    this.eventCallbacks.push(callback);
    return () => {
      this.eventCallbacks = this.eventCallbacks.filter((cb) => cb !== callback);
    };
  }

  onStatus(callback: StatusCallback) {
    this.statusCallbacks.push(callback);
    return () => {
      this.statusCallbacks = this.statusCallbacks.filter((cb) => cb !== callback);
    };
  }

  private notifyEvent(event: Event) {
    this.eventCallbacks.forEach((cb) => cb(event));
  }

  private notifyStatus(connected: boolean) {
    this.statusCallbacks.forEach((cb) => cb(connected));
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const wsClient = new WebSocketClient();
