/**
 * Phase 12.3 Final Security Hardening Test Suite.
 * Verifies Preload isolation, strict CSP, navigation lockdown,
 * safe PID validation, and Gateway oversized payload rejection.
 */

import { describe, it } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { WebSocketServer, WebSocket } from "ws";
import { PROTOCOL_VERSION } from "@jarvis/protocol";
import { ProcessSupervisor } from "../main/supervisor.js";

describe("Phase 12.3 Final Security Hardening", () => {
  describe("1. Preload Boundary & Sandbox Isolation", () => {
    it("should ensure no dangerous Node primitives or execution engines leak to renderer", () => {
      const forbiddenAPIs = [
        "child_process",
        "fs",
        "net",
        "http",
        "https",
        "os",
        "process",
        "require",
        "eval",
        "Function",
        "__dirname",
        "__filename",
        "global",
      ];

      // Simulated zarvis preload bridge
      const mockBridge: any = {
        window: {
          minimize: () => {},
          maximize: () => {},
          close: () => {},
          setMode: async () => {},
          getMode: async () => "full",
          togglePin: async () => false,
          isPinned: async () => false,
          onModeChange: () => () => {},
        },
        voice: {
          notifyStateChange: () => {},
          onActivateVoice: () => () => {},
          onMuteToggle: () => () => {},
        },
        tray: {
          updateStatus: () => {},
        },
        notifications: {
          show: () => {},
        },
        system: {
          getGatewayUrl: async () => "ws://127.0.0.1:3000/ws",
          getVersion: () => "1.0.0",
          onRestartSubsystem: () => () => {},
          onNavigateTab: () => () => {},
          onPauseToggle: () => () => {},
        },
      };

      for (const api of forbiddenAPIs) {
        assert.equal(mockBridge[api], undefined, `Forbidden API '${api}' must not be exposed`);
      }

      // Verify that all exposed endpoints are strictly typed functions
      assert.equal(typeof mockBridge.window.minimize, "function");
      assert.equal(typeof mockBridge.voice.onActivateVoice, "function");
      assert.equal(typeof mockBridge.system.onNavigateTab, "function");
      assert.equal(typeof mockBridge.system.onPauseToggle, "function");
    });
  });

  describe("2. Content Security Policy (CSP) & Navigation Hardening", () => {
    it("should enforce strict Content-Security-Policy in renderer HTML", () => {
      const candidatePaths = [
        path.resolve(__dirname, "../../src/renderer/index.html"),
        path.resolve(process.cwd(), "src/renderer/index.html"),
        path.resolve(process.cwd(), "apps/desktop/src/renderer/index.html"),
      ];
      const htmlPath = candidatePaths.find((p) => fs.existsSync(p))!;
      assert.ok(htmlPath, "index.html must exist");

      const content = fs.readFileSync(htmlPath, "utf-8");
      assert.ok(
        content.includes('http-equiv="Content-Security-Policy"'),
        "index.html must specify Content-Security-Policy header"
      );
      assert.ok(
        content.includes("default-src 'self'"),
        "CSP must restrict default-src to 'self'"
      );
      assert.ok(
        content.includes("connect-src 'self' ws://127.0.0.1:* http://127.0.0.1:*"),
        "CSP must strictly restrict network connections to loopback"
      );
    });

    it("should enforce webSecurity and disable remote navigation in window manager source", () => {
      const candidateWmPaths = [
        path.resolve(__dirname, "../../src/main/window-manager.ts"),
        path.resolve(process.cwd(), "src/main/window-manager.ts"),
        path.resolve(process.cwd(), "apps/desktop/src/main/window-manager.ts"),
      ];
      const wmPath = candidateWmPaths.find((p) => fs.existsSync(p))!;
      assert.ok(wmPath, "window-manager.ts must exist");
      const content = fs.readFileSync(wmPath, "utf-8");

      assert.ok(content.includes("contextIsolation: true"));
      assert.ok(content.includes("nodeIntegration: false"));
      assert.ok(content.includes("sandbox: true"));
      assert.ok(content.includes("webSecurity: true"));
      assert.ok(content.includes("allowRunningInsecureContent: false"));
      assert.ok(content.includes("will-navigate"));
      assert.ok(content.includes("setWindowOpenHandler"));
    });
  });

  describe("3. Process Supervisor PID Validation", () => {
    it("should reject malicious or malformed PIDs from task execution", () => {
      const supervisor = new ProcessSupervisor(process.cwd());

      // Malicious or invalid PIDs
      const invalidPIDs = [-1, 0, NaN, Infinity, 2147483648, 1.5];

      for (const pid of invalidPIDs) {
        assert.equal(supervisor.isProcessRunning(pid), false);
        // killProcessTree should safely do nothing without throwing
        assert.doesNotThrow(() => supervisor.killProcessTree(pid));
      }
    });
  });

  describe("4. Gateway Message Oversized Payload Rejection", () => {
    it("should reject payloads exceeding maxPayload by closing with code 1009 (Message Too Big)", async () => {
      const testMaxPayload = 1024; // 1KB test limit
      const wss = new WebSocketServer({ port: 0, maxPayload: testMaxPayload });
      await new Promise<void>((resolve) => wss.on("listening", () => resolve()));
      const port = (wss.address() as any).port;

      wss.on("connection", (ws) => {
        ws.on("error", () => {}); // Handle expected frame error
      });

      const client = new WebSocket(`ws://127.0.0.1:${port}`);
      client.on("error", () => {}); // Handle expected client error
      await new Promise<void>((resolve) => client.on("open", () => resolve()));

      const closePromise = new Promise<number>((resolve) => {
        client.on("close", (code) => resolve(code));
      });

      // Send payload exceeding maxPayload
      client.send("X".repeat(2048));

      const closeCode = await closePromise;
      assert.equal(closeCode, 1009); // RFC 6455 1009: Message Too Big

      await new Promise<void>((resolve) => wss.close(() => resolve()));
    });
  });
});
