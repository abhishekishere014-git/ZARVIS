/**
 * Types and interfaces for the ZARVIS Desktop Main Process.
 */

export type DesktopWindowMode = "full" | "hud";

export interface WindowState {
  mode: DesktopWindowMode;
  isPinned: boolean;
  isVisible: boolean;
  bounds: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface HotkeyConfig {
  activationShortcut: string; // e.g. "CommandOrControl+Space"
  enabled: boolean;
}

export interface SystemTrayAction {
  id: string;
  label: string;
  enabled?: boolean;
}
