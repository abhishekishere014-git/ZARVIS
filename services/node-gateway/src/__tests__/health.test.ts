import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { HealthMonitor } from "../health.js";

describe("Node Gateway Health Monitor", () => {
  it("should report unhealthy when gateway is stopped", () => {
    const monitor = new HealthMonitor();
    monitor.setGatewayRunning(false);

    const report = monitor.getReport();
    assert.equal(report.status, "unhealthy");
    assert.equal(report.components.gateway.status, "unhealthy");
  });

  it("should report degraded when gateway runs but Python Core is disconnected", () => {
    const monitor = new HealthMonitor();
    monitor.setGatewayRunning(true);
    monitor.setPythonCoreConnected(false);

    const report = monitor.getReport();
    assert.equal(report.status, "degraded");
    assert.equal(report.components.gateway.status, "healthy");
    assert.equal(report.components.pythonCore.status, "degraded");
  });

  it("should report healthy when all components are active", () => {
    const monitor = new HealthMonitor();
    monitor.setGatewayRunning(true);
    monitor.setPythonCoreConnected(true);

    const report = monitor.getReport();
    assert.equal(report.status, "healthy");
    assert.equal(report.components.gateway.status, "healthy");
    assert.equal(report.components.pythonCore.status, "healthy");
  });
});
