import { z } from "zod";

export const GatewayConfigSchema = z.object({
  host: z
    .string()
    .default("127.0.0.1")
    .refine(
      (val) => val === "127.0.0.1" || val === "localhost",
      { message: "Security violation: Gateway must strictly bind to loopback (127.0.0.1 or localhost)" }
    ),
  port: z.coerce.number().int().min(1024).max(65535).default(3000),
  pythonCoreUrl: z.string().default("tcp://127.0.0.1:8765"),
  ipcHost: z.string().default("127.0.0.1"),
  ipcPort: z.coerce.number().int().min(1024).max(65535).default(8765),
  ipcTimeoutMs: z.coerce.number().int().default(30000),
  ipcReconnectIntervalMs: z.coerce.number().int().default(1000),
  ipcMaxMessageBytes: z.coerce.number().int().default(10 * 1024 * 1024),
  logLevel: z.enum(["debug", "info", "warn", "error"]).default("info"),
  nodeEnv: z.enum(["development", "production", "test"]).default("development"),
});

export type GatewayConfig = z.infer<typeof GatewayConfigSchema>;

export function loadConfig(env: NodeJS.ProcessEnv = process.env): GatewayConfig {
  return GatewayConfigSchema.parse({
    host: env.GATEWAY_HOST ?? "127.0.0.1",
    port: env.GATEWAY_PORT ?? 3000,
    pythonCoreUrl: env.PYTHON_CORE_URL ?? "tcp://127.0.0.1:8765",
    ipcHost: env.IPC_HOST ?? "127.0.0.1",
    ipcPort: env.IPC_PORT ?? 8765,
    ipcTimeoutMs: env.IPC_TIMEOUT_MS ?? 30000,
    ipcReconnectIntervalMs: env.IPC_RECONNECT_INTERVAL_MS ?? 1000,
    ipcMaxMessageBytes: env.IPC_MAX_MESSAGE_BYTES ?? 10 * 1024 * 1024,
    logLevel: env.GATEWAY_LOG_LEVEL ?? "info",
    nodeEnv: env.NODE_ENV ?? "development",
  });
}
