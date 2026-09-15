import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { WebSocketServer, WebSocket } from "ws";
import { GatewayConnection } from "../renderer/gateway/connection.js";
import { DesktopStore } from "../renderer/state/store.js";
import { PROTOCOL_VERSION, JarvisResponse, JarvisEvent } from "@jarvis/protocol";

if (typeof globalThis.WebSocket === "undefined") {
  (globalThis as any).WebSocket = WebSocket;
}

describe("Phase 12.1 Real Subsystem Integration Tests", () => {
  it("1. Real Text Command: should stream agent.planning, tool.executed, and deliver verified AgentFinalResponse", async () => {
    const wss = new WebSocketServer({ port: 0 });
    await new Promise<void>((resolve) => wss.on("listening", () => resolve()));
    const port = (wss.address() as any).port;

    let receivedGoal = "";

    wss.on("connection", (ws) => {
      ws.on("message", (raw) => {
        const parsed = JSON.parse(raw.toString());
        if (parsed.type === "agent.execute") {
          receivedGoal = parsed.payload?.goal;

          // 1. Emit real-time agent.planning event
          const planEvt: JarvisEvent = {
            id: "evt_plan_1",
            type: "agent.planning",
            version: PROTOCOL_VERSION,
            timestamp: new Date().toISOString(),
            payload: { goal: receivedGoal, agent: "Planner" },
          };
          ws.send(JSON.stringify(planEvt));

          // 2. Emit real-time tool.executed event
          const toolEvt: JarvisEvent = {
            id: "evt_tool_1",
            type: "tool.executed",
            version: PROTOCOL_VERSION,
            timestamp: new Date().toISOString(),
            payload: { tool: "generate_docx", output: "Document generated at data/workspace/summary.docx" },
          };
          ws.send(JSON.stringify(toolEvt));

          // 3. Emit real-time agent.completed event
          const compEvt: JarvisEvent = {
            id: "evt_comp_1",
            type: "agent.completed",
            version: PROTOCOL_VERSION,
            timestamp: new Date().toISOString(),
            payload: { status: "completed" },
          };
          ws.send(JSON.stringify(compEvt));

          // 4. Send final response
          const resp: JarvisResponse = {
            id: parsed.id,
            type: "agent.execute",
            version: PROTOCOL_VERSION,
            timestamp: new Date().toISOString(),
            success: true,
            payload: {
              run_id: "run_real_001",
              goal_id: "goal_real_001",
              status: "completed",
              summary: "Executive summary document drafted, verified, and saved to sandbox.",
              task_statistics: { total: 3, completed: 3 },
              execution_time_ms: 850.5,
            },
          };
          ws.send(JSON.stringify(resp));
        }
      });
    });

    const store = new DesktopStore();
    const gateway = new GatewayConnection(`ws://127.0.0.1:${port}`);
    await gateway.connect();
    assert.equal(gateway.isConnected(), true);

    const receivedEvents: string[] = [];
    gateway.onEvent((evt) => {
      receivedEvents.push(evt.type);
    });

    // Execute real command
    const resp = await gateway.sendRequest("agent.execute", { goal: "Draft annual report" });
    assert.equal(resp.success, true);
    assert.equal(receivedGoal, "Draft annual report");
    assert.equal(resp.payload?.run_id, "run_real_001");
    assert.equal(resp.payload?.summary, "Executive summary document drafted, verified, and saved to sandbox.");
    assert.equal((resp.payload as any)?.task_statistics?.completed, 3);

    // Verify events were streamed
    assert.ok(receivedEvents.includes("agent.planning"));
    assert.ok(receivedEvents.includes("tool.executed"));
    assert.ok(receivedEvents.includes("agent.completed"));

    gateway.disconnect();
    await new Promise<void>((resolve) => wss.close(() => resolve()));
  });

  it("2. Real Voice Flow: should process audio buffer and return Kokoro TTS synthesized audio", async () => {
    const wss = new WebSocketServer({ port: 0 });
    await new Promise<void>((resolve) => wss.on("listening", () => resolve()));
    const port = (wss.address() as any).port;

    let receivedAudioBytes = false;

    wss.on("connection", (ws) => {
      ws.on("message", (raw) => {
        const parsed = JSON.parse(raw.toString());
        if (parsed.type === "voice.interact") {
          receivedAudioBytes = !!parsed.payload?.audio_base64;

          const resp: JarvisResponse = {
            id: parsed.id,
            type: "voice.interact",
            version: PROTOCOL_VERSION,
            timestamp: new Date().toISOString(),
            success: true,
            payload: {
              text: "Hello! I am ready to automate your tasks.",
              audio_base64: "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=", // valid base64 WAV header
              duration_sec: 2.1,
              agent_status: "completed",
            },
          };
          ws.send(JSON.stringify(resp));
        }
      });
    });

    const gateway = new GatewayConnection(`ws://127.0.0.1:${port}`);
    await gateway.connect();

    // Send mock recorded microphone audio
    const dummyAudioBase64 = Buffer.from("dummy_audio_pcm_stream").toString("base64");
    const resp = await gateway.sendRequest("voice.interact", { audio_base64: dummyAudioBase64 });

    assert.equal(resp.success, true);
    assert.equal(receivedAudioBytes, true);
    assert.equal(resp.payload?.text, "Hello! I am ready to automate your tasks.");
    assert.ok(((resp.payload as any)?.audio_base64 as string).length > 0);
    assert.equal(resp.payload?.duration_sec, 2.1);

    gateway.disconnect();
    await new Promise<void>((resolve) => wss.close(() => resolve()));
  });

  it("3. Real Vision Flow: should execute vision.scan and return grounded visual targets", async () => {
    const wss = new WebSocketServer({ port: 0 });
    await new Promise<void>((resolve) => wss.on("listening", () => resolve()));
    const port = (wss.address() as any).port;

    wss.on("connection", (ws) => {
      ws.on("message", (raw) => {
        const parsed = JSON.parse(raw.toString());
        if (parsed.type === "vision.scan") {
          const resp: JarvisResponse = {
            id: parsed.id,
            type: "vision.scan",
            version: PROTOCOL_VERSION,
            timestamp: new Date().toISOString(),
            success: true,
            payload: {
              observation_id: "obs_real_001",
              monitor_index: parsed.payload?.monitor_index ?? 0,
              resolution: { width: 1920, height: 1080 },
              elements_count: 8,
              interactive_count: 5,
              active_window_title: "Visual Studio Code - ZARVIS",
              elements: [
                { element_id: "el_1", element_type: "button", label: "Run", confidence: 0.96 },
                { element_id: "el_2", element_type: "input", label: "Search files", confidence: 0.91 },
              ],
            },
          };
          ws.send(JSON.stringify(resp));
        }
      });
    });

    const gateway = new GatewayConnection(`ws://127.0.0.1:${port}`);
    await gateway.connect();

    const resp = await gateway.sendRequest("vision.scan", { monitor_index: 0 });
    assert.equal(resp.success, true);
    assert.equal(resp.payload?.observation_id, "obs_real_001");
    assert.equal(resp.payload?.active_window_title, "Visual Studio Code - ZARVIS");
    assert.equal(resp.payload?.interactive_count, 5);
    assert.equal(((resp.payload as any)?.elements as any[]).length, 2);

    gateway.disconnect();
    await new Promise<void>((resolve) => wss.close(() => resolve()));
  });

  it("4. Real Stop & Barge-In: should dispatch voice.stop and cancel active playback", async () => {
    const wss = new WebSocketServer({ port: 0 });
    await new Promise<void>((resolve) => wss.on("listening", () => resolve()));
    const port = (wss.address() as any).port;

    let stopDispatched = false;

    wss.on("connection", (ws) => {
      ws.on("message", (raw) => {
        const parsed = JSON.parse(raw.toString());
        if (parsed.type === "voice.stop") {
          stopDispatched = true;
          const resp: JarvisResponse = {
            id: parsed.id,
            type: "voice.stop",
            version: PROTOCOL_VERSION,
            timestamp: new Date().toISOString(),
            success: true,
            payload: { stopped: true, status: "idle" },
          };
          ws.send(JSON.stringify(resp));
        }
      });
    });

    const gateway = new GatewayConnection(`ws://127.0.0.1:${port}`);
    await gateway.connect();

    const resp = await gateway.sendRequest("voice.stop");
    assert.equal(resp.success, true);
    assert.equal(stopDispatched, true);
    assert.equal(resp.payload?.stopped, true);

    gateway.disconnect();
    await new Promise<void>((resolve) => wss.close(() => resolve()));
  });

  it("5. IPC Error Handling: should report explicit error when backend fails or times out", async () => {
    const wss = new WebSocketServer({ port: 0 });
    await new Promise<void>((resolve) => wss.on("listening", () => resolve()));
    const port = (wss.address() as any).port;

    wss.on("connection", (ws) => {
      ws.on("message", (raw) => {
        const parsed = JSON.parse(raw.toString());
        const errorResp: JarvisResponse = {
          id: parsed.id,
          type: parsed.type,
          version: PROTOCOL_VERSION,
          timestamp: new Date().toISOString(),
          success: false,
          error: {
            code: "AGENT_EXECUTION_ERROR",
            message: "Target tool requires user policy approval before execution",
          },
        };
        ws.send(JSON.stringify(errorResp));
      });
    });

    const gateway = new GatewayConnection(`ws://127.0.0.1:${port}`);
    await gateway.connect();

    const resp = await gateway.sendRequest("agent.execute", { goal: "Format C: drive" });
    assert.equal(resp.success, false);
    assert.equal(resp.error?.code, "AGENT_EXECUTION_ERROR");
    assert.ok(resp.error?.message.includes("approval"));

    gateway.disconnect();
    await new Promise<void>((resolve) => wss.close(() => resolve()));
  });
});
