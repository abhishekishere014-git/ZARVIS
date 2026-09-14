import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { loadConfig } from "../config.js";

describe("Node Gateway Configuration", () => {
  it("should load default loopback configuration", () => {
    const config = loadConfig({});
    assert.equal(config.host, "127.0.0.1");
    assert.equal(config.port, 3000);
    assert.equal(config.nodeEnv, "development");
  });

  it("should accept valid environment variable overrides", () => {
    const customEnv: NodeJS.ProcessEnv = {
      GATEWAY_HOST: "localhost",
      GATEWAY_PORT: "4000",
      GATEWAY_LOG_LEVEL: "debug",
      NODE_ENV: "production",
    };

    const config = loadConfig(customEnv);
    assert.equal(config.host, "localhost");
    assert.equal(config.port, 4000);
    assert.equal(config.logLevel, "debug");
    assert.equal(config.nodeEnv, "production");
  });

  it("should reject unsafe non-loopback network bindings (e.g. 0.0.0.0)", () => {
    const unsafeEnv: NodeJS.ProcessEnv = {
      GATEWAY_HOST: "0.0.0.0", // Forbidden public binding
    };

    assert.throws(
      () => loadConfig(unsafeEnv),
      /Security violation: Gateway must strictly bind to loopback/
    );
  });
});
