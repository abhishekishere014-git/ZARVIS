/**
 * Reactive Central State Store for ZARVIS Desktop Renderer.
 */

export type AssistantState =
  | "IDLE"
  | "LISTENING"
  | "THINKING"
  | "SPEAKING"
  | "ERROR"
  | "OFFLINE";

export interface MessageItem {
  id: string;
  sender: "user" | "assistant" | "tool";
  text: string;
  timestamp: string;
  toolName?: string;
  toolStatus?: string;
}

export interface AgentProgressItem {
  name: string;
  role: string;
  status: "complete" | "working" | "waiting" | "attention";
  duration?: string;
}

export interface ActivityFeedItem {
  id: string;
  title: string;
  category: "command" | "tool" | "agent" | "vision" | "system";
  description: string;
  timestamp: string;
}

export interface SystemTelemetry {
  core: "healthy" | "degraded" | "offline";
  gateway: "healthy" | "degraded" | "offline";
  ipc: "connected" | "disconnected";
  voice: "ready" | "unavailable";
  vision: "ready" | "unavailable";
  memory: "ready" | "unavailable";
}

export interface DesktopState {
  assistantState: AssistantState;
  voiceMode: "tap" | "hold" | null;
  windowMode: "full" | "hud";
  isPinned: boolean;
  transcription: string;
  speakingText: string;
  telemetry: SystemTelemetry;
  conversation: MessageItem[];
  agents: AgentProgressItem[];
  activity: ActivityFeedItem[];
  memories: {
    preferences: string[];
    facts: string[];
  };
}

export type StoreListener = (state: DesktopState) => void;

export class DesktopStore {
  private state: DesktopState;
  private readonly listeners = new Set<StoreListener>();

  constructor() {
    this.state = {
      assistantState: "IDLE",
      voiceMode: null,
      windowMode: "full",
      isPinned: false,
      transcription: "",
      speakingText: "",
      telemetry: {
        core: "healthy",
        gateway: "healthy",
        ipc: "connected",
        voice: "ready",
        vision: "ready",
        memory: "ready",
      },
      conversation: [],
      agents: [
        { name: "Planner", role: "DAG Plan Decomposition", status: "waiting" },
        { name: "Coder", role: "Sandboxed File Execution", status: "waiting" },
        { name: "Verifier", role: "Artifact Byte Validation", status: "waiting" },
        { name: "Synthesis", role: "Normalized Response Formulation", status: "waiting" },
      ],
      activity: [],
      memories: {
        preferences: [
          "Default IDE: Visual Studio Code",
          "Audio Voice: Kokoro af_heart (Natural)",
          "Theme: Dark Obsidian Slate",
        ],
        facts: [
          "Workspace: Local Windows Desktop",
          "Operating System: Windows 11",
          "Local-first hybrid core architecture",
        ],
      },
    };
  }

  public getState(): DesktopState {
    return this.state;
  }

  public subscribe(listener: StoreListener): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => this.listeners.delete(listener);
  }

  private emit(): void {
    for (const listener of this.listeners) {
      try {
        listener(this.state);
      } catch {
        // Ignore subscriber error
      }
    }
  }

  public setAssistantState(newState: AssistantState, voiceMode: "tap" | "hold" | null = null): void {
    this.state = {
      ...this.state,
      assistantState: newState,
      voiceMode: newState === "LISTENING" ? voiceMode : null,
    };
    this.emit();
  }

  public setWindowMode(mode: "full" | "hud"): void {
    this.state = { ...this.state, windowMode: mode };
    this.emit();
  }

  public setPinned(isPinned: boolean): void {
    this.state = { ...this.state, isPinned };
    this.emit();
  }

  public setTranscription(text: string): void {
    this.state = { ...this.state, transcription: text };
    this.emit();
  }

  public setSpeakingText(text: string): void {
    this.state = { ...this.state, speakingText: text };
    this.emit();
  }

  public setTelemetry(telemetry: Partial<SystemTelemetry>): void {
    this.state = {
      ...this.state,
      telemetry: { ...this.state.telemetry, ...telemetry },
    };
    this.emit();
  }

  public addMessage(msg: MessageItem): void {
    this.state = {
      ...this.state,
      conversation: [...this.state.conversation, msg],
    };
    this.emit();
  }

  public addActivity(item: ActivityFeedItem): void {
    this.state = {
      ...this.state,
      activity: [item, ...this.state.activity.slice(0, 49)], // keep last 50
    };
    this.emit();
  }

  public updateAgent(name: string, update: Partial<AgentProgressItem>): void {
    this.state = {
      ...this.state,
      agents: this.state.agents.map((a) => (a.name === name ? { ...a, ...update } : a)),
    };
    this.emit();
  }
}
