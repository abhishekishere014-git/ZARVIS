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
  }

  private setupPreloadBridge(): void {
    if (!window.zarvis) return;

    window.zarvis.window.onModeChange((mode) => {
      this.setWindowMode(mode);
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
        this.store.setAssistantState("IDLE");
        this.store.setTelemetry({ gateway: "healthy" });
        this.refreshSystemHealth();
      } else {
        this.store.setAssistantState("OFFLINE");
        this.store.setTelemetry({ gateway: "offline", ipc: "disconnected" });
      }
    });

    this.gateway.onEvent((event) => {
      const payload = event.payload as Record<string, any>;
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

      if (event.type.startsWith("agent.") && event.type !== "agent.planning" && event.type !== "agent.task.started") {
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

      if (event.type === "agent.completed") {
        this.store.addActivity({
          id: `act_${Date.now()}`,
          title: "Agent Workflow Complete",
          category: "agent",
          description: "All task waves verified and synthesized.",
          timestamp: new Date().toLocaleTimeString(),
        });
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

  public async startListening(mode: "tap" | "hold"): Promise<void> {
    this.store.setAssistantState("LISTENING", mode);
    this.store.setTranscription("Listening...");
    window.zarvis?.voice.notifyStateChange("Listening...");
    window.zarvis?.tray.updateStatus("Listening...");

    this.audioChunks = [];
    if (typeof navigator !== "undefined" && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.mediaStream = stream;
        const recorder = new (window as any).MediaRecorder(stream);
        recorder.ondataavailable = (e: any) => {
          if (e.data && e.data.size > 0) {
            this.audioChunks.push(e.data);
          }
        };
        recorder.start(100);
        this.mediaRecorder = recorder;
      } catch (err) {
        // Fallback for environments without physical mic access
      }
    }
  }

  public async stopListening(): Promise<void> {
    this.store.setAssistantState("THINKING");
    this.store.setTranscription("Processing speech buffer...");
    window.zarvis?.voice.notifyStateChange("Thinking...");
    window.zarvis?.tray.updateStatus("Thinking...");

    if (this.isMuted) {
      this.store.setTranscription("Microphone is muted.");
      this.store.setAssistantState("IDLE");
      return;
    }

    let audioBase64 = "";

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

        if (this.audioChunks.length > 0) {
          const audioBlob = new Blob(this.audioChunks, { type: "audio/webm" });
          const buffer = await audioBlob.arrayBuffer();
          const bytes = new Uint8Array(buffer);
          let binary = "";
          for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
          }
          audioBase64 = btoa(binary);
        }
      } catch {
        // Gracefully proceed if audio buffer conversion fails
      }
      this.mediaRecorder = null;
    }

    try {
      const resp = await this.gateway.sendRequest("voice.interact", {
        audio_base64: audioBase64 || undefined,
        text: audioBase64 ? undefined : "Voice command triggered from desktop client",
      });

      if (resp.success && resp.payload) {
        const payload = resp.payload as Record<string, any>;
        const speechText = payload.text || "Voice pipeline operational.";
        this.store.setTranscription(speechText);
        await this.startSpeaking(speechText, payload.audio_base64);
      } else {
        this.store.setAssistantState("IDLE");
      }
    } catch {
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

    // 3. Fallback to native Chromium SpeechSynthesis
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
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
        const summary = payload.summary || `Goal completed successfully.`;
        const stats = payload.task_statistics ? ` (${payload.task_statistics.completed ?? 0}/${payload.task_statistics.total ?? 0} tasks)` : "";

        this.store.addMessage({
          id: `msg_a_${Date.now()}`,
          sender: "assistant",
          text: summary + stats,
          timestamp: new Date().toLocaleTimeString(),
        });

        this.store.addActivity({
          id: `act_${Date.now()}`,
          title: "Task Completed",
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
        this.store.setAssistantState("ERROR");
      }
    } catch (err: any) {
      this.store.addMessage({
        id: `msg_err_${Date.now()}`,
        sender: "assistant",
        text: `Failed to process command: ${err.message || "Unknown error"}`,
        timestamp: new Date().toLocaleTimeString(),
      });
      this.store.setAssistantState("ERROR");
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
          description: `Active: "${windowTitle}" | ${res.width}x${res.height} | ${elementsCount} elements mapped (${interactiveCount} interactive)`,
          timestamp: new Date().toLocaleTimeString(),
        });

        this.store.addMessage({
          id: `msg_vis_${Date.now()}`,
          sender: "assistant",
          text: `Screen visual analysis complete (${res.width}x${res.height}). Active window: "${windowTitle}". Identified ${elementsCount} UI elements with ${interactiveCount} actionable interactive targets mapped.`,
          timestamp: new Date().toLocaleTimeString(),
        });

        this.store.setAssistantState("IDLE");
        window.zarvis?.notifications.show(
          "Screen Grounding",
          `Mapped ${interactiveCount} interactive elements on ${res.width}x${res.height} display.`,
          "success"
        );
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
      const resp = await this.gateway.sendRequest("system.ping");
      if (resp.success) {
        this.store.setTelemetry({
          gateway: "healthy",
          core: "healthy",
          ipc: "connected",
          voice: "ready",
          vision: "ready",
          memory: "ready",
        });
      }
    } catch {
      this.store.setTelemetry({
        gateway: "degraded",
        core: "offline",
        ipc: "disconnected",
      });
    }
  }

  public switchTab(tab: string): void {
    const screens = ["home", "chat", "agents", "memory", "settings", "activity"];
    screens.forEach((s) => {
      document.getElementById(`view-${s}`)?.classList.add("hidden");
    });
    document.getElementById(`view-${tab}`)?.classList.remove("hidden");

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

    if (mode === "hud") {
      workspaceContainer?.classList.add("hidden");
      hudContainer?.classList.remove("hidden");
    } else {
      hudContainer?.classList.add("hidden");
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

    // 2. Hero Voice Button & Orb
    const micBtn = document.getElementById("hero-voice-btn");
    const micText = document.getElementById("hero-mic-text");
    const orb = document.getElementById("core-orb");
    const waveform = document.getElementById("live-waveform");
    const transcription = document.getElementById("live-transcription-box");

    if (state.assistantState === "LISTENING") {
      if (micBtn) {
        micBtn.className =
          "group relative flex items-center gap-3 px-6 py-3 rounded-full bg-gradient-to-r from-emerald-600 to-emerald-500 text-white font-medium text-sm shadow-[0_0_25px_rgba(16,185,129,0.35)] transition-all cursor-pointer";
      }
      if (micText) {
        micText.textContent =
          state.voiceMode === "hold" ? "Listening · Release to send" : "Listening... Tap to stop";
      }
      if (orb) {
        orb.className =
          "w-28 h-28 rounded-full border border-emerald-500/60 bg-gradient-to-b from-emerald-500/20 to-transparent flex items-center justify-center transition-all shadow-[0_0_30px_rgba(16,185,129,0.3)]";
      }
      waveform?.classList.remove("hidden");
      transcription?.classList.remove("hidden");
      if (transcription) transcription.textContent = `"${state.transcription}"`;
    } else if (state.assistantState === "THINKING") {
      if (micBtn) {
        micBtn.className =
          "group relative flex items-center gap-3 px-6 py-3 rounded-full bg-blue-700 text-white font-medium text-sm shadow-md transition-all cursor-pointer";
      }
      if (micText) micText.textContent = "Thinking & Planning...";
      if (orb) {
        orb.className =
          "w-28 h-28 rounded-full border border-blue-500 animate-spin-slow bg-gradient-to-b from-blue-500/20 to-transparent flex items-center justify-center transition-all shadow-[0_0_30px_rgba(10,132,255,0.4)]";
      }
      waveform?.classList.add("hidden");
    } else if (state.assistantState === "SPEAKING") {
      if (micBtn) {
        micBtn.className =
          "group relative flex items-center gap-3 px-6 py-3 rounded-full bg-sky-600 text-white font-medium text-sm shadow-[0_0_25px_rgba(56,189,248,0.35)] transition-all cursor-pointer";
      }
      if (micText) micText.textContent = "Speaking... Tap to interrupt";
      if (orb) {
        orb.className =
          "w-28 h-28 rounded-full border border-sky-400 bg-gradient-to-b from-sky-500/20 to-transparent flex items-center justify-center transition-all shadow-[0_0_35px_rgba(56,189,248,0.4)]";
      }
      waveform?.classList.remove("hidden");
    } else {
      // IDLE or ERROR
      if (micBtn) {
        micBtn.className =
          "group relative flex items-center gap-3 px-6 py-3 rounded-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-medium text-sm shadow-[0_4px_20px_rgba(10,132,255,0.3)] transition-all cursor-pointer";
      }
      if (micText) micText.textContent = "Tap to speak or Hold for PTT";
      if (orb) {
        orb.className =
          "w-28 h-28 rounded-full border border-blue-500/20 bg-gradient-to-b from-blue-500/10 to-transparent flex items-center justify-center transition-all";
      }
      waveform?.classList.add("hidden");
      transcription?.classList.add("hidden");
    }

    // 3. Render Messages
    const chatBox = document.getElementById("chat-messages-container");
    if (chatBox) {
      chatBox.innerHTML = state.conversation
        .map((m: MessageItem) => {
          if (m.sender === "user") {
            return `<div class="flex justify-end"><div class="bg-blue-600 text-white px-4 py-2.5 rounded-2xl rounded-tr-none max-w-md shadow-sm">${m.text}</div></div>`;
          } else if (m.sender === "tool") {
            return `<div class="bg-[#0e1422] border border-slate-700/80 rounded-lg p-2.5 flex items-center justify-between text-[11px]"><div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-emerald-400"></span><span class="font-mono text-slate-300">${m.toolName || "tool"}</span></div><span class="text-emerald-400 font-medium">✓ ${m.toolStatus || "Completed"}</span></div>`;
          } else {
            return `<div class="flex justify-start items-start gap-2.5"><div class="w-6 h-6 rounded bg-blue-600/30 border border-blue-500/50 flex items-center justify-center font-bold text-blue-400 text-[10px] mt-0.5">Z</div><div class="bg-[#111827] border border-slate-800 text-slate-200 px-4 py-2.5 rounded-2xl rounded-tl-none max-w-md">${m.text}</div></div>`;
          }
        })
        .join("");
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
  }
}

// Bootstrap on DOM load
window.addEventListener("DOMContentLoaded", () => {
  const app = new ZarvisApp();
  app.init();
});
