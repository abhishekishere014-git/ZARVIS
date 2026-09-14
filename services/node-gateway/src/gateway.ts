import http from "node:http";
import { WebSocketServer, WebSocket } from "ws";
import { GatewayConfig } from "./config.js";
import { HealthMonitor, GatewayHealthReport } from "./health.js";
import { Logger } from "./logger.js";
import {
  validateRequest,
  validateEvent,
  JarvisResponse,
  PROTOCOL_VERSION,
} from "@jarvis/protocol";

export class NodeGateway {
  private readonly config: GatewayConfig;
  private readonly logger: Logger;
  private readonly healthMonitor: HealthMonitor;
  private server: http.Server | null = null;
  private wss: WebSocketServer | null = null;
  private readonly clients = new Set<WebSocket>();

  constructor(config: GatewayConfig) {
    this.config = config;
    this.logger = new Logger("jarvis.gateway", config.logLevel);
    this.healthMonitor = new HealthMonitor();
  }

  public getHealth(): GatewayHealthReport {
    return this.healthMonitor.getReport();
  }

  public async start(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.logger.info(
        `Starting Node Gateway on ${this.config.host}:${this.config.port}...`
      );

      this.server = http.createServer((req, res) => {
        const url = new URL(req.url ?? "/", `http://${this.config.host}:${this.config.port}`);

        if (req.method === "GET" && url.pathname === "/health") {
          const report = this.getHealth();
          const statusCode = report.status === "unhealthy" ? 503 : 200;
          res.writeHead(statusCode, { "Content-Type": "application/json" });
          res.end(JSON.stringify(report, null, 2));
          return;
        }

        res.writeHead(404, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Not Found" }));
      });

      this.wss = new WebSocketServer({ server: this.server, path: "/ws" });

      this.wss.on("connection", (ws: WebSocket, req) => {
        const clientIp = req.socket.remoteAddress;
        this.logger.info(`Client connected from ${clientIp}`);
        this.clients.add(ws);
        this.healthMonitor.setActiveClientsCount(this.clients.size);

        ws.on("message", (raw) => {
          this.handleClientMessage(ws, raw.toString());
        });

        ws.on("close", () => {
          this.clients.delete(ws);
          this.healthMonitor.setActiveClientsCount(this.clients.size);
          this.logger.info("Client disconnected");
        });

        ws.on("error", (err) => {
          this.logger.error("WebSocket client error", undefined, err.message);
        });
      });

      this.server.listen(this.config.port, this.config.host, () => {
        this.healthMonitor.setGatewayRunning(true);
        this.logger.info(
          `Node Gateway online at http://${this.config.host}:${this.config.port} (WebSocket at /ws)`
        );
        resolve();
      });

      this.server.on("error", (err) => {
        this.logger.error("Server error during startup", undefined, err.message);
        this.healthMonitor.setGatewayRunning(false);
        reject(err);
      });
    });
  }

  public async stop(): Promise<void> {
    return new Promise((resolve) => {
      this.logger.info("Stopping Node Gateway...");
      this.healthMonitor.setGatewayRunning(false);

      // Close all connected WebSocket clients
      for (const client of this.clients) {
        if (client.readyState === WebSocket.OPEN) {
          client.close(1001, "Gateway shutting down");
        }
      }
      this.clients.clear();
      this.healthMonitor.setActiveClientsCount(0);

      if (this.wss) {
        this.wss.close();
        this.wss = null;
      }

      if (this.server) {
        this.server.close(() => {
          this.logger.info("Node Gateway stopped gracefully.");
          this.server = null;
          resolve();
        });
      } else {
        resolve();
      }
    });
  }

  private handleClientMessage(ws: WebSocket, raw: string): void {
    try {
      const parsed = JSON.parse(raw);
      const reqResult = validateRequest(parsed);

      if (!reqResult.valid) {
        const errorResponse: JarvisResponse = {
          id: parsed?.id ?? "unknown",
          type: "error.validation",
          version: PROTOCOL_VERSION,
          timestamp: new Date().toISOString(),
          success: false,
          error: {
            code: "INVALID_PROTOCOL_MESSAGE",
            message: reqResult.error ?? "Message failed schema validation",
          },
        };
        ws.send(JSON.stringify(errorResponse));
        return;
      }

      const request = reqResult.data!;
      this.logger.debug(`Received request '${request.type}'`, request.id);

      // Future Phase 10 will route this to Python Core via IPC
      // For Phase 02 foundation, acknowledge protocol receipt
      const ackResponse: JarvisResponse = {
        id: request.id,
        type: request.type,
        version: PROTOCOL_VERSION,
        timestamp: new Date().toISOString(),
        success: true,
        payload: {
          acknowledged: true,
          status: "queued_or_handled",
        },
      };
      ws.send(JSON.stringify(ackResponse));
    } catch (err) {
      this.logger.error("Failed to parse incoming message", undefined, String(err));
    }
  }
}
