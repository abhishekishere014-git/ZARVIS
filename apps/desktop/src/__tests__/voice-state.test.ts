import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { DesktopStore } from "../renderer/state/store.js";

describe("Desktop Voice State Machine & Barge-In", () => {
  it("should transition from IDLE to LISTENING (Tap) to THINKING to SPEAKING to IDLE", () => {
    const store = new DesktopStore();
    assert.equal(store.getState().assistantState, "IDLE");
    assert.equal(store.getState().voiceMode, null);

    // 1. Tap-to-speak activates listening
    store.setAssistantState("LISTENING", "tap");
    assert.equal(store.getState().assistantState, "LISTENING");
    assert.equal(store.getState().voiceMode, "tap");

    // 2. Transcription update
    store.setTranscription("Open Visual Studio Code");
    assert.equal(store.getState().transcription, "Open Visual Studio Code");

    // 3. User finishes speaking -> Thinking
    store.setAssistantState("THINKING");
    assert.equal(store.getState().assistantState, "THINKING");
    assert.equal(store.getState().voiceMode, null);

    // 4. TTS audio output begins -> Speaking
    store.setAssistantState("SPEAKING");
    store.setSpeakingText("Opening Visual Studio Code now.");
    assert.equal(store.getState().assistantState, "SPEAKING");
    assert.equal(store.getState().speakingText, "Opening Visual Studio Code now.");

    // 5. TTS finishes -> Return to IDLE
    store.setAssistantState("IDLE");
    assert.equal(store.getState().assistantState, "IDLE");
  });

  it("should support Hold-to-Speak (Push-to-Talk) mode", () => {
    const store = new DesktopStore();

    // Press and hold
    store.setAssistantState("LISTENING", "hold");
    assert.equal(store.getState().assistantState, "LISTENING");
    assert.equal(store.getState().voiceMode, "hold");

    // Release to send -> Thinking
    store.setAssistantState("THINKING");
    assert.equal(store.getState().assistantState, "THINKING");
    assert.equal(store.getState().voiceMode, null);
  });

  it("should support instant Barge-In when speaking", () => {
    const store = new DesktopStore();
    store.setAssistantState("SPEAKING");
    assert.equal(store.getState().assistantState, "SPEAKING");

    // User interrupts by tapping or speaking -> Barge-in cancels speech and immediately listens
    store.setAssistantState("LISTENING", "tap");
    assert.equal(store.getState().assistantState, "LISTENING");
    assert.equal(store.getState().voiceMode, "tap");
  });

  it("should handle error and offline states gracefully", () => {
    const store = new DesktopStore();
    store.setAssistantState("ERROR");
    assert.equal(store.getState().assistantState, "ERROR");

    store.setAssistantState("OFFLINE");
    assert.equal(store.getState().assistantState, "OFFLINE");
  });
});
