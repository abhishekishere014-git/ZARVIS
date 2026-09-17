import { describe, it } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { WebSocket } from "ws";
import { NodeGateway } from "../gateway.js";
import { loadConfig } from "../config.js";
import { PROTOCOL_VERSION, JarvisRequest, JarvisResponse } from "@jarvis/protocol";

describe("Node Gateway Lifecycle & Protocol Handling", () => {
  const testPort = 3199;
  const config = loadConfig({
    GATEWAY_HOST: "127.0.0.1",
    GATEWAY_PORT: String(testPort),
    GATEWAY_LOG_LEVEL: "error", // Suppress logs in tests
    NODE_ENV: "test",
  });

  it("should start up, serve /health, and shut down cleanly", async () => {
    const gateway = new NodeGateway(config);
    await gateway.start();

    // 1. Query /health over HTTP
    const healthReport = await new Promise<any>((resolve, reject) => {
      http.get(`http://127.0.0.1:${testPort}/health`, (res) => {
        assert.equal(res.statusCode, 200);
        let body = "";
        res.on("data", (chunk) => (body += chunk));
        res.on("end", () => resolve(JSON.parse(body)));
      }).on("error", reject);
    });

    assert.equal(healthReport.components.gateway.status, "healthy");
    assert.equal(healthReport.components.protocol.status, "healthy");

    // 2. Connect WebSocket client and send valid protocol request
    const ws = new WebSocket(`ws://127.0.0.1:${testPort}/ws`);

    await new Promise<void>((resolve, reject) => {
      ws.on("open", () => resolve());
      ws.on("error", reject);
    });

    const validRequest: JarvisRequest = {
      id: "test-req-001",
      type: "system.ping",
      version: PROTOCOL_VERSION,
      timestamp: new Date().toISOString(),
      payload: { ping: true },
    };

    const responsePromise = new Promise<JarvisResponse>((resolve) => {
      ws.on("message", (data) => {
        resolve(JSON.parse(data.toString()));
      });
    });

    ws.send(JSON.stringify(validRequest));
    const response = await responsePromise;

    assert.equal(response.id, "test-req-001");
    assert.equal(response.success, true);
    assert.equal(response.payload?.acknowledged, true);

    // 3. Send invalid protocol message (missing required fields)
    const invalidPromise = new Promise<JarvisResponse>((resolve) => {
      ws.once("message", (data) => {
        resolve(JSON.parse(data.toString()));
      });
    });

    ws.send(JSON.stringify({ bad: "message" }));
    const invalidResponse = await invalidPromise;
    assert.equal(invalidResponse.success, false);
    assert.equal(invalidResponse.error?.code, "INVALID_PROTOCOL_MESSAGE");

    // 4. Test system.health request when Python Core is offline
    const healthPromise = new Promise<JarvisResponse>((resolve) => {
      const handler = (data: any) => {
        const parsed = JSON.parse(data.toString());
        if (parsed.id === "test-health-req") {
          ws.removeListener("message", handler);
          resolve(parsed);
        }
      };
      ws.on("message", handler);
    });

    ws.send(JSON.stringify({
      id: "test-health-req",
      type: "system.health",
      version: PROTOCOL_VERSION,
      timestamp: new Date().toISOString(),
      payload: {},
    }));
    const healthResp = await healthPromise;
    assert.equal(healthResp.success, true);
    assert.equal(healthResp.payload?.core, "offline");
    assert.equal(healthResp.payload?.gateway, "healthy");
    assert.equal(healthResp.payload?.ipc, "disconnected");
    assert.equal(healthResp.payload?.voice, "unavailable");

    // 5. Close client and stop gateway
    ws.close();
    await gateway.stop();
  });
});
