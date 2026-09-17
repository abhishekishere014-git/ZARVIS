import { z } from "zod";
import {
  PROTOCOL_VERSION,
  JarvisRequest,
  JarvisResponse,
  JarvisEvent,
} from "./types.js";

export const ProtocolVersionSchema = z.literal(PROTOCOL_VERSION);

export const ProtocolErrorSchema = z.object({
  code: z.string().min(1),
  message: z.string().min(1),
  details: z.unknown().optional(),
});

export const JarvisRequestSchema = z.object({
  id: z.string().min(1),
  type: z.string().min(1),
  version: ProtocolVersionSchema,
  timestamp: z.string().datetime({ offset: true }),
  payload: z.record(z.unknown()).default({}),
});

export const JarvisResponseSchema = z.object({
  id: z.string().min(1),
  type: z.string().min(1),
  version: ProtocolVersionSchema,
  timestamp: z.string().datetime({ offset: true }),
  success: z.boolean(),
  payload: z.record(z.unknown()).nullable().optional(),
  error: ProtocolErrorSchema.nullable().optional(),
}).refine(
  (data) => {
    if (data.success) {
      return data.error === undefined || data.error === null;
    } else {
      return data.error !== undefined && data.error !== null;
    }
  },
  {
    message: "If success is true, error must be undefined or null; if success is false, error must be defined and not null",
  }
);

export const JarvisEventSchema = z.object({
  id: z.string().min(1),
  type: z.string().min(1),
  version: ProtocolVersionSchema,
  timestamp: z.string().datetime({ offset: true }),
  correlation_id: z.string().optional(),
  payload: z.record(z.unknown()).default({}),
});

export function parseRequest(raw: unknown): JarvisRequest {
  return JarvisRequestSchema.parse(raw) as JarvisRequest;
}

export function parseResponse(raw: unknown): JarvisResponse {
  return JarvisResponseSchema.parse(raw) as JarvisResponse;
}

export function parseEvent(raw: unknown): JarvisEvent {
  return JarvisEventSchema.parse(raw) as JarvisEvent;
}

export function validateRequest(raw: unknown): { valid: boolean; data?: JarvisRequest; error?: string } {
  const result = JarvisRequestSchema.safeParse(raw);
  if (result.success) {
    return { valid: true, data: result.data as JarvisRequest };
  }
  return { valid: false, error: result.error.message };
}

export function validateResponse(raw: unknown): { valid: boolean; data?: JarvisResponse; error?: string } {
  const result = JarvisResponseSchema.safeParse(raw);
  if (result.success) {
    return { valid: true, data: result.data as JarvisResponse };
  }
  return { valid: false, error: result.error.message };
}

export function validateEvent(raw: unknown): { valid: boolean; data?: JarvisEvent; error?: string } {
  const result = JarvisEventSchema.safeParse(raw);
  if (result.success) {
    return { valid: true, data: result.data as JarvisEvent };
  }
  return { valid: false, error: result.error.message };
}
