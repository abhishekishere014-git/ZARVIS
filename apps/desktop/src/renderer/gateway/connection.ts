/**
 * Real WebSocket Gateway Connection for ZARVIS Desktop.
 * Communicates directly with Node Gateway over JSON-RPC v1.0.
 */

import {
  JarvisEvent,
  JarvisRequest,
  JarvisResponse,
  PROTOCOL_VERSION,
  validateEvent,
  validateResponse,
} from "@jarvis/protocol";

export type EventCallback = (event: JarvisEvent) => void;
export type StateCallback = (isConnected: boolean) => void;

interface PendingRequest {
  resolve: (response: JarvisResponse) => void;
  reject: (error: Error) => void;
  timer: any;
}

export class GatewayConnection {
  private ws: WebSocket | null = null;
  private isIntentionallyClosed = false;
  private reconnectTimer: any = null;
  private reconnectAttempts = 0;

  private readonly pendingRequests = new Map<string, PendingRequest>();
  private readonly eventListeners = new Set<EventCallback>();
  private readonly stateListeners = new Set<StateCallback>();

  constructor(private readonly gatewayUrl: string = "ws://127.0.0.1:3000/ws") {}

  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  public onEvent(callback: EventCallback): () => void {
    this.eventListeners.add(callback);
    return () => this.eventListeners.delete(callback);
  }

  public onStateChange(callback: StateCallback): () => void {
    this.stateListeners.add(callback);
    return () => this.stateListeners.delete(callback);
  }

  private notifyState(connected: boolean): void {
    for (const listener of this.stateListeners) {
      try {
        listener(connected);
      } catch {
        // Ignore listener errors
      }
    }
  }

  public connect(): Promise<void> {
    if (this.isConnected()) return Promise.resolve();
    this.isIntentionallyClosed = false;

    return new Promise((resolve, reject) => {
      let isSettled = false;

      try {
        this.ws = new WebSocket(this.gatewayUrl);

        this.ws.onopen = () => {
          this.reconnectAttempts = 0;
          this.notifyState(true);
          if (!isSettled) {
            isSettled = true;
            resolve();
          }
        };

        this.ws.onmessage = (event) => {
          this.handleIncomingMessage(event.data);
        };

        this.ws.onerror = (err) => {
          if (!isSettled) {
            isSettled = true;
            reject(err);
          }
        };

        this.ws.onclose = () => {
          this.notifyState(false);
          this.handleClose();
          if (!isSettled) {
            isSettled = true;
            resolve(); // Do not crash on initial close, allow reconnect loop
          }
        };
      } catch (err) {
        if (!isSettled) {
          isSettled = true;
          reject(err);
        }
      }
    });
  }

  public sendRequest(
    type: string,
    payload: Record<string, any> = {},
    timeoutMs: number = 30000
  ): Promise<JarvisResponse> {
    if (!this.isConnected()) {
      return Promise.resolve({
        id: `offline_${Date.now()}`,
        type,
        version: PROTOCOL_VERSION,
        timestamp: new Date().toISOString(),
        success: false,
        error: {
          code: "GATEWAY_OFFLINE",
          message: "Node Gateway is not currently connected",
        },
      });
    }

    const id = `req_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const request: JarvisRequest = {
      id,
      type,
      version: PROTOCOL_VERSION,
      timestamp: new Date().toISOString(),
      payload,
    };

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pendingRequests.delete(id);
        resolve({
          id,
          type,
          version: PROTOCOL_VERSION,
          timestamp: new Date().toISOString(),
          success: false,
          error: {
            code: "REQUEST_TIMEOUT",
            message: `Request '${type}' timed out after ${timeoutMs}ms`,
          },
        });
      }, timeoutMs);

      this.pendingRequests.set(id, { resolve, reject, timer });

      try {
        this.ws?.send(JSON.stringify(request));
      } catch (sendErr: any) {
        clearTimeout(timer);
        this.pendingRequests.delete(id);
        reject(sendErr);
      }
    });
  }

  private handleIncomingMessage(rawData: any): void {
    let parsed: any;
    try {
      const str = typeof rawData === "string" ? rawData : rawData.toString();
      parsed = JSON.parse(str);
    } catch {
      return;
    }

    // 1. Correlate Response
    if (parsed && typeof parsed.id === "string" && this.pendingRequests.has(parsed.id)) {
      const pending = this.pendingRequests.get(parsed.id)!;
      clearTimeout(pending.timer);
      this.pendingRequests.delete(parsed.id);

      const validated = validateResponse(parsed);
      if (validated.valid && validated.data) {
        pending.resolve(validated.data);
      } else {
        pending.resolve({
          id: parsed.id,
          type: parsed.type ?? "unknown",
          version: PROTOCOL_VERSION,
          timestamp: new Date().toISOString(),
          success: false,
          error: {
            code: "INVALID_RESPONSE_SCHEMA",
            message: validated.error ?? "Invalid response schema received",
          },
        });
      }
      return;
    }

    // 2. Broadcast Event
    const eventValidation = validateEvent(parsed);
    if (eventValidation.valid && eventValidation.data) {
      for (const listener of this.eventListeners) {
        try {
          listener(eventValidation.data);
        } catch {
          // Ignore listener errors
        }
      }
    }
  }

  private handleClose(): void {
    this.ws = null;

    // Fail in-flight requests
    for (const [id, pending] of this.pendingRequests) {
      clearTimeout(pending.timer);
      pending.resolve({
        id,
        type: "unknown",
        version: PROTOCOL_VERSION,
        timestamp: new Date().toISOString(),
        success: false,
        error: {
          code: "CONNECTION_CLOSED",
          message: "Gateway connection closed while request was in-flight",
        },
      });
    }
    this.pendingRequests.clear();

    if (!this.isIntentionallyClosed) {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer || this.isIntentionallyClosed) return;

    this.reconnectAttempts++;
    const baseDelay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts - 1), 10000);
    const jitter = baseDelay * (0.8 + Math.random() * 0.4);
    const delay = Math.round(jitter);

    this.reconnectTimer = setTimeout(async () => {
      this.reconnectTimer = null;
      if (this.isIntentionallyClosed) return;

      try {
        await this.connect();
      } catch {
        // Reconnect failure triggers handleClose which schedules next
      }
    }, delay);
  }

  public disconnect(): void {
    this.isIntentionallyClosed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    // Fail all in-flight requests on explicit disconnect
    for (const [id, pending] of this.pendingRequests) {
      clearTimeout(pending.timer);
      pending.resolve({
        id,
        type: "unknown",
        version: PROTOCOL_VERSION,
        timestamp: new Date().toISOString(),
        success: false,
        error: {
          code: "CONNECTION_CLOSED",
          message: "Gateway connection disconnected",
        },
      });
    }
    this.pendingRequests.clear();

    if (this.ws) {
      try {
        this.ws.close();
      } catch {}
      this.ws = null;
    }
    this.notifyState(false);
  }
}
