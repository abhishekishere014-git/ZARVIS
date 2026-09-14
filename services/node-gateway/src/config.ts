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
  pythonCoreUrl: z.string().url().default("ws://127.0.0.1:8765"),
  logLevel: z.enum(["debug", "info", "warn", "error"]).default("info"),
  nodeEnv: z.enum(["development", "production", "test"]).default("development"),
});

export type GatewayConfig = z.infer<typeof GatewayConfigSchema>;

export function loadConfig(env: NodeJS.ProcessEnv = process.env): GatewayConfig {
  return GatewayConfigSchema.parse({
    host: env.GATEWAY_HOST ?? "127.0.0.1",
    port: env.GATEWAY_PORT ?? 3000,
    pythonCoreUrl: env.PYTHON_CORE_URL ?? "ws://127.0.0.1:8765",
    logLevel: env.GATEWAY_LOG_LEVEL ?? "info",
    nodeEnv: env.NODE_ENV ?? "development",
  });
}
