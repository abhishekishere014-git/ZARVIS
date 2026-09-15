import net from "node:net";
import {
  JarvisRequest,
  JarvisResponse,
  JarvisEvent,
  PROTOCOL_VERSION,
  validateResponse,
  validateEvent,
} from "@jarvis/protocol";
import { Logger } from "../logger.js";
import { MessageBuffer } from "./framing.js";
import {
  EventListener,
  IPCClientOptions,
  IPCConnectionState,
  PendingRequest,
  StateChangeListener,
} from "./types.js";

export class IPCClient {
  private readonly options: Required<IPCClientOptions>;
  private readonly logger: Logger;
  private socket: net.Socket | null = null;
  private readonly messageBuffer: MessageBuffer;

  private state: IPCConnectionState = "DISCONNECTED";
  private isIntentionallyClosed = false;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;

  private readonly pendingRequests = new Map<string, PendingRequest>();
  private readonly eventListeners = new Set<EventListener>();
  private readonly stateListeners = new Set<StateChangeListener>();

  constructor(options: IPCClientOptions, logger?: Logger) {
    this.options = {
      host: options.host,
      port: options.port,
      timeoutMs: options.timeoutMs ?? 30000,
      reconnectIntervalMs: options.reconnectIntervalMs ?? 1000,
      maxMessageBytes: options.maxMessageBytes ?? 10 * 1024 * 1024,
      heartbeatIntervalMs: options.heartbeatIntervalMs ?? 10000,
    };
    this.logger = logger ?? new Logger("jarvis.gateway.ipc");
    this.messageBuffer = new MessageBuffer(this.options.maxMessageBytes);
  }

  public getState(): IPCConnectionState {
    return this.state;
  }

  public isConnected(): boolean {
    return this.state === "CONNECTED";
  }

  public onEvent(listener: EventListener): () => void {
    this.eventListeners.add(listener);
    return () => this.eventListeners.delete(listener);
  }

  public onStateChange(listener: StateChangeListener): () => void {
    this.stateListeners.add(listener);
    return () => this.stateListeners.delete(listener);
  }

  private setState(newState: IPCConnectionState): void {
    if (this.state !== newState) {
      this.logger.info(`IPC Connection state changed: ${this.state} -> ${newState}`);
      this.state = newState;
      for (const listener of this.stateListeners) {
        try {
          listener(newState);
        } catch (err) {
          this.logger.error("Error in state change listener", undefined, String(err));
        }
      }
    }
  }

  public async connect(): Promise<void> {
    if (this.isConnected() || this.state === "CONNECTING") {
      return;
    }

    this.isIntentionallyClosed = false;
    this.setState("CONNECTING");

    return new Promise<void>((resolve, reject) => {
      let isResolved = false;

      const socket = net.createConnection(
        { host: this.options.host, port: this.options.port },
        async () => {
          this.logger.info(`Connected to Python Core at ${this.options.host}:${this.options.port}`);
          try {
            await this.performHandshake();
            this.setState("CONNECTED");
            this.reconnectAttempts = 0;
            this.startHeartbeat();
            if (!isResolved) {
              isResolved = true;
              resolve();
            }
          } catch (handshakeErr) {
            this.logger.error("IPC Handshake failed", undefined, String(handshakeErr));
            this.setState("ERROR");
            socket.destroy();
            if (!isResolved) {
              isResolved = true;
              reject(handshakeErr);
            }
          }
        }
      );

      this.socket = socket;

      socket.on("data", (chunk) => {
        try {
          const frames = this.messageBuffer.push(chunk);
          for (const frame of frames) {
            this.handleIncomingFrame(frame);
          }
        } catch (err) {
          this.logger.error("Error processing stream buffer", undefined, String(err));
        }
      });

      socket.on("error", (err) => {
        this.logger.warn(`IPC socket error: ${err.message}`);
        if (!isResolved) {
          isResolved = true;
          this.setState("DEGRADED");
          reject(err);
        }
      });

      socket.on("close", () => {
        this.handleSocketClose();
        if (!isResolved) {
          isResolved = true;
          reject(new Error("Socket closed before connection completed"));
        }
      });
    });
  }

  private async performHandshake(): Promise<void> {
    const handshakeReq: JarvisRequest = {
      id: `handshake_${Date.now()}`,
      type: "ipc.handshake",
      version: PROTOCOL_VERSION,
      timestamp: new Date().toISOString(),
      payload: {
        service: "node-gateway",
        version: "0.1.0",
        protocol: PROTOCOL_VERSION,
        capabilities: ["requests", "events", "heartbeat"],
      },
    };

    const response = await this.sendRequestInternal(handshakeReq, 5000);
    if (!response.success) {
      throw new Error(`Handshake rejected: ${response.error?.message ?? "Unknown error"}`);
    }
    this.logger.info("IPC Handshake confirmed by Python Core");
  }

  public async sendRequest(request: JarvisRequest, timeoutMs?: number): Promise<JarvisResponse> {
    if (!this.isConnected()) {
      return {
        id: request.id,
        type: request.type,
        version: PROTOCOL_VERSION,
        timestamp: new Date().toISOString(),
        success: false,
        error: {
          code: "IPC_NOT_CONNECTED",
          message: "Python Core IPC connection is not connected",
        },
      };
    }
    return this.sendRequestInternal(request, timeoutMs);
  }

  private sendRequestInternal(request: JarvisRequest, customTimeoutMs?: number): Promise<JarvisResponse> {
    return new Promise<JarvisResponse>((resolve, reject) => {
      const timeoutDuration = customTimeoutMs ?? this.options.timeoutMs;

      const timer = setTimeout(() => {
        this.pendingRequests.delete(request.id);
        resolve({
          id: request.id,
          type: request.type,
          version: PROTOCOL_VERSION,
          timestamp: new Date().toISOString(),
          success: false,
          error: {
            code: "REQUEST_TIMEOUT",
            message: `IPC request '${request.type}' timed out after ${timeoutDuration}ms`,
          },
        });
      }, timeoutDuration);

      this.pendingRequests.set(request.id, {
        request,
        resolve,
        reject,
        timer,
      });

      try {
        const frame = MessageBuffer.formatFrame(request);
        this.socket?.write(frame, "utf-8", (err) => {
          if (err) {
            clearTimeout(timer);
            this.pendingRequests.delete(request.id);
            reject(err);
          }
        });
      } catch (err) {
        clearTimeout(timer);
        this.pendingRequests.delete(request.id);
        reject(err);
      }
    });
  }

  private handleIncomingFrame(raw: string): void {
    let parsed: any;
    try {
      parsed = JSON.parse(raw);
    } catch (err) {
      this.logger.error("Failed to parse incoming frame JSON", undefined, String(err));
      return;
    }

    // 1. Check if frame is a response to a pending request
    if (parsed && typeof parsed.id === "string" && this.pendingRequests.has(parsed.id)) {
      const pending = this.pendingRequests.get(parsed.id)!;
      clearTimeout(pending.timer);
      this.pendingRequests.delete(parsed.id);

      const respValidation = validateResponse(parsed);
      if (respValidation.valid && respValidation.data) {
        pending.resolve(respValidation.data);
      } else {
        pending.resolve({
          id: parsed.id,
          type: parsed.type ?? "unknown",
          version: PROTOCOL_VERSION,
          timestamp: new Date().toISOString(),
          success: false,
          error: {
            code: "INVALID_RESPONSE_SCHEMA",
            message: respValidation.error ?? "Invalid response schema",
          },
        });
      }
      return;
    }

    // 2. Check if frame is a server-pushed JarvisEvent
    const eventValidation = validateEvent(parsed);
    if (eventValidation.valid && eventValidation.data) {
      for (const listener of this.eventListeners) {
        try {
          listener(eventValidation.data);
        } catch (listenerErr) {
          this.logger.error("Error in event listener", undefined, String(listenerErr));
        }
      }
      return;
    }

    this.logger.debug("Received unhandled or late message frame", parsed?.id);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(async () => {
      if (!this.isConnected()) return;
      try {
        const pingReq: JarvisRequest = {
          id: `hb_${Date.now()}`,
          type: "system.ping",
          version: PROTOCOL_VERSION,
          timestamp: new Date().toISOString(),
          payload: {},
        };
        const resp = await this.sendRequestInternal(pingReq, 4000);
        if (!resp.success) {
          this.logger.warn("Heartbeat ping returned unsuccessful status");
        }
      } catch (err) {
        this.logger.warn(`Heartbeat ping failed: ${err}`);
      }
    }, this.options.heartbeatIntervalMs);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private handleSocketClose(): void {
    this.stopHeartbeat();
    this.socket = null;
    this.messageBuffer.clear();

    // Reject all in-flight pending requests
    for (const [id, pending] of this.pendingRequests) {
      clearTimeout(pending.timer);
      pending.resolve({
        id,
        type: pending.request.type,
        version: PROTOCOL_VERSION,
        timestamp: new Date().toISOString(),
        success: false,
        error: {
          code: "CONNECTION_CLOSED",
          message: "IPC connection closed while request was in-flight",
        },
      });
    }
    this.pendingRequests.clear();

    if (this.isIntentionallyClosed) {
      this.setState("STOPPED");
      return;
    }

    this.setState("DEGRADED");
    this.scheduleReconnect();
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer || this.isIntentionallyClosed) return;

    this.setState("RECONNECTING");
    this.reconnectAttempts++;

    // Bounded exponential backoff with full jitter: min 1s, max 10s
    const baseDelay = Math.min(
      this.options.reconnectIntervalMs * Math.pow(1.5, this.reconnectAttempts - 1),
      10000
    );
    const jitterDelay = Math.floor(baseDelay * (0.8 + Math.random() * 0.4));

    this.logger.info(`Scheduling IPC reconnect attempt ${this.reconnectAttempts} in ${jitterDelay}ms`);

    this.reconnectTimer = setTimeout(async () => {
      this.reconnectTimer = null;
      if (this.isIntentionallyClosed) return;

      try {
        await this.connect();
      } catch {
        // Reconnect failure automatically triggers handleSocketClose which schedules next
      }
    }, jitterDelay);
  }

  public async disconnect(): Promise<void> {
    this.isIntentionallyClosed = true;
    this.setState("STOPPING");

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.stopHeartbeat();

    if (this.socket) {
      this.socket.destroy();
      this.socket = null;
    }

    this.setState("STOPPED");
    this.logger.info("IPC Client disconnected gracefully");
  }
}
