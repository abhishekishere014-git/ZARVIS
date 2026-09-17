import http from "node:http";
import net from "node:net";
import { WebSocket } from "ws";

console.log("=== TRUTHFULNESS & RELIABILITY VERIFICATION SUITE ===");

async function main() {
  console.log("\n[TEST 1] Testing Gateway truthful offline reporting when Python Core is down...");
  
  const { NodeGateway } = await import("../services/node-gateway/dist/gateway.js");
  const { loadConfig } = await import("../services/node-gateway/dist/config.js");

  const testPort = 3911;
  const config = loadConfig({
    GATEWAY_HOST: "127.0.0.1",
    GATEWAY_PORT: String(testPort),
    GATEWAY_LOG_LEVEL: "error",
    NODE_ENV: "test",
    IPC_PORT: "8765",
  });

  const gw = new NodeGateway(config);
  await gw.start();
  console.log("  Node Gateway started on port", testPort);

  const ws = new WebSocket(`ws://127.0.0.1:${testPort}/ws`);
  const receivedMessages = [];
  ws.on("message", (data) => {
    try {
      receivedMessages.push(JSON.parse(data.toString()));
    } catch {}
  });

  await new Promise((res, rej) => {
    ws.on("open", res);
    ws.on("error", rej);
  });
  console.log("  Connected to Gateway WebSocket.");

  // Wait 100ms for connection handshake broadcast
  await new Promise((r) => setTimeout(r, 200));

  const initialHealth = receivedMessages.find((m) => m.type === "system.health");
  if (initialHealth) {
    console.log("  [VERIFIED] Initial connection health broadcast received:");
    console.log("    Core:", initialHealth.payload?.core);
    console.log("    Gateway:", initialHealth.payload?.gateway);
    console.log("    IPC:", initialHealth.payload?.ipc);

    if (initialHealth.payload.core !== "offline" || initialHealth.payload.ipc !== "disconnected") {
      throw new Error("FAILED: Gateway falsely reported core or IPC as active when offline!");
    }
  }

  // Request system.health explicitly
  const healthResp = await new Promise((res, rej) => {
    const timer = setTimeout(() => rej(new Error("Timeout waiting for system.health response")), 3000);
    const handler = (data) => {
      try {
        const parsed = JSON.parse(data.toString());
        if (parsed.id === "req_health_audit") {
          clearTimeout(timer);
          ws.removeListener("message", handler);
          res(parsed);
        }
      } catch {}
    };
    ws.on("message", handler);
    ws.send(JSON.stringify({
      id: "req_health_audit",
      type: "system.health",
      version: "1.0",
      timestamp: new Date().toISOString(),
      payload: {},
    }));
  });

  console.log("  [VERIFIED] Explicit system.health RPC response:");
  console.log("    Core:", healthResp.payload.core);
  console.log("    Gateway:", healthResp.payload.gateway);
  console.log("    IPC:", healthResp.payload.ipc);
  console.log("    Voice:", healthResp.payload.voice);
  console.log("    Vision:", healthResp.payload.vision);

  if (healthResp.payload.core !== "offline" || healthResp.payload.voice !== "unavailable") {
    throw new Error("FAILED: Gateway system.health falsely reported ready when offline!");
  }

  // Execute agent task when offline
  const agentResp = await new Promise((res, rej) => {
    const timer = setTimeout(() => rej(new Error("Timeout waiting for agent.execute response")), 3000);
    const handler = (data) => {
      try {
        const parsed = JSON.parse(data.toString());
        if (parsed.id === "req_agent_audit") {
          clearTimeout(timer);
          ws.removeListener("message", handler);
          res(parsed);
        }
      } catch {}
    };
    ws.on("message", handler);
    ws.send(JSON.stringify({
      id: "req_agent_audit",
      type: "agent.execute",
      version: "1.0",
      timestamp: new Date().toISOString(),
      payload: { goal: "Open youtube and play lofi" },
    }));
  });

  console.log("  [VERIFIED] Execution failure response when offline:");
  console.log("    Success:", agentResp.success);
  console.log("    Error Code:", agentResp.error?.code);
  console.log("    Error Message:", agentResp.error?.message);

  if (agentResp.success !== false || agentResp.error?.code !== "CORE_OFFLINE") {
    throw new Error("FAILED: Gateway did not return honest CORE_OFFLINE error!");
  }

  ws.close();
  await gw.stop();
  console.log("  [PASS] Test 1 passed: Zero fake success, zero fake health when Core is offline.");

  console.log("\n=======================================================");
  console.log("ALL TRUTHFULNESS & RELIABILITY AUDIT CHECKS PASSED!");
  console.log("=======================================================");
  process.exit(0);
}

main().catch((err) => {
  console.error("\nFATAL VERIFICATION FAILURE:", err);
  process.exit(1);
});
