/**
 * ZARVIS Desktop Main Renderer Application.
 * Binds Gateway WebSocket Connection, Reactive Store, and DOM Interactions.
 */

import { GatewayConnection } from "./gateway/connection";
import { DesktopStore, MessageItem, ActivityFeedItem, AssistantState } from "./state/store";

export class ZarvisApp {
  private readonly store: DesktopStore;
  private readonly gateway: GatewayConnection;
  private holdTimer: any = null;
  private isHolding = false;
  private mediaRecorder: any = null;
  private audioChunks: Blob[] = [];
  private mediaStream: any = null;
  private activeAudioSource: any = null;
  private audioContext: any = null;

  constructor() {
    this.store = new DesktopStore();
    this.gateway = new GatewayConnection();
  }

  public async init(): Promise<void> {
    this.setupStoreListeners();
    this.setupDomEvents();
    this.setupPreloadBridge();
    this.setupGatewayListeners();

    // Connect to Node Gateway
    try {
      await this.gateway.connect();
      this.refreshSystemHealth();
    } catch {
      this.store.setAssistantState("OFFLINE");
      this.store.setTelemetry({ gateway: "offline", core: "offline", ipc: "disconnected" });
    }
  }

  private setupStoreListeners(): void {
    this.store.subscribe((state) => {
      this.renderState(state);
    });
  }

  private setupDomEvents(): void {
    // Navigation Tabs
    const tabs = ["home", "chat", "agents", "memory", "settings", "activity"];
    tabs.forEach((tab) => {
      document.getElementById(`nav-${tab}`)?.addEventListener("click", () => {
        this.switchTab(tab);
      });
    });

    // Hero Voice Button (Tap & Hold)
    const micBtn = document.getElementById("hero-voice-btn");
    const hudMicBtn = document.getElementById("hud-mic-btn");

    [micBtn, hudMicBtn].forEach((btn) => {
      if (!btn) return;

      btn.addEventListener("click", () => {
        if (!this.isHolding) {
          this.handleMicTap();
        }
      });

      btn.addEventListener("mousedown", () => {
        this.holdTimer = setTimeout(() => {
          this.isHolding = true;
          this.handleMicHoldStart();
        }, 220);
      });

      btn.addEventListener("mouseup", () => {
        if (this.holdTimer) clearTimeout(this.holdTimer);
        if (this.isHolding) {
          this.isHolding = false;
          this.handleMicHoldEnd();
        }
      });

      btn.addEventListener("mouseleave", () => {
        if (this.holdTimer) clearTimeout(this.holdTimer);
        if (this.isHolding) {
          this.isHolding = false;
          this.handleMicHoldEnd();
        }
      });
    });

    // Text Command Input
    const cmdInput = document.getElementById("cmd-input") as HTMLInputElement;
    const sendBtn = document.getElementById("btn-send-cmd");

    const onSend = () => {
      if (!cmdInput || !cmdInput.value.trim()) return;
      this.submitCommand(cmdInput.value.trim());
      cmdInput.value = "";
    };

    sendBtn?.addEventListener("click", onSend);
    cmdInput?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        onSend();
      }
    });

    // Quick Actions
    document.getElementById("qa-code")?.addEventListener("click", () => {
      this.submitCommand("Open Visual Studio Code");
    });
    document.getElementById("qa-search")?.addEventListener("click", () => {
      this.submitCommand("Search the web for latest AI engineering news");
    });
    document.getElementById("qa-office")?.addEventListener("click", () => {
      this.submitCommand("Generate an executive project overview docx in workspace");
    });
    document.getElementById("qa-automation")?.addEventListener("click", () => {
      this.submitCommand("List active desktop windows and display geometry");
    });

    // Window controls
    document.getElementById("btn-switch-hud")?.addEventListener("click", () => {
      window.zarvis?.window.setMode("hud");
      this.setWindowMode("hud");
    });
    document.getElementById("hud-expand-btn")?.addEventListener("click", () => {
      window.zarvis?.window.setMode("full");
      this.setWindowMode("full");
    });
    document.getElementById("btn-pin-toggle")?.addEventListener("click", async () => {
      const isPinned = await window.zarvis?.window.togglePin();
      this.store.setPinned(!!isPinned);
    });
    document.getElementById("hud-pin-btn")?.addEventListener("click", async () => {
      const isPinned = await window.zarvis?.window.togglePin();
      this.store.setPinned(!!isPinned);
    });
    document.getElementById("btn-scan-screen")?.addEventListener("click", () => {
      this.triggerVisionScan();
    });
    document.getElementById("hud-vision-btn")?.addEventListener("click", () => {
      this.triggerVisionScan();
    });

    // In-App Desktop Window Controls (Minimize, Maximize / Restore, Close)
    document.getElementById("btn-window-minimize")?.addEventListener("click", () => {
      window.zarvis?.window.minimize();
    });
    document.getElementById("btn-window-maximize")?.addEventListener("click", async () => {
      if (window.zarvis?.window.toggleMaximize) {
        const isMax = await window.zarvis.window.toggleMaximize();
        this.updateMaximizeIcon(isMax);
      } else {
        window.zarvis?.window.maximize();
      }
    });
    document.getElementById("btn-window-close")?.addEventListener("click", () => {
      window.zarvis?.window.close();
    });

    // Titlebar Double-Click Toggle Maximize
    const titlebar = document.getElementById("titlebar-header");
    titlebar?.addEventListener("dblclick", async (e) => {
      if ((e.target as HTMLElement).closest("button, input, select, a")) return;
      if (window.zarvis?.window.toggleMaximize) {
        const isMax = await window.zarvis.window.toggleMaximize();
        this.updateMaximizeIcon(isMax);
      }
    });

    // Quick Suggestion Prompt Chips
    document.querySelectorAll(".prompt-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const cmd = chip.getAttribute("data-cmd");
        if (cmd) {
          this.submitCommand(cmd);
        }
      });
    });

    // Diagnostics Modal Controls
    document.getElementById("btn-diag-close")?.addEventListener("click", () => {
      document.getElementById("modal-diagnostics")?.classList.add("hidden");
    });
    document.getElementById("btn-diag-retry")?.addEventListener("click", async () => {
      document.getElementById("modal-diagnostics")?.classList.add("hidden");
      await this.init();
    });
    document.getElementById("btn-diag-copy")?.addEventListener("click", () => {
      const box = document.getElementById("diagnostic-details-box");
      if (box) {
        navigator.clipboard?.writeText(box.innerText);
        window.zarvis?.notifications.show("Diagnostics Copied", "Diagnostic report copied to clipboard", "info");
      }
    });
    document.getElementById("connection-text")?.addEventListener("click", () => {
      if (!this.gateway.isConnected()) {
        this.showDiagnosticsModal();
      }
    });
    document.getElementById("telemetry-summary-dot")?.addEventListener("click", () => {
      this.showDiagnosticsModal();
    });

    // Safety Modal
    document.getElementById("safety-modal-deny")?.addEventListener("click", () => {
      document.getElementById("modal-safety-approval")?.classList.add("hidden");
      this.store.setAssistantState("IDLE");
    });
    document.getElementById("safety-modal-approve")?.addEventListener("click", () => {
      document.getElementById("modal-safety-approval")?.classList.add("hidden");
      this.store.addActivity({
        id: `act_${Date.now()}`,
        title: "Action Approved by User",
        category: "system",
        description: "User confirmed high-risk automation permission",
        timestamp: new Date().toLocaleTimeString(),
      });
      this.store.setAssistantState("IDLE");
    });

    // Home View — New Quick Action Buttons
    document.getElementById("btn-view-all-activity")?.addEventListener("click", () => {
      this.switchTab("activity");
    });
    document.getElementById("qa-settings-action")?.addEventListener("click", () => {
      this.switchTab("settings");
    });
    document.getElementById("qa-activity-action")?.addEventListener("click", () => {
      this.switchTab("activity");
    });
    document.getElementById("qa-minimize-action")?.addEventListener("click", () => {
      window.zarvis?.window.minimize();
    });
  }

  private setupPreloadBridge(): void {
    if (!window.zarvis) return;

    window.zarvis.window.onModeChange((mode) => {
      this.setWindowMode(mode);
    });

    window.zarvis.window.onMaximizedChange?.((isMaximized) => {
      this.updateMaximizeIcon(isMaximized);
    });

    // Sync initial maximized state
    window.zarvis.window.isMaximized?.().then((isMax) => {
      this.updateMaximizeIcon(isMax);
    });

    window.zarvis.voice.onActivateVoice(() => {
      this.handleMicTap();
    });

    window.zarvis.voice.onMuteToggle?.(() => {
      this.handleMuteToggle();
    });

    window.zarvis.system.onRestartSubsystem?.((subsystem) => {
      this.handleRestartSubsystem(subsystem);
    });

    window.zarvis.system.onNavigateTab?.((tab) => {
      this.switchTab(tab);
    });

    window.zarvis.system.onPauseToggle?.((isPaused) => {
      this.handlePauseToggle(isPaused);
    });

    window.zarvis.system.onRuntimeError?.((errInfo) => {
      this.showDiagnosticsModal(errInfo);
    });

    window.zarvis.system.onSupervisorReady?.(() => {
      this.refreshSystemHealth();
    });
  }

  public handlePauseToggle(isPaused: boolean): void {
    if (isPaused) {
      this.stopSpeaking();
      this.stopListening();
      this.store.setAssistantState("IDLE");
      window.zarvis?.tray.updateStatus("Paused", "amber");
      window.zarvis?.notifications.show("ZARVIS Paused", "Assistant actions paused via tray", "info");
      this.store.addActivity({
        id: `act_${Date.now()}`,
        title: "Assistant Paused",
        category: "system",
        description: "Voice and autonomous tasks paused via system tray",
        timestamp: new Date().toLocaleTimeString(),
      });
    } else {
      window.zarvis?.tray.updateStatus("Ready", "green");
      window.zarvis?.notifications.show("ZARVIS Resumed", "Assistant actions active", "info");
      this.store.addActivity({
        id: `act_${Date.now()}`,
        title: "Assistant Resumed",
        category: "system",
        description: "Assistant active and ready",
        timestamp: new Date().toLocaleTimeString(),
      });
    }
  }

  private isMuted = false;

  public handleMuteToggle(): void {
    this.isMuted = !this.isMuted;
    const status = this.isMuted ? "Muted" : "Ready";
    window.zarvis?.tray.updateStatus(status, this.isMuted ? "amber" : "green");
    window.zarvis?.notifications.show(
      "Microphone",
      this.isMuted ? "Microphone muted" : "Microphone active",
      this.isMuted ? "warning" : "info"
    );
    this.store.addActivity({
      id: `act_${Date.now()}`,
      title: this.isMuted ? "Microphone Muted" : "Microphone Unmuted",
      category: "system",
      description: `Input capture set to ${this.isMuted ? "MUTED" : "ACTIVE"} via system tray`,
      timestamp: new Date().toLocaleTimeString(),
    });
  }

  public async handleRestartSubsystem(subsystem: string): Promise<void> {
    window.zarvis?.notifications.show(
      "Subsystem Refresh",
      `Refreshing connection to ${subsystem}...`,
      "info"
    );
    await this.refreshSystemHealth();
    this.store.addActivity({
      id: `act_${Date.now()}`,
      title: `Subsystem Refresh: ${subsystem}`,
      category: "system",
      description: `Re-pinged and verified health for ${subsystem}`,
      timestamp: new Date().toLocaleTimeString(),
    });
  }

  private setupGatewayListeners(): void {
    this.gateway.onStateChange((connected) => {
      if (connected) {
        this.store.setTelemetry({ gateway: "healthy" });
        this.refreshSystemHealth();
      } else {
        this.stopSpeakingPlaybackOnly();
        this.stopListening();
        this.store.setAssistantState("OFFLINE");
        this.store.setTelemetry({
          gateway: "offline",
          ipc: "disconnected",
          core: "offline",
          voice: "unavailable",
          vision: "unavailable",
          memory: "unavailable",
        });
      }
    });

    this.gateway.onEvent((event) => {
      try {
        if (!event || typeof event.type !== "string") return;
        const payload = (event.payload as Record<string, any>) || {};

        if (event.type === "system.health") {
          this.store.setTelemetry({
            gateway: payload.gateway ?? "healthy",
            core: payload.core ?? "offline",
            ipc: payload.ipc ?? "disconnected",
            voice: payload.voice ?? "unavailable",
            vision: payload.vision ?? "unavailable",
            memory: payload.memory ?? "unavailable",
          });
          if (payload.core === "healthy") {
            if (this.store.getState().assistantState === "OFFLINE") {
              this.store.setAssistantState("IDLE");
            }
          } else {
            this.store.setAssistantState("OFFLINE");
          }
          return;
        }

        if (event.type === "agent.planning") {
          this.store.addActivity({
            id: `act_${Date.now()}`,
            title: "Agent Planner",
            category: "agent",
            description: "Decomposing goal and generating execution DAG...",
            timestamp: new Date().toLocaleTimeString(),
          });
          this.store.updateAgent("Planner", { status: "working" });
        }

        if (event.type === "agent.task.started") {
          const agentName = String(payload.agent_id || "Agent");
          this.store.updateAgent(agentName, { status: "working" });
          this.store.addActivity({
            id: `act_${Date.now()}`,
            title: `Task Started: ${String(payload.task_id || "")}`,
            category: "agent",
            description: `Delegated to ${agentName}`,
            timestamp: new Date().toLocaleTimeString(),
          });
        }

        if (
          event.type.startsWith("agent.") &&
          event.type !== "agent.planning" &&
          event.type !== "agent.task.started" &&
          event.type !== "agent.completed" &&
          event.type !== "agent.failed"
        ) {
          const agentName = String(payload.agent || payload.agent_id || "Planner");
          this.store.updateAgent(agentName, {
            status: payload.status === "completed" ? "complete" : "working",
          });
        }

        if (event.type === "tool.executed") {
          this.store.addActivity({
            id: `act_${Date.now()}`,
            title: `Tool Executed: ${String(payload.tool || "tool")}`,
            category: "tool",
            description: String(payload.output || "Execution completed"),
            timestamp: new Date().toLocaleTimeString(),
          });
        }

        if (event.type === "agent.completed" || event.type === "agent.failed") {
          const isSuccess = event.type === "agent.completed" && (payload.status === "completed" || payload.status === undefined);
          this.store.addActivity({
            id: `act_${Date.now()}`,
            title: isSuccess ? "Agent Workflow Complete" : "Agent Workflow Failed",
            category: "agent",
            description: isSuccess
              ? (payload.summary ? String(payload.summary).slice(0, 100) : "All task waves verified and synthesized.")
              : (payload.error || payload.summary || "Agent execution failed."),
            timestamp: new Date().toLocaleTimeString(),
          });
        }
      } catch (evtErr) {
        console.warn("Failed to process event safely:", evtErr);
      }
    });
  }

  public handleMicTap(): void {
    const currentState = this.store.getState().assistantState;

    // Barge-in: if currently speaking, instantly cut off speech and start listening
    if (currentState === "SPEAKING") {
      this.stopSpeaking();
      this.startListening("tap");
      return;
    }

    if (currentState === "LISTENING") {
      this.stopListening();
    } else {
      this.startListening("tap");
    }
  }

  public handleMicHoldStart(): void {
    const currentState = this.store.getState().assistantState;
    if (currentState === "SPEAKING") {
      this.stopSpeaking();
    }
    this.startListening("hold");
  }

  public handleMicHoldEnd(): void {
    this.stopListening();
  }

  // ─── Web Speech API state ─────────────────────────────────────────────────
  private speechRecognizer: any = null;
  private speechRecognizerActive = false;

  public async startListening(mode: "tap" | "hold"): Promise<void> {
    if (this.isMuted) {
      this.store.addMessage({
        id: `msg_sys_${Date.now()}`,
        sender: "assistant",
        text: "🔇 Microphone band hai. Pehle unmute karein.",
        timestamp: new Date().toLocaleTimeString(),
      });
      return;
    }

    this.store.setAssistantState("LISTENING", mode);
    this.store.setTranscription("सुन रहा हूँ...");
    window.zarvis?.voice.notifyStateChange("Listening...");
    window.zarvis?.tray.updateStatus("Listening...");

    // ── Use Web Speech API (SpeechRecognition) — natively supported in Electron/Chromium
    const SpeechRecognitionCtor =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognitionCtor) {
      // Fallback: prompt user to type
      this.store.setAssistantState("IDLE");
      this.store.addMessage({
        id: `msg_sys_${Date.now()}`,
        sender: "assistant",
        text: "❌ Is device par voice recognition support nahi hai. Please text type karein.",
        timestamp: new Date().toLocaleTimeString(),
      });
      return;
    }

    try {
      this.speechRecognizer = new SpeechRecognitionCtor();
      this.speechRecognizer.lang = "hi-IN";          // Hindi primary
      this.speechRecognizer.interimResults = true;   // Show partial results live
      this.speechRecognizer.maxAlternatives = 1;
      this.speechRecognizer.continuous = (mode === "hold");

      let finalTranscript = "";
      let interimTranscript = "";

      this.speechRecognizer.onresult = (event: any) => {
        interimTranscript = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          if (result.isFinal) {
            finalTranscript += result[0].transcript;
          } else {
            interimTranscript += result[0].transcript;
          }
        }
        // Show live transcription
        const live = finalTranscript + interimTranscript;
        this.store.setTranscription(live || "सुन रहा हूँ...");
        const box = document.getElementById("live-transcription-box");
        if (box) box.textContent = `"${live}"`;
      };

      this.speechRecognizer.onend = () => {
        this.speechRecognizerActive = false;
        const transcript = finalTranscript.trim();
        if (transcript) {
          this.processVoiceTranscript(transcript);
        } else {
          // Nothing heard
          this.store.setAssistantState("IDLE");
          this.store.setTranscription("Kuch sunayi nahi diya...");
          this.store.addMessage({
            id: `msg_sys_${Date.now()}`,
            sender: "assistant",
            text: "🎙️ Kuch sunai nahi diya. Phir se boliye ya type karein.",
            timestamp: new Date().toLocaleTimeString(),
          });
        }
      };

      this.speechRecognizer.onerror = (event: any) => {
        this.speechRecognizerActive = false;
        const errCode: string = event.error || "unknown";
        let userMsg = "❌ Kuch technical samasya aayi. Phir koshish karein.";
        if (errCode === "not-allowed" || errCode === "permission-denied") {
          userMsg = "🔒 Microphone ki permission nahi mili. Browser/Electron settings mein allow karein.";
        } else if (errCode === "no-speech") {
          userMsg = "🎙️ Koi awaaz nahi aayi. Mic check karein aur phir boliye.";
        } else if (errCode === "audio-capture") {
          userMsg = "🎙️ Microphone available nahi hai ya dusre app ne use kar rakha hai.";
        } else if (errCode === "network") {
          userMsg = "🌐 Network error. Offline mode mein voice recognition nahi chalega.";
        } else if (errCode === "aborted") {
          this.store.setAssistantState("IDLE");
          return;
        }
        this.store.setAssistantState("IDLE");
        this.store.addMessage({
          id: `msg_err_${Date.now()}`,
          sender: "assistant",
          text: userMsg,
          timestamp: new Date().toLocaleTimeString(),
        });
      };

      this.speechRecognizer.start();
      this.speechRecognizerActive = true;

    } catch (err: any) {
      this.store.setAssistantState("IDLE");
      this.store.addMessage({
        id: `msg_err_${Date.now()}`,
        sender: "assistant",
        text: `❌ Microphone start nahi ho saka: ${err?.message || err}`,
        timestamp: new Date().toLocaleTimeString(),
      });
    }
  }

  public async stopListening(): Promise<void> {
    // Stop the Web Speech recognizer gracefully — onend fires automatically with transcript
    if (this.speechRecognizer && this.speechRecognizerActive) {
      this.speechRecognizerActive = false;
      try {
        this.speechRecognizer.stop(); // triggers onresult(final) then onend
      } catch {}
      return;
    }

    // Legacy MediaRecorder path (kept as fallback for hold-mode raw audio)
    this.store.setAssistantState("THINKING");
    this.store.setTranscription("Samajh raha hoon...");
    window.zarvis?.voice.notifyStateChange("Thinking...");
    window.zarvis?.tray.updateStatus("Thinking...");

    if (this.isMuted) {
      this.store.setTranscription("Microphone band hai.");
      this.store.setAssistantState("IDLE");
      return;
    }

    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      try {
        await new Promise<void>((resolve) => {
          this.mediaRecorder.onstop = () => resolve();
          this.mediaRecorder.stop();
        });
        if (this.mediaStream) {
          this.mediaStream.getTracks().forEach((track: any) => track.stop());
          this.mediaStream = null;
        }
      } catch {}
      this.mediaRecorder = null;
    }

    this.store.setAssistantState("IDLE");
  }

  /**
   * Core voice processing: takes a transcribed text string → agent execution → Hindi spoken response.
   * This is called after Web Speech API fires the final transcript.
   */
  private async processVoiceTranscript(transcript: string): Promise<void> {
    const timeStr = new Date().toLocaleTimeString();

    // 1. Show user said something in chat
    this.store.addMessage({
      id: `msg_voice_u_${Date.now()}`,
      sender: "user",
      text: `🎙️ ${transcript}`,
      timestamp: timeStr,
    });
    this.store.addActivity({
      id: `act_voice_${Date.now()}`,
      title: "Voice Input",
      category: "command",
      description: transcript,
      timestamp: timeStr,
    });

    // Switch to chat view so user sees the conversation
    this.switchTab("chat");
    this.store.setAssistantState("THINKING");
    this.store.setTranscription(transcript);

    try {
      // 2. Send transcript to Python Core agent runtime
      const resp = await this.gateway.sendRequest("agent.execute", { goal: transcript });

      if (resp.success && resp.payload) {
        const payload = resp.payload as Record<string, any>;
        const isSuccess = payload.status === "completed" || payload.status === undefined;
        const rawSummary = payload.summary || (isSuccess ? "Kaam ho gaya." : "Kuch galat hua.");
        const stats = payload.task_statistics
          ? ` (${payload.task_statistics.completed ?? 0}/${payload.task_statistics.total ?? 0} tasks)`
          : "";
        const responseText = (isSuccess ? rawSummary : `Kuch samasya aayi: ${rawSummary}`) + stats;

        // 3. Show assistant message
        this.store.addMessage({
          id: `msg_voice_a_${Date.now()}`,
          sender: "assistant",
          text: responseText,
          timestamp: new Date().toLocaleTimeString(),
        });
        this.store.addActivity({
          id: `act_voice_res_${Date.now()}`,
          title: isSuccess ? "Voice Task Complete" : "Voice Task Failed",
          category: "agent",
          description: rawSummary.slice(0, 80),
          timestamp: new Date().toLocaleTimeString(),
        });

        // 4. Speak the response in Hindi
        await this.startSpeaking(responseText);

      } else {
        const errMsg = resp.error?.message || "Backend se koi jawab nahi mila.";
        this.store.addMessage({
          id: `msg_voice_err_${Date.now()}`,
          sender: "assistant",
          text: `❌ ${errMsg}`,
          timestamp: new Date().toLocaleTimeString(),
        });
        this.store.setAssistantState("IDLE");
      }
    } catch (err: any) {
      const errMsg = err?.message || "Unknown error";
      this.store.addMessage({
        id: `msg_voice_err_${Date.now()}`,
        sender: "assistant",
        text: `❌ Voice command process nahi ho saka: ${errMsg}`,
        timestamp: new Date().toLocaleTimeString(),
      });
      this.store.setAssistantState("IDLE");
    }
  }

  public async startSpeaking(text: string, audioBase64?: string): Promise<void> {
    // 1. Cancel previous playback
    this.stopSpeakingPlaybackOnly();

    this.store.setAssistantState("SPEAKING");
    this.store.setSpeakingText(text);
    window.zarvis?.voice.notifyStateChange("Speaking...");
    window.zarvis?.tray.updateStatus("Speaking...");

    // 2. If real synthesized audio bytes returned from Kokoro TTS, play via Web Audio API
    if (audioBase64 && typeof window !== "undefined") {
      try {
        const binaryStr = atob(audioBase64);
        const bytes = new Uint8Array(binaryStr.length);
        for (let i = 0; i < binaryStr.length; i++) {
          bytes[i] = binaryStr.charCodeAt(i);
        }

        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        if (AudioCtx) {
          this.audioContext = this.audioContext || new AudioCtx();
          if (this.audioContext.state === "suspended") {
            await this.audioContext.resume();
          }

          const audioBuffer = await this.audioContext.decodeAudioData(bytes.buffer.slice(0));
          const source = this.audioContext.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(this.audioContext.destination);

          source.onended = () => {
            if (this.store.getState().assistantState === "SPEAKING") {
              this.store.setAssistantState("IDLE");
              window.zarvis?.voice.notifyStateChange("Ready");
              window.zarvis?.tray.updateStatus("Ready");
            }
            this.activeAudioSource = null;
          };

          this.activeAudioSource = source;
          source.start(0);
          return;
        }
      } catch {
        // Fallback to native SpeechSynthesis
      }
    }

    // 3. Native Chromium SpeechSynthesis with Hindi voice
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);

        // ── Select the best available Hindi voice ──────────────────────────
        const selectHindiVoice = () => {
          const voices = window.speechSynthesis.getVoices();
          // Priority: hi-IN exact → hi region → any Hindi → Microsoft Hindi neural → fallback
          const priority = [
            voices.find(v => v.lang === "hi-IN" && v.name.toLowerCase().includes("kalpana")),
            voices.find(v => v.lang === "hi-IN" && v.name.toLowerCase().includes("neural")),
            voices.find(v => v.lang === "hi-IN"),
            voices.find(v => v.lang.startsWith("hi")),
            voices.find(v => v.name.toLowerCase().includes("hindi")),
          ];
          return priority.find(Boolean) ?? null;
        };

        utterance.lang = "hi-IN";
        utterance.rate = 0.92;   // Slightly slower — cleaner Hindi diction
        utterance.pitch = 1.05;  // Slightly warmer pitch
        utterance.volume = 1.0;

        // Voices may not be loaded yet — try immediately then via voiceschanged
        const hindiVoice = selectHindiVoice();
        if (hindiVoice) {
          utterance.voice = hindiVoice;
        } else {
          // Wait for voices to load then re-select
          window.speechSynthesis.addEventListener("voiceschanged", () => {
            const v = selectHindiVoice();
            if (v) utterance.voice = v;
          }, { once: true });
        }
        // ─────────────────────────────────────────────────────────────────

        utterance.onend = () => {
          if (this.store.getState().assistantState === "SPEAKING") {
            this.store.setAssistantState("IDLE");
            window.zarvis?.voice.notifyStateChange("Ready");
            window.zarvis?.tray.updateStatus("Ready");
          }
        };
        utterance.onerror = () => {
          this.store.setAssistantState("IDLE");
        };
        window.speechSynthesis.speak(utterance);
        return;
      } catch {
        this.store.setAssistantState("IDLE");
      }
    } else {
      this.store.setAssistantState("IDLE");
    }
  }

  private stopSpeakingPlaybackOnly(): void {
    if (this.activeAudioSource) {
      try {
        this.activeAudioSource.stop();
      } catch {}
      this.activeAudioSource = null;
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch {}
    }
  }

  public stopSpeaking(): void {
    this.stopSpeakingPlaybackOnly();
    // Dispatch real voice.stop to interrupt Python Core voice session and playback task
    this.gateway.sendRequest("voice.stop").catch(() => {});
    this.store.setAssistantState("IDLE");
    window.zarvis?.voice.notifyStateChange("Ready");
    window.zarvis?.tray.updateStatus("Ready");
  }

  public async submitCommand(commandText: string): Promise<void> {
    const timeStr = new Date().toLocaleTimeString();

    // 1. Add User Message
    this.store.addMessage({
      id: `msg_u_${Date.now()}`,
      sender: "user",
      text: commandText,
      timestamp: timeStr,
    });

    this.store.addActivity({
      id: `act_${Date.now()}`,
      title: "User Command",
      category: "command",
      description: commandText,
      timestamp: timeStr,
    });

    this.switchTab("chat");
    this.store.setAssistantState("THINKING");

    try {
      // Genuinely dispatch to Autonomous Multi-Agent Runtime via Gateway
      const resp = await this.gateway.sendRequest("agent.execute", { goal: commandText });

      if (resp.success && resp.payload) {
        const payload = resp.payload as Record<string, any>;
        const isSuccess = payload.status === "completed" || payload.status === undefined;
        const summary = payload.summary || (isSuccess ? `Goal completed successfully.` : `Goal execution failed.`);
        const stats = payload.task_statistics ? ` (${payload.task_statistics.completed ?? 0}/${payload.task_statistics.total ?? 0} tasks)` : "";

        this.store.addMessage({
          id: `msg_a_${Date.now()}`,
          sender: "assistant",
          text: (isSuccess ? summary : `Task failed: ${summary}`) + stats,
          timestamp: new Date().toLocaleTimeString(),
        });

        this.store.addActivity({
          id: `act_${Date.now()}`,
          title: isSuccess ? "Task Completed" : "Task Failed",
          category: "agent",
          description: `Run ID: ${payload.run_id || "done"}. ${summary.slice(0, 80)}`,
          timestamp: new Date().toLocaleTimeString(),
        });

        this.store.setAssistantState("IDLE");
      } else {
        const errMsg = resp.error?.message || "Execution failed";
        this.store.addMessage({
          id: `msg_err_${Date.now()}`,
          sender: "assistant",
          text: `Task failed: ${errMsg}`,
          timestamp: new Date().toLocaleTimeString(),
        });
        this.store.addActivity({
          id: `act_err_${Date.now()}`,
          title: "Task Failed",
          category: "agent",
          description: errMsg.slice(0, 80),
          timestamp: new Date().toLocaleTimeString(),
        });
        this.store.setAssistantState("IDLE");
        window.zarvis?.notifications.show("Task Interrupted", errMsg, "warning");
      }
    } catch (err: any) {
      const errMsg = err.message || "Unknown error";
      this.store.addMessage({
        id: `msg_err_${Date.now()}`,
        sender: "assistant",
        text: `Failed to process command: ${errMsg}`,
        timestamp: new Date().toLocaleTimeString(),
      });
      this.store.addActivity({
        id: `act_err_${Date.now()}`,
        title: "Task Failed",
        category: "agent",
        description: errMsg.slice(0, 80),
        timestamp: new Date().toLocaleTimeString(),
      });
      this.store.setAssistantState("IDLE");
      window.zarvis?.notifications.show("Task Error", errMsg, "error");
    }
  }

  public async triggerVisionScan(): Promise<void> {
    this.store.addActivity({
      id: `act_vis_${Date.now()}`,
      title: "Screen Visual Grounding",
      category: "vision",
      description: "Capturing and analyzing primary display...",
      timestamp: new Date().toLocaleTimeString(),
    });

    this.store.setAssistantState("THINKING");
    try {
      // Genuinely dispatch to Phase 09 Vision Subsystem via Gateway
      const resp = await this.gateway.sendRequest("vision.scan", { monitor_index: 0 });

      if (resp.success && resp.payload) {
        const payload = resp.payload as Record<string, any>;
        const elementsCount = payload.elements_count ?? 0;
        const interactiveCount = payload.interactive_count ?? 0;
        const res = payload.resolution || { width: 1920, height: 1080 };
        const windowTitle = payload.active_window_title || "Desktop";

        this.store.addActivity({
          id: `act_vis_res_${Date.now()}`,
          title: "Screen Analysis Complete",
          category: "vision",
          description: `Identified ${elementsCount} UI elements (${interactiveCount} interactive) on "${windowTitle}" [${res.width}x${res.height}]`,
          timestamp: new Date().toLocaleTimeString(),
        });

        this.store.addMessage({
          id: `msg_vis_${Date.now()}`,
          sender: "assistant",
          text: `Screen visual analysis complete for **${windowTitle}** (${res.width}x${res.height}). Detected ${elementsCount} UI elements with ${interactiveCount} actionable interaction targets.`,
          timestamp: new Date().toLocaleTimeString(),
        });
        this.store.setAssistantState("IDLE");
      } else {
        this.store.setAssistantState("IDLE");
        window.zarvis?.notifications.show(
          "Vision Scan Failed",
          resp.error?.message || "Could not analyze screen",
          "error"
        );
      }
    } catch {
      this.store.setAssistantState("IDLE");
    }
  }

  public async refreshSystemHealth(): Promise<void> {
    try {
      const resp = await this.gateway.sendRequest("system.health");
      if (resp.success && resp.payload) {
        const payload = resp.payload as Record<string, any>;
        this.store.setTelemetry({
          gateway: payload.gateway ?? "healthy",
          core: payload.core ?? "offline",
          ipc: payload.ipc ?? "disconnected",
          voice: payload.voice ?? "unavailable",
          vision: payload.vision ?? "unavailable",
          memory: payload.memory ?? "unavailable",
        });
        if (payload.core === "healthy") {
          if (this.store.getState().assistantState === "OFFLINE") {
            this.store.setAssistantState("IDLE");
          }
        } else {
          this.store.setAssistantState("OFFLINE");
        }
      } else {
        this.store.setTelemetry({
          gateway: "healthy",
          core: "offline",
          ipc: "disconnected",
          voice: "unavailable",
          vision: "unavailable",
          memory: "unavailable",
        });
      }
    } catch {
      this.store.setTelemetry({
        gateway: "offline",
        core: "offline",
        ipc: "disconnected",
        voice: "unavailable",
        vision: "unavailable",
        memory: "unavailable",
      });
    }
  }

  public switchTab(tab: string): void {
    const screens = ["home", "chat", "agents", "memory", "settings", "activity"];
    screens.forEach((s) => {
      document.getElementById(`view-${s}`)?.classList.add("hidden");
    });
    document.getElementById(`view-${tab}`)?.classList.remove("hidden");

    // Update Workspace breadcrumb
    const tabBreadcrumb = document.getElementById("workspace-current-tab");
    if (tabBreadcrumb) {
      tabBreadcrumb.textContent = tab.charAt(0).toUpperCase() + tab.slice(1);
    }

    // Update Sidebar navigation active class
    screens.forEach((s) => {
      const el = document.getElementById(`nav-${s}`);
      if (el) {
        if (s === tab) {
          el.className =
            "w-full flex items-center space-x-2.5 px-3 py-2 text-xs font-medium rounded-lg bg-blue-600/15 text-blue-400 border border-blue-500/30 transition-all";
        } else {
          el.className =
            "w-full flex items-center space-x-2.5 px-3 py-2 text-xs font-medium rounded-lg text-slate-400 hover:text-white hover:bg-[#111827] transition-all";
        }
      }
    });
  }

  public setWindowMode(mode: "full" | "hud"): void {
    this.store.setWindowMode(mode);
    const hudContainer = document.getElementById("hud-container");
    const workspaceContainer = document.getElementById("workspace-container");
    const titlebarHeader = document.getElementById("titlebar-header");

    if (mode === "hud") {
      workspaceContainer?.classList.add("hidden");
      titlebarHeader?.classList.add("hidden");
      hudContainer?.classList.remove("hidden");
    } else {
      hudContainer?.classList.add("hidden");
      titlebarHeader?.classList.remove("hidden");
      workspaceContainer?.classList.remove("hidden");
    }
  }

  private renderState(state: any): void {
    // 1. Connection & Titlebar Status
    const connDot = document.getElementById("connection-dot");
    const connText = document.getElementById("connection-text");
    const hudStatus = document.getElementById("hud-status-text");

    if (state.assistantState === "OFFLINE") {
      if (connDot) connDot.className = "w-2 h-2 rounded-full bg-red-400";
      if (connText) connText.textContent = "Reconnecting to Gateway...";
      if (hudStatus) hudStatus.textContent = "Offline";
    } else {
      if (connDot) connDot.className = "w-2 h-2 rounded-full bg-emerald-400";
      if (connText) connText.textContent = "ZARVIS Online";
      if (hudStatus) hudStatus.textContent = state.assistantState === "IDLE" ? "Ready" : state.assistantState;
    }

    // 2. Hero Voice Button & Arc Reactor Orb
    const micBtn = document.getElementById("hero-voice-btn");
    const micText = document.getElementById("hero-mic-text");
    const orbOuter = document.getElementById("core-orb");            // .arc-ring-outer
    const orbInner = orbOuter?.querySelector(".arc-ring-inner") as HTMLElement | null;
    const orbGlyph = orbOuter?.querySelector(".arc-core-glyph") as HTMLElement | null;
    const orbGlow  = orbOuter?.closest(".arc-reactor-container")?.querySelector(".arc-reactor-glow") as HTMLElement | null;
    const waveform = document.getElementById("live-waveform");
    const transcription = document.getElementById("live-transcription-box");

    if (state.assistantState === "LISTENING") {
      if (micBtn) {
        micBtn.className =
          "btn-hero-glow w-full flex items-center justify-center gap-2.5 py-3 px-5 rounded-full text-white font-medium text-xs shadow-lg cursor-pointer";
        micBtn.style.background = "linear-gradient(135deg,#059669,#10b981)";
        micBtn.style.boxShadow = "0 0 28px rgba(16,185,129,0.45)";
      }
      if (micText) {
        micText.textContent =
          state.voiceMode === "hold" ? "Listening · Release to send" : "Listening... Tap to stop";
      }
      // Arc Reactor — Emerald/Cyan
      if (orbOuter) {
        orbOuter.style.borderColor = "rgba(16,185,129,0.7)";
        orbOuter.style.boxShadow = "inset 0 0 18px rgba(16,185,129,0.25), 0 0 30px rgba(16,185,129,0.4)";
      }
      if (orbInner) {
        orbInner.style.borderColor = "rgba(0,242,254,0.8)";
        orbInner.style.boxShadow = "0 0 20px rgba(0,242,254,0.5)";
        orbInner.classList.remove("spin-slow", "spin-fast");
        orbInner.classList.add("spin-slow");
      }
      if (orbGlyph) {
        orbGlyph.style.background = "linear-gradient(135deg,#059669,#00f2fe)";
        orbGlyph.style.boxShadow = "0 0 20px rgba(0,242,254,0.8)";
      }
      if (orbGlow) {
        orbGlow.style.background = "radial-gradient(circle,rgba(16,185,129,0.5) 0%,rgba(0,242,254,0.2) 45%,transparent 70%)";
      }
      waveform?.classList.remove("hidden");
      transcription?.classList.remove("hidden");
      if (transcription) transcription.textContent = `"${state.transcription}"`;

    } else if (state.assistantState === "THINKING") {
      if (micBtn) {
        micBtn.className =
          "btn-hero-glow w-full flex items-center justify-center gap-2.5 py-3 px-5 rounded-full text-white font-medium text-xs shadow-lg cursor-pointer";
        micBtn.style.background = "linear-gradient(135deg,#7c3aed,#a855f7)";
        micBtn.style.boxShadow = "0 0 28px rgba(168,85,247,0.45)";
      }
      if (micText) micText.textContent = "Thinking & Planning...";
      // Arc Reactor — Purple/Violet, fast spin
      if (orbOuter) {
        orbOuter.style.borderColor = "rgba(168,85,247,0.7)";
        orbOuter.style.boxShadow = "inset 0 0 18px rgba(168,85,247,0.25), 0 0 30px rgba(168,85,247,0.4)";
      }
      if (orbInner) {
        orbInner.style.borderColor = "rgba(168,85,247,0.9)";
        orbInner.style.boxShadow = "0 0 22px rgba(168,85,247,0.6)";
        orbInner.classList.remove("spin-slow", "spin-fast");
        orbInner.classList.add("spin-fast");
      }
      if (orbGlyph) {
        orbGlyph.style.background = "linear-gradient(135deg,#7c3aed,#a855f7)";
        orbGlyph.style.boxShadow = "0 0 22px rgba(168,85,247,0.9)";
      }
      if (orbGlow) {
        orbGlow.style.background = "radial-gradient(circle,rgba(168,85,247,0.5) 0%,rgba(139,92,246,0.2) 45%,transparent 70%)";
      }
      waveform?.classList.add("hidden");

    } else if (state.assistantState === "SPEAKING") {
      if (micBtn) {
        micBtn.className =
          "btn-hero-glow w-full flex items-center justify-center gap-2.5 py-3 px-5 rounded-full text-white font-medium text-xs shadow-lg cursor-pointer";
        micBtn.style.background = "linear-gradient(135deg,#0284c7,#38bdf8)";
        micBtn.style.boxShadow = "0 0 28px rgba(56,189,248,0.45)";
      }
      if (micText) micText.textContent = "Speaking... Tap to interrupt";
      // Arc Reactor — Sky Blue
      if (orbOuter) {
        orbOuter.style.borderColor = "rgba(56,189,248,0.7)";
        orbOuter.style.boxShadow = "inset 0 0 18px rgba(56,189,248,0.25), 0 0 35px rgba(56,189,248,0.5)";
      }
      if (orbInner) {
        orbInner.style.borderColor = "rgba(56,189,248,0.85)";
        orbInner.style.boxShadow = "0 0 20px rgba(56,189,248,0.5)";
        orbInner.classList.remove("spin-slow", "spin-fast");
        orbInner.classList.add("spin-slow");
      }
      if (orbGlyph) {
        orbGlyph.style.background = "linear-gradient(135deg,#0284c7,#38bdf8)";
        orbGlyph.style.boxShadow = "0 0 22px rgba(56,189,248,0.9)";
      }
      if (orbGlow) {
        orbGlow.style.background = "radial-gradient(circle,rgba(56,189,248,0.5) 0%,rgba(14,165,233,0.2) 45%,transparent 70%)";
      }
      waveform?.classList.remove("hidden");

    } else if (state.assistantState === "OFFLINE") {
      if (micBtn) {
        micBtn.className =
          "btn-hero-glow w-full flex items-center justify-center gap-2.5 py-3 px-5 rounded-full text-white font-medium text-xs shadow-lg cursor-pointer";
        micBtn.style.background = "linear-gradient(135deg,#991b1b,#ef4444)";
        micBtn.style.boxShadow = "0 0 25px rgba(239,68,68,0.4)";
      }
      if (micText) micText.textContent = "Backend Offline — Reconnecting...";
      // Arc Reactor — Red/Error
      if (orbOuter) {
        orbOuter.style.borderColor = "rgba(239,68,68,0.7)";
        orbOuter.style.boxShadow = "inset 0 0 18px rgba(239,68,68,0.2), 0 0 25px rgba(239,68,68,0.35)";
      }
      if (orbInner) {
        orbInner.style.borderColor = "rgba(239,68,68,0.7)";
        orbInner.style.boxShadow = "0 0 15px rgba(239,68,68,0.4)";
        orbInner.classList.remove("spin-slow", "spin-fast");
      }
      if (orbGlyph) {
        orbGlyph.style.background = "linear-gradient(135deg,#991b1b,#ef4444)";
        orbGlyph.style.boxShadow = "0 0 18px rgba(239,68,68,0.7)";
      }
      if (orbGlow) {
        orbGlow.style.background = "radial-gradient(circle,rgba(239,68,68,0.4) 0%,rgba(220,38,38,0.15) 45%,transparent 70%)";
      }
      waveform?.classList.add("hidden");
      transcription?.classList.add("hidden");

    } else {
      // IDLE — Blue/Cyan default
      if (micBtn) {
        micBtn.className =
          "btn-hero-glow w-full flex items-center justify-center gap-2.5 py-3 px-5 rounded-full text-white font-medium text-xs shadow-lg cursor-pointer";
        micBtn.style.background = "";
        micBtn.style.boxShadow = "";
      }
      if (micText) micText.textContent = "Hold / Click to Speak";
      // Arc Reactor — Blue/Cyan (default CSS)
      if (orbOuter) {
        orbOuter.style.borderColor = "";
        orbOuter.style.boxShadow = "";
      }
      if (orbInner) {
        orbInner.style.borderColor = "";
        orbInner.style.boxShadow = "";
        orbInner.classList.remove("spin-fast");
        orbInner.classList.add("spin-slow");
      }
      if (orbGlyph) {
        orbGlyph.style.background = "";
        orbGlyph.style.boxShadow = "";
      }
      if (orbGlow) {
        orbGlow.style.background = "";
      }
      waveform?.classList.add("hidden");
      transcription?.classList.add("hidden");
    }

    // 3. Render Messages
    const chatBox = document.getElementById("chat-messages-container");
    if (chatBox) {
      let messagesHtml = state.conversation
        .map((m: MessageItem) => {
          if (m.sender === "user") {
            return `<div class="flex justify-end"><div class="bg-blue-600 text-white px-4 py-2.5 rounded-2xl rounded-tr-none max-w-md shadow-sm">${m.text}</div></div>`;
          } else if (m.sender === "tool") {
            return `<div class="bg-[#0e1422] border border-slate-700/80 rounded-lg p-2.5 flex items-center justify-between text-[11px]"><div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-emerald-400"></span><span class="font-mono text-slate-300">${m.toolName || "tool"}</span></div><span class="text-emerald-400 font-medium">✓ ${m.toolStatus || "Completed"}</span></div>`;
          } else {
            return `<div class="flex justify-start items-start gap-2.5"><div class="w-6 h-6 rounded bg-blue-600/30 border border-blue-500/50 flex items-center justify-center font-bold text-blue-400 text-[10px] mt-0.5">Z</div><div class="bg-[#111827] border border-slate-800 text-slate-200 px-4 py-2.5 rounded-2xl rounded-tl-none max-w-md leading-relaxed whitespace-pre-wrap">${m.text}</div></div>`;
          }
        })
        .join("");

      if (state.assistantState === "THINKING") {
        messagesHtml += `
          <div class="bg-[#0e1422] border border-blue-500/40 rounded-xl p-3.5 space-y-2 shadow-lg animate-pulse my-2">
            <div class="flex items-center justify-between text-xs font-semibold text-blue-400">
              <span class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-blue-400 animate-ping"></span>
                ZARVIS Autonomous Execution Pipeline
              </span>
              <span class="text-[10px] bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded font-mono">Running</span>
            </div>
            <div class="space-y-1.5 text-[11px] text-slate-300 pt-1">
              <div class="flex items-center gap-2"><span class="text-emerald-400">✓</span> 1. User Intent Detected & DAG Planned</div>
              <div class="flex items-center gap-2"><span class="text-emerald-400">✓</span> 2. Security & Policy Sandbox Verified</div>
              <div class="flex items-center gap-2 text-blue-300 font-medium"><span class="w-1.5 h-1.5 rounded-full bg-blue-400 animate-spin"></span> 3. Executing Tool Action on Windows OS...</div>
            </div>
          </div>
        `;
      }

      chatBox.innerHTML = messagesHtml;
      chatBox.scrollTop = chatBox.scrollHeight;
    }

    // 4. Render Activity Streams
    const rightStream = document.getElementById("activity-stream-container");
    const fullActivity = document.getElementById("activity-full-list");

    const activityHtml = state.activity
      .map(
        (a: ActivityFeedItem) => `
        <div class="bg-[#101623] p-2.5 rounded-lg border border-slate-800/80 hover:border-slate-700 transition-colors">
          <div class="flex items-center justify-between text-[11px] font-medium text-slate-200">
            <span class="flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-blue-400"></span>${a.title}</span>
            <span class="text-[10px] text-slate-500">${a.timestamp}</span>
          </div>
          <p class="text-[10px] text-slate-400 mt-1 font-mono">${a.description}</p>
        </div>`
      )
      .join("");

    if (rightStream) rightStream.innerHTML = activityHtml || `<div class="text-slate-500 text-center py-6 text-[11px]">No recent activity</div>`;
    if (fullActivity) fullActivity.innerHTML = activityHtml || `<div class="text-slate-500 text-center py-6 text-[11px]">No activity logged</div>`;

    // 5. Render Memory
    const prefsList = document.getElementById("memory-prefs-list");
    const factsList = document.getElementById("memory-facts-list");
    if (prefsList) {
      prefsList.innerHTML = state.memories.preferences
        .map((p: string) => `<li class="bg-[#0d1320] p-1.5 rounded border border-slate-800/50">${p}</li>`)
        .join("");
    }
    if (factsList) {
      factsList.innerHTML = state.memories.facts
        .map((f: string) => `<li class="bg-[#0d1320] p-1.5 rounded border border-slate-800/50">${f}</li>`)
        .join("");
    }

    // 6. Render Telemetry Sidebar
    const telDot = document.getElementById("telemetry-summary-dot");
    const telCore = document.getElementById("tel-core");
    const telGw = document.getElementById("tel-gateway");
    const telIpc = document.getElementById("tel-ipc");
    const telVoice = document.getElementById("tel-voice");
    const telVision = document.getElementById("tel-vision");
    const telMem = document.getElementById("tel-memory");

    if (state.telemetry) {
      const isHealthy = state.telemetry.core === "healthy" && state.telemetry.gateway === "healthy";
      if (telDot) {
        telDot.className = isHealthy
          ? "w-1.5 h-1.5 rounded-full bg-emerald-400"
          : "w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse";
      }
      if (telCore) {
        const ok = state.telemetry.core === "healthy";
        telCore.textContent = ok ? "● Healthy" : "○ Offline";
        telCore.className = ok ? "text-emerald-400 font-mono" : "text-red-400 font-mono";
      }
      if (telGw) {
        const ok = state.telemetry.gateway === "healthy";
        telGw.textContent = ok ? "● Healthy" : "○ Offline";
        telGw.className = ok ? "text-emerald-400 font-mono" : "text-red-400 font-mono";
      }
      if (telIpc) {
        const ok = state.telemetry.ipc === "connected";
        telIpc.textContent = ok ? "● Connected" : "○ Disconnected";
        telIpc.className = ok ? "text-emerald-400 font-mono" : "text-red-400 font-mono";
      }
      if (telVoice) {
        const ok = state.telemetry.voice === "ready";
        telVoice.textContent = ok ? "● Ready" : "○ Standby";
        telVoice.className = ok ? "text-emerald-400 font-mono" : "text-slate-400 font-mono";
      }
      if (telVision) {
        const ok = state.telemetry.vision === "ready";
        telVision.textContent = ok ? "● Ready" : "○ Standby";
        telVision.className = ok ? "text-emerald-400 font-mono" : "text-slate-400 font-mono";
      }
      if (telMem) {
        const ok = state.telemetry.memory === "ready";
        telMem.textContent = ok ? "● Ready" : "○ Standby";
        telMem.className = ok ? "text-emerald-400 font-mono" : "text-slate-400 font-mono";
      }
    }
  }

  private updateMaximizeIcon(isMaximized: boolean): void {
    const iconMax = document.getElementById("icon-window-maximize");
    const iconRestore = document.getElementById("icon-window-restore");
    if (isMaximized) {
      iconMax?.classList.add("hidden");
      iconRestore?.classList.remove("hidden");
    } else {
      iconMax?.classList.remove("hidden");
      iconRestore?.classList.add("hidden");
    }
  }

  public async showDiagnosticsModal(errInfo?: any): Promise<void> {
    const modal = document.getElementById("modal-diagnostics");
    const detailsBox = document.getElementById("diagnostic-details-box");
    const msgEl = document.getElementById("diagnostic-message");

    if (!modal) return;
    modal.classList.remove("hidden");

    let diagText = "";
    if (errInfo) {
      if (msgEl) msgEl.textContent = "Missing or incomplete runtime files detected.";
      diagText += `RUNTIME VALIDATION FAILED:\n${(errInfo.errors || []).join("\n")}\n\n`;
      diagText += `DIAGNOSTICS:\n${JSON.stringify(errInfo.diagnostics, null, 2)}`;
    } else if (window.zarvis?.system.getDiagnostics) {
      try {
        const diag = await window.zarvis.system.getDiagnostics();
        const errors = diag.validation?.errors || [];
        if (errors.length > 0) {
          if (msgEl) msgEl.textContent = "Backend runtime files are missing from the installed package.";
          diagText += `ERRORS:\n${errors.join("\n")}\n\n`;
        } else {
          if (msgEl) msgEl.textContent = "Backend services could not be reached over local loopback.";
        }
        diagText += `PROCESS STATUS:\n${JSON.stringify(diag.processes, null, 2)}\n\n`;
        diagText += `RUNTIME INFO:\n${JSON.stringify(diag.validation?.diagnostics, null, 2)}`;
      } catch (err) {
        diagText = `Failed to fetch diagnostics: ${err}`;
      }
    } else {
      diagText = "Local WebSocket Gateway on ws://127.0.0.1:3000/ws is unreachable.";
    }

    if (detailsBox) {
      detailsBox.textContent = diagText;
    }
  }
}

// Bootstrap on DOM load
window.addEventListener("DOMContentLoaded", () => {
  const app = new ZarvisApp();
  app.init();
});
