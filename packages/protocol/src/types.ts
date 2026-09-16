/**
 * JARVIS Protocol Message Contracts
 * Specification Version: 1.0
 */

export const PROTOCOL_VERSION = "1.0" as const;
export type ProtocolVersion = typeof PROTOCOL_VERSION;

export interface ProtocolError {
  code: string;
  message: string;
  details?: unknown;
}

export interface JarvisRequest<TPayload = Record<string, unknown>> {
  id: string;
  type: string;
  version: ProtocolVersion;
  timestamp: string;
  payload: TPayload;
}

export interface JarvisResponse<TPayload = Record<string, unknown>> {
  id: string;
  type: string;
  version: ProtocolVersion;
  timestamp: string;
  success: boolean;
  payload?: TPayload;
  error?: ProtocolError | null;
}

export interface JarvisEvent<TPayload = Record<string, unknown>> {
  id: string;
  type: string;
  version: ProtocolVersion;
  timestamp: string;
  correlation_id?: string;
  payload: TPayload;
}

export type JarvisMessage =
  | JarvisRequest
  | JarvisResponse
  | JarvisEvent;
