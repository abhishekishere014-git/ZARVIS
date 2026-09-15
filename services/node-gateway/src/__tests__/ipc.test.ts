import { describe, it } from "node:test";
import assert from "node:assert/strict";
import net from "node:net";
import { MessageBuffer } from "../ipc/framing.js";
import { IPCClient } from "../ipc/client.js";
import { PROTOCOL_VERSION, JarvisRequest, JarvisResponse, JarvisEvent } from "@jarvis/protocol";
import { Logger } from "../logger.js";

const testLogger = new Logger("test.ipc", "error");

describe("Phase 10 Node Gateway IPC Subsystem", () => {
  describe("MessageBuffer Framing", () => {
    it("should extract single and multiple frames delimited by newline", () => {
      const buffer = new MessageBuffer(1024);
      const frames = buffer.push('{"id":"1"}\n{"id":"2"}\n');
      assert.equal(frames.length, 2);
      assert.equal(frames[0], '{"id":"1"}');
      assert.equal(frames[1], '{"id":"2"}');
    });

    it("should handle partial chunk buffering across multiple pushes", () => {
      const buffer = new MessageBuffer(1024);
      const frames1 = buffer.push('{"id":');
      assert.equal(frames1.length, 0);

      const frames2 = buffer.push('"partial"}\n');
      assert.equal(frames2.length, 1);
      assert.equal(frames2[0], '{"id":"partial"}');
    });

    it("should throw when exceeding maximum frame limit", () => {
      const buffer = new MessageBuffer(50);
      assert.throws(() => {
        buffer.push("A".repeat(60));
      }, /exceeded maximum limit/);
    });

    it("should correctly format JSON messages with newline delimiter", () => {
      const frame = MessageBuffer.formatFrame({ ping: true });
      assert.equal(frame, '{"ping":true}\n');
    });
  });

  describe("IPCClient Lifecycle & Communication", () => {
    it("should fail gracefully when sending request while disconnected", async () => {
      const client = new IPCClient({ host: "127.0.0.1", port: 9999 }, testLogger);
      assert.equal(client.isConnected(), false);
      assert.equal(client.getState(), "DISCONNECTED");

      const req: JarvisRequest = {
        id: "req_disc",
        type: "system.ping",
        version: PROTOCOL_VERSION,
        timestamp: new Date().toISOString(),
        payload: {},
      };

      const resp = await client.sendRequest(req);
      assert.equal(resp.id, "req_disc");
      assert.equal(resp.success, false);
      assert.equal(resp.error?.code, "IPC_NOT_CONNECTED");
    });

    it("should connect, perform handshake, exchange requests, receive events, and disconnect cleanly", async () => {
      let serverSocket: net.Socket | null = null;
      const receivedRequests: any[] = [];

      // Start mock TCP server
      const mockServer = net.createServer((socket) => {
        serverSocket = socket;
        let buf = "";

        socket.on("data", (chunk) => {
          buf += chunk.toString("utf-8");
          let newlineIdx: number;
          while ((newlineIdx = buf.indexOf("\n")) !== -1) {
            const raw = buf.slice(0, newlineIdx).trim();
            buf = buf.slice(newlineIdx + 1);
            if (!raw) continue;

            const parsed = JSON.parse(raw);
            receivedRequests.push(parsed);

            if (parsed.type === "ipc.handshake") {
              const resp: JarvisResponse = {
                id: parsed.id,
                type: "ipc.handshake",
                version: PROTOCOL_VERSION,
                timestamp: new Date().toISOString(),
                success: true,
                payload: { session_id: "mock_sess_123" },
              };
              socket.write(JSON.stringify(resp) + "\n");
            } else if (parsed.type === "math.multiply") {
              const resp: JarvisResponse = {
                id: parsed.id,
                type: parsed.type,
                version: PROTOCOL_VERSION,
                timestamp: new Date().toISOString(),
                success: true,
                payload: { product: parsed.payload.a * parsed.payload.b },
              };
              socket.write(JSON.stringify(resp) + "\n");
            }
          }
        });
      });

      // Listen on dynamic ephemeral port
      await new Promise<void>((resolve) => {
        mockServer.listen(0, "127.0.0.1", () => resolve());
      });

      const port = (mockServer.address() as net.AddressInfo).port;
      const client = new IPCClient(
        {
          host: "127.0.0.1",
          port,
          timeoutMs: 2000,
          heartbeatIntervalMs: 60000, // disable frequent heartbeat during test
        },
        testLogger
      );

      const stateChanges: string[] = [];
      client.onStateChange((state) => stateChanges.push(state));

      // Connect and handshake
      await client.connect();
      assert.equal(client.isConnected(), true);
      assert.equal(client.getState(), "CONNECTED");
      assert.ok(stateChanges.includes("CONNECTING"));
      assert.ok(stateChanges.includes("CONNECTED"));

      // Send math request
      const req: JarvisRequest = {
        id: "calc_1",
        type: "math.multiply",
        version: PROTOCOL_VERSION,
        timestamp: new Date().toISOString(),
        payload: { a: 6, b: 7 },
      };

      const resp = await client.sendRequest(req);
      assert.equal(resp.id, "calc_1");
      assert.equal(resp.success, true);
      assert.equal(resp.payload?.product, 42);

      // Verify event reception
      const receivedEvents: JarvisEvent[] = [];
      client.onEvent((ev) => receivedEvents.push(ev));

      const eventToSend: JarvisEvent = {
        id: "ev_node_1",
        type: "system.alert",
        version: PROTOCOL_VERSION,
        timestamp: new Date().toISOString(),
        payload: { text: "hello gateway" },
      };

      serverSocket!.write(JSON.stringify(eventToSend) + "\n");

      // Wait a moment for event delivery
      await new Promise((r) => setTimeout(r, 50));
      assert.equal(receivedEvents.length, 1);
      assert.equal(receivedEvents[0].id, "ev_node_1");
      assert.equal(receivedEvents[0].type, "system.alert");
      assert.equal(receivedEvents[0].payload.text, "hello gateway");

      // Clean disconnect
      await client.disconnect();
      assert.equal(client.isConnected(), false);
      assert.equal(client.getState(), "STOPPED");

      // Close mock server
      await new Promise<void>((resolve) => {
        mockServer.close(() => resolve());
      });
    });

    it("should handle request timeout when server fails to respond", async () => {
      const mockServer = net.createServer((socket) => {
        socket.on("data", (chunk) => {
          const raw = chunk.toString("utf-8").trim();
          const parsed = JSON.parse(raw);
          if (parsed.type === "ipc.handshake") {
            const resp: JarvisResponse = {
              id: parsed.id,
              type: "ipc.handshake",
              version: PROTOCOL_VERSION,
              timestamp: new Date().toISOString(),
              success: true,
              payload: {},
            };
            socket.write(JSON.stringify(resp) + "\n");
          }
          // Do NOT respond to any other request to trigger timeout
        });
      });

      await new Promise<void>((resolve) => {
        mockServer.listen(0, "127.0.0.1", () => resolve());
      });

      const port = (mockServer.address() as net.AddressInfo).port;
      const client = new IPCClient(
        {
          host: "127.0.0.1",
          port,
          timeoutMs: 150, // Short timeout for test
          heartbeatIntervalMs: 60000,
        },
        testLogger
      );

      await client.connect();

      const slowReq: JarvisRequest = {
        id: "slow_req",
        type: "slow.operation",
        version: PROTOCOL_VERSION,
        timestamp: new Date().toISOString(),
        payload: {},
      };

      const resp = await client.sendRequest(slowReq, 100);
      assert.equal(resp.id, "slow_req");
      assert.equal(resp.success, false);
      assert.equal(resp.error?.code, "REQUEST_TIMEOUT");

      await client.disconnect();
      await new Promise<void>((resolve) => {
        mockServer.close(() => resolve());
      });
    });
  });
});
