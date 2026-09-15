import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { WebSocketServer, WebSocket } from "ws";
import { GatewayConnection } from "../renderer/gateway/connection.js";
import { PROTOCOL_VERSION, JarvisResponse, JarvisEvent } from "@jarvis/protocol";

// Polyfill WebSocket in Node test runner environment
if (typeof globalThis.WebSocket === "undefined") {
  (globalThis as any).WebSocket = WebSocket;
}

describe("Desktop Gateway Connection", () => {
  it("should fail gracefully when sending request while offline", async () => {
    const client = new GatewayConnection("ws://127.0.0.1:9876/ws");
    assert.equal(client.isConnected(), false);

    const resp = await client.sendRequest("system.ping");
    assert.equal(resp.success, false);
    assert.equal(resp.error?.code, "GATEWAY_OFFLINE");
  });

  it("should connect to Gateway, send request, correlate response, receive events, and disconnect", async () => {
    const wss = new WebSocketServer({ port: 0 });
    await new Promise<void>((resolve) => wss.on("listening", () => resolve()));
    const port = (wss.address() as any).port;

    let serverWs: WebSocket | null = null;
    wss.on("connection", (ws) => {
      serverWs = ws;
      ws.on("message", (raw) => {
        const parsed = JSON.parse(raw.toString());
        if (parsed.type === "system.ping") {
          const resp: JarvisResponse = {
            id: parsed.id,
            type: "system.ping",
            version: PROTOCOL_VERSION,
            timestamp: new Date().toISOString(),
            success: true,
            payload: { status: "pong", client: "desktop" },
          };
          ws.send(JSON.stringify(resp));
        }
      });
    });

    const client = new GatewayConnection(`ws://127.0.0.1:${port}`);
    await client.connect();
    assert.equal(client.isConnected(), true);

    // 1. Send ping request
    const response = await client.sendRequest("system.ping", { test: true });
    assert.equal(response.success, true);
    assert.equal(response.payload?.status, "pong");

    // 2. Receive broadcast event from Gateway
    const eventsReceived: JarvisEvent[] = [];
    client.onEvent((ev) => eventsReceived.push(ev));

    const testEvent: JarvisEvent = {
      id: "ev_desk_1",
      type: "agent.task.started",
      version: PROTOCOL_VERSION,
      timestamp: new Date().toISOString(),
      payload: { agent: "Planner", status: "working" },
    };

    serverWs!.send(JSON.stringify(testEvent));

    await new Promise((r) => setTimeout(r, 60));
    assert.equal(eventsReceived.length, 1);
    assert.equal(eventsReceived[0].id, "ev_desk_1");
    assert.equal(eventsReceived[0].payload.agent, "Planner");

    client.disconnect();
    assert.equal(client.isConnected(), false);

    await new Promise<void>((resolve) => wss.close(() => resolve()));
  });
});
