import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { DesktopStore } from "../renderer/state/store.js";

describe("Desktop Window Lifecycle & Mode Switching", () => {
  it("should switch seamlessly between Full Workspace and Compact HUD", () => {
    const store = new DesktopStore();
    assert.equal(store.getState().windowMode, "full");

    // Switch to Compact Floating HUD
    store.setWindowMode("hud");
    assert.equal(store.getState().windowMode, "hud");

    // Switch back to Full Workspace
    store.setWindowMode("full");
    assert.equal(store.getState().windowMode, "full");
  });

  it("should toggle pin / always-on-top state", () => {
    const store = new DesktopStore();
    assert.equal(store.getState().isPinned, false);

    store.setPinned(true);
    assert.equal(store.getState().isPinned, true);

    store.setPinned(false);
    assert.equal(store.getState().isPinned, false);
  });

  it("should maintain real telemetry status across lifecycle transitions", () => {
    const store = new DesktopStore();
    const tel = store.getState().telemetry;
    assert.equal(tel.core, "offline");
    assert.equal(tel.gateway, "offline");
    assert.equal(tel.ipc, "disconnected");

    store.setTelemetry({ core: "healthy", gateway: "healthy", ipc: "connected" });
    assert.equal(store.getState().telemetry.core, "healthy");
    assert.equal(store.getState().telemetry.gateway, "healthy");
    assert.equal(store.getState().telemetry.ipc, "connected");

    store.setWindowMode("hud");
    assert.equal(store.getState().telemetry.core, "healthy");

    store.setTelemetry({ gateway: "degraded", ipc: "disconnected" });
    assert.equal(store.getState().telemetry.gateway, "degraded");
    assert.equal(store.getState().telemetry.ipc, "disconnected");
  });
});
