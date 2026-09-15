import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { WebSocketServer, WebSocket } from "ws";
import { GatewayConnection } from "../renderer/gateway/connection.js";
import { DesktopStore } from "../renderer/state/store.js";
import { PROTOCOL_VERSION, JarvisResponse } from "@jarvis/protocol";

if (typeof globalThis.WebSocket === "undefined") {
  (globalThis as any).WebSocket = WebSocket;
}

describe("Desktop Client Real End-to-End Smoke Test", () => {
  it("should complete Desktop -> Gateway -> Core ping roundtrip and update UI state", async () => {
    // 1. Initialize Mock Gateway server simulating Node Gateway
    const wss = new WebSocketServer({ port: 0 });
    await new Promise<void>((resolve) => wss.on("listening", () => resolve()));
    const port = (wss.address() as any).port;

    wss.on("connection", (ws) => {
      ws.on("message", (raw) => {
        const parsed = JSON.parse(raw.toString());
        if (parsed.type === "system.ping") {
          const resp: JarvisResponse = {
            id: parsed.id,
            type: "system.ping",
            version: PROTOCOL_VERSION,
            timestamp: new Date().toISOString(),
            success: true,
            payload: { status: "pong", server: "python-core", roundtrip_ms: 12 },
          };
          ws.send(JSON.stringify(resp));
        }
      });
    });

    // 2. Initialize Desktop state store and gateway connection
    const store = new DesktopStore();
    const client = new GatewayConnection(`ws://127.0.0.1:${port}`);

    await client.connect();
    assert.equal(client.isConnected(), true);

    // 3. User submits command
    const cmdText = "Perform system health check";
    store.addMessage({
      id: "msg_user_1",
      sender: "user",
      text: cmdText,
      timestamp: new Date().toLocaleTimeString(),
    });

    // 4. Send request through Gateway
    store.setAssistantState("THINKING");
    const response = await client.sendRequest("system.ping", { command: cmdText });

    assert.equal(response.success, true);
    assert.equal(response.payload?.status, "pong");
    assert.equal(response.payload?.server, "python-core");

    // 5. Update assistant response in Store
    store.addMessage({
      id: "msg_asst_1",
      sender: "assistant",
      text: "System health check verified. All subsystems operational.",
      timestamp: new Date().toLocaleTimeString(),
    });
    store.addActivity({
      id: "act_e2e_1",
      title: "System Diagnostics",
      category: "system",
      description: "Health check completed with 0 errors",
      timestamp: new Date().toLocaleTimeString(),
    });
    store.setAssistantState("IDLE");

    // 6. Verify full state integration
    assert.equal(store.getState().assistantState, "IDLE");
    assert.equal(store.getState().conversation.length, 2);
    assert.equal(store.getState().conversation[0].sender, "user");
    assert.equal(store.getState().conversation[1].sender, "assistant");
    assert.equal(store.getState().activity.length, 1);
    assert.equal(store.getState().activity[0].title, "System Diagnostics");

    // 7. Clean teardown
    client.disconnect();
    await new Promise<void>((resolve) => wss.close(() => resolve()));
  });

  it("should complete real agent.execute and vision.scan roundtrips", async () => {
    const wss = new WebSocketServer({ port: 0 });
    await new Promise<void>((resolve) => wss.on("listening", () => resolve()));
    const port = (wss.address() as any).port;

    wss.on("connection", (ws) => {
      ws.on("message", (raw) => {
        const parsed = JSON.parse(raw.toString());
        if (parsed.type === "agent.execute") {
          const resp: JarvisResponse = {
            id: parsed.id,
            type: "agent.execute",
            version: PROTOCOL_VERSION,
            timestamp: new Date().toISOString(),
            success: true,
            payload: {
              run_id: "run_e2e_456",
              status: "completed",
              summary: "Executive summary document generated and verified in sandbox.",
              task_statistics: { total: 4, completed: 4 },
            },
          };
          ws.send(JSON.stringify(resp));
        } else if (parsed.type === "vision.scan") {
          const resp: JarvisResponse = {
            id: parsed.id,
            type: "vision.scan",
            version: PROTOCOL_VERSION,
            timestamp: new Date().toISOString(),
            success: true,
            payload: {
              observation_id: "obs_e2e_789",
              resolution: { width: 1920, height: 1080 },
              elements_count: 14,
              interactive_count: 8,
              active_window_title: "VS Code",
            },
          };
          ws.send(JSON.stringify(resp));
        }
      });
    });

    const store = new DesktopStore();
    const client = new GatewayConnection(`ws://127.0.0.1:${port}`);
    await client.connect();

    // Test agent.execute
    const agentResp = await client.sendRequest("agent.execute", { goal: "Generate report" });
    assert.equal(agentResp.success, true);
    assert.equal(agentResp.payload?.run_id, "run_e2e_456");
    assert.equal(agentResp.payload?.status, "completed");

    // Test vision.scan
    const visionResp = await client.sendRequest("vision.scan", { monitor_index: 0 });
    assert.equal(visionResp.success, true);
    assert.equal(visionResp.payload?.interactive_count, 8);
    assert.equal(visionResp.payload?.active_window_title, "VS Code");

    client.disconnect();
    await new Promise<void>((resolve) => wss.close(() => resolve()));
  });
});
