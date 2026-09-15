/**
 * Global hotkey management for ZARVIS.
 */

import { globalShortcut } from "electron";
import { WindowManager } from "./window-manager";

export class HotkeyManager {
  private registeredShortcut: string | null = null;

  constructor(
    private readonly windowManager: WindowManager,
    private readonly onActivateVoice: () => void
  ) {}

  public register(shortcut: string = "CommandOrControl+Space"): boolean {
    this.unregister();

    try {
      const success = globalShortcut.register(shortcut, () => {
        this.windowManager.showAndFocus();
        this.onActivateVoice();
      });

      if (success) {
        this.registeredShortcut = shortcut;
      }
      return success;
    } catch {
      return false;
    }
  }

  public unregister(): void {
    if (this.registeredShortcut) {
      globalShortcut.unregister(this.registeredShortcut);
      this.registeredShortcut = null;
    }
  }

  public unregisterAll(): void {
    globalShortcut.unregisterAll();
    this.registeredShortcut = null;
  }
}
