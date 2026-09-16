import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  PROTOCOL_VERSION,
  validateRequest,
  validateResponse,
  validateEvent,
  parseRequest,
  parseResponse,
  parseEvent,
} from "../index.js";

describe("JARVIS Protocol Specification (v1.0)", () => {
  it("should validate a conforming request", () => {
    const validRequest = {
      id: "req-123",
      type: "system.health",
      version: PROTOCOL_VERSION,
      timestamp: new Date().toISOString(),
      payload: { component: "core" },
    };

    const result = validateRequest(validRequest);
    assert.equal(result.valid, true);
    assert.deepEqual(result.data?.id, "req-123");
  });

  it("should reject a request with unsupported protocol version", () => {
    const invalidRequest = {
      id: "req-124",
      type: "system.health",
      version: "99.0", // Unsupported
      timestamp: new Date().toISOString(),
      payload: {},
    };

    const result = validateRequest(invalidRequest);
    assert.equal(result.valid, false);
    assert.match(result.error ?? "", /Invalid literal value/);
  });

  it("should validate a conforming successful response", () => {
    const validResponse = {
      id: "res-123",
      type: "system.health",
      version: PROTOCOL_VERSION,
      timestamp: new Date().toISOString(),
      success: true,
      payload: { status: "healthy" },
    };

    const result = validateResponse(validResponse);
    assert.equal(result.valid, true);
    assert.equal(result.data?.success, true);
  });

  it("should validate a conforming successful response with null error (Python Core format)", () => {
    const validResponseWithNullError = {
      id: "res-123-null",
      type: "system.health",
      version: PROTOCOL_VERSION,
      timestamp: new Date().toISOString(),
      success: true,
      payload: { status: "healthy" },
      error: null,
    };

    const result = validateResponse(validResponseWithNullError);
    assert.equal(result.valid, true);
    assert.equal(result.data?.success, true);
  });

  it("should validate a conforming error response", () => {
    const errorResponse = {
      id: "res-124",
      type: "service.start",
      version: PROTOCOL_VERSION,
      timestamp: new Date().toISOString(),
      success: false,
      error: {
        code: "SERVICE_INITIALIZATION_FAILED",
        message: "Port already in use",
        details: { port: 8765 },
      },
    };

    const result = validateResponse(errorResponse);
    assert.equal(result.valid, true);
    assert.equal(result.data?.success, false);
    assert.equal(result.data?.error?.code, "SERVICE_INITIALIZATION_FAILED");
  });

  it("should reject an error response that claims success=false but omits error", () => {
    const malformedResponse = {
      id: "res-125",
      type: "service.start",
      version: PROTOCOL_VERSION,
      timestamp: new Date().toISOString(),
      success: false,
      // Missing required error object
    };

    const result = validateResponse(malformedResponse);
    assert.equal(result.valid, false);
  });

  it("should validate a conforming event", () => {
    const validEvent = {
      id: "evt-001",
      type: "service.state_changed",
      version: PROTOCOL_VERSION,
      timestamp: new Date().toISOString(),
      correlation_id: "req-123",
      payload: { service: "voice", state: "listening" },
    };

    const result = validateEvent(validEvent);
    assert.equal(result.valid, true);
    assert.equal(result.data?.correlation_id, "req-123");
  });

  it("should reject a message with non-ISO8601 timestamp", () => {
    const badTimestampRequest = {
      id: "req-126",
      type: "system.ping",
      version: PROTOCOL_VERSION,
      timestamp: "yesterday afternoon",
      payload: {},
    };

    const result = validateRequest(badTimestampRequest);
    assert.equal(result.valid, false);
  });
});
