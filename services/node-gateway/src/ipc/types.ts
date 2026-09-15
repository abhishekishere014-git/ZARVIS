import { JarvisRequest, JarvisResponse, JarvisEvent } from "@jarvis/protocol";

export type IPCConnectionState =
  | "DISCONNECTED"
  | "CONNECTING"
  | "CONNECTED"
  | "DEGRADED"
  | "RECONNECTING"
  | "STOPPING"
  | "STOPPED"
  | "ERROR";

export interface IPCClientOptions {
  host: string;
  port: number;
  timeoutMs?: number;
  reconnectIntervalMs?: number;
  maxMessageBytes?: number;
  heartbeatIntervalMs?: number;
}

export interface PendingRequest {
  request: JarvisRequest;
  resolve: (response: JarvisResponse) => void;
  reject: (error: Error) => void;
  timer: NodeJS.Timeout;
}

export type EventListener = (event: JarvisEvent) => void;
export type StateChangeListener = (state: IPCConnectionState) => void;
