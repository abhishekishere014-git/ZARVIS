/**
 * Strictly typed Preload Security Bridge API for ZARVIS Renderer.
 * Zero raw Node/process/shell APIs are exposed to the UI.
 */

export interface ZarvisWindowApi {
  minimize: () => void;
  maximize: () => void;
  unmaximize: () => void;
  toggleMaximize: () => Promise<boolean>;
  isMaximized: () => Promise<boolean>;
  close: () => void;
  setMode: (mode: "full" | "hud") => Promise<void>;
  getMode: () => Promise<"full" | "hud">;
  togglePin: () => Promise<boolean>;
  isPinned: () => Promise<boolean>;
  onModeChange: (callback: (mode: "full" | "hud") => void) => () => void;
  onMaximizedChange: (callback: (isMaximized: boolean) => void) => () => void;
}

export interface ZarvisVoiceBridgeApi {
  notifyStateChange: (state: string) => void;
  onActivateVoice: (callback: () => void) => () => void;
  onMuteToggle?: (callback: () => void) => () => void;
}

export interface ZarvisTrayBridgeApi {
  updateStatus: (statusText: string, stateColor?: "green" | "blue" | "amber" | "red") => void;
}

export interface ZarvisNotificationApi {
  show: (title: string, body: string, level?: "info" | "warning" | "error" | "success") => void;
}

export interface ZarvisSystemBridgeApi {
  getGatewayUrl: () => Promise<string>;
  getVersion: () => string;
  getDiagnostics: () => Promise<any>;
  onRestartSubsystem?: (callback: (subsystem: string) => void) => () => void;
  onNavigateTab?: (callback: (tab: string) => void) => () => void;
  onPauseToggle?: (callback: (isPaused: boolean) => void) => () => void;
  onRuntimeError?: (callback: (errorInfo: { errors: string[]; diagnostics: any }) => void) => () => void;
}

export interface ZarvisBridgeApi {
  window: ZarvisWindowApi;
  voice: ZarvisVoiceBridgeApi;
  tray: ZarvisTrayBridgeApi;
  notifications: ZarvisNotificationApi;
  system: ZarvisSystemBridgeApi;
}

declare global {
  interface Window {
    zarvis?: ZarvisBridgeApi;
  }
}
