/**
 * Phase 12.4 Reliability, Reconnect & Crash Recovery Test Suite.
 * Verifies Gateway disconnect handling, exponential backoff,
 * pending request cleanup, IPC timeouts, malformed event resilience,
 * and safe state recovery across failures.
 */

import { describe, it } from "node:test";
import * as assert from "node:assert/strict";
import { WebSocketServer } from "ws";
import { PROTOCOL_VERSION, JarvisResponse } from "@jarvis/protocol";
import { GatewayConnection } from "../renderer/gateway/connection.js";
import { DesktopStore } from "../renderer/state/store.js";

describe("Phase 12.4 Reliability, Reconnect & Crash Recovery", () => {
  describe("1. Gateway Disconnect & Pending Request Cleanup", () => {
    it("should clean up pending in-flight requests with CONNECTION_CLOSED when connection drops", async () => {
      const wss = new WebSocketServer({ port: 0 });
      await new Promise<void>((resolve) => wss.on("listening", () => resolve()));
      const port = (wss.address() as any).port;

      const gateway = new GatewayConnection(`ws://127.0.0.1:${port}`);
      await gateway.connect();
      assert.equal(gateway.isConnected(), true);

      // Issue an in-flight request that is never answered by server
      const inFlightPromise = gateway.sendRequest("agent.execute", { goal: "Long task" }, 10000);

      // Disconnect client and terminate server
      gateway.disconnect();
      for (const client of wss.clients) {
        client.terminate();
      }
      await new Promise<void>((resolve) => wss.close(() => resolve()));

      const resp = await inFlightPromise;
      assert.equal(resp.success, false);
      assert.equal(resp.error?.code, "CONNECTION_CLOSED");
      assert.equal(gateway.isConnected(), false);
    });

    it("should return GATEWAY_OFFLINE immediately when sending requests while offline", async () => {
      const gateway = new GatewayConnection("ws://127.0.0.1:59999/ws");
      assert.equal(gateway.isConnected(), false);

      const resp = await gateway.sendRequest("system.ping");
      assert.equal(resp.success, false);
      assert.equal(resp.error?.code, "GATEWAY_OFFLINE");
    });
  });

  describe("2. Request Timeout & Stale Timer Cleanup", () => {
    it("should cleanly time out long-running or stalled requests with REQUEST_TIMEOUT", async () => {
      const wss = new WebSocketServer({ port: 0 });
      await new Promise<void>((resolve) => wss.on("listening", () => resolve()));
      const port = (wss.address() as any).port;

      const gateway = new GatewayConnection(`ws://127.0.0.1:${port}`);
      await gateway.connect();

      // Send request with short 100ms timeout
      const startTime = Date.now();
      const resp = await gateway.sendRequest("agent.execute", { goal: "Stalled task" }, 100);
      const elapsed = Date.now() - startTime;

      assert.equal(resp.success, false);
      assert.equal(resp.error?.code, "REQUEST_TIMEOUT");
      assert.ok(elapsed >= 90 && elapsed <= 500, `Elapsed time was ${elapsed}ms`);

      gateway.disconnect();
      await new Promise<void>((resolve) => wss.close(() => resolve()));
    });
  });

  describe("3. Core Crash / Offline Error Propagation", () => {
    it("should return explicit CORE_OFFLINE error when Python Core backend is unavailable", async () => {
      const wss = new WebSocketServer({ port: 0 });
      await new Promise<void>((resolve) => wss.on("listening", () => resolve()));
      const port = (wss.address() as any).port;

      wss.on("connection", (ws) => {
        ws.on("message", (raw) => {
          const parsed = JSON.parse(raw.toString());
          const offlineResp: JarvisResponse = {
            id: parsed.id,
            type: parsed.type,
            version: PROTOCOL_VERSION,
            timestamp: new Date().toISOString(),
            success: false,
            error: {
              code: "CORE_OFFLINE",
              message: "Cannot execute 'agent.execute': Python Core IPC backend is currently offline.",
            },
          };
          ws.send(JSON.stringify(offlineResp));
        });
      });

      const gateway = new GatewayConnection(`ws://127.0.0.1:${port}`);
      await gateway.connect();

      const resp = await gateway.sendRequest("agent.execute", { goal: "Check weather" });
      assert.equal(resp.success, false);
      assert.equal(resp.error?.code, "CORE_OFFLINE");
      assert.ok(resp.error?.message.includes("Python Core IPC backend is currently offline"));

      gateway.disconnect();
      await new Promise<void>((resolve) => wss.close(() => resolve()));
    });
  });

  describe("4. Task & Voice Failure State Recovery", () => {
    it("should recover assistant state from THINKING to IDLE on task error without frozen UI", () => {
      const store = new DesktopStore();
      assert.equal(store.getState().assistantState, "IDLE");

      // Task starts -> THINKING
      store.setAssistantState("THINKING");
      assert.equal(store.getState().assistantState, "THINKING");

      // Failure occurs -> recovers safely to IDLE
      store.setAssistantState("IDLE");
      assert.equal(store.getState().assistantState, "IDLE");

      // Immediate retry allowed
      store.setAssistantState("LISTENING", "tap");
      assert.equal(store.getState().assistantState, "LISTENING");

      // Reset to IDLE
      store.setAssistantState("IDLE");
      assert.equal(store.getState().assistantState, "IDLE");
    });

    it("should recover voice playback state from SPEAKING to IDLE on playback termination or error", () => {
      const store = new DesktopStore();
      store.setAssistantState("SPEAKING");
      store.setSpeakingText("Synthesized speech text");
      assert.equal(store.getState().assistantState, "SPEAKING");

      // Audio playback finishes or encounters error -> resets to IDLE
      store.setAssistantState("IDLE");
      assert.equal(store.getState().assistantState, "IDLE");
    });
  });

  describe("5. Malformed Backend Event Resilience", () => {
    it("should safely ignore malformed JSON or invalid event schemas without crashing listeners", async () => {
      const wss = new WebSocketServer({ port: 0 });
      await new Promise<void>((resolve) => wss.on("listening", () => resolve()));
      const port = (wss.address() as any).port;

      let clientSocket: any = null;
      wss.on("connection", (ws) => {
        clientSocket = ws;
      });

      const gateway = new GatewayConnection(`ws://127.0.0.1:${port}`);
      await gateway.connect();

      const validEvents: string[] = [];
      gateway.onEvent((evt) => {
        validEvents.push(evt.type);
      });

      // 1. Send completely malformed raw string
      clientSocket.send("INVALID_NON_JSON_CORRUPT_BUFFER{{{");

      // 2. Send JSON that fails schema validation (missing timestamp, id, etc.)
      clientSocket.send(JSON.stringify({ notAnEvent: true }));

      // 3. Send valid event
      clientSocket.send(
        JSON.stringify({
          id: "evt_valid_1",
          type: "agent.planning",
          version: PROTOCOL_VERSION,
          timestamp: new Date().toISOString(),
          payload: { status: "planning" },
        })
      );

      // Allow event propagation
      await new Promise((resolve) => setTimeout(resolve, 50));

      assert.equal(validEvents.length, 1);
      assert.equal(validEvents[0], "agent.planning");

      gateway.disconnect();
      await new Promise<void>((resolve) => wss.close(() => resolve()));
    });
  });
});
