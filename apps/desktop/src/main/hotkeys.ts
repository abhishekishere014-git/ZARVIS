/**
 * Global hotkey management for ZARVIS.
 * Handles shortcut registration, conflict detection, fallback shortcuts,
 * dynamic configuration changes, and clean shutdown.
 */

import { globalShortcut } from "electron";
import { WindowManager } from "./window-manager";

export interface HotkeyRegistrationResult {
  success: boolean;
  shortcut: string;
  isFallback: boolean;
  error?: string;
}

export class HotkeyManager {
  private registeredShortcut: string | null = null;
  private readonly fallbackShortcut = "CommandOrControl+Shift+Space";

  constructor(
    private readonly windowManager: WindowManager,
    private readonly onActivateVoice: () => void
  ) {}

  /**
   * Registers a global hotkey with conflict detection and fallback recovery.
   */
  public register(
    shortcut: string = "CommandOrControl+Space",
    allowFallback = true
  ): HotkeyRegistrationResult {
    this.unregister();

    try {
      // Check if shortcut is already registered/bound
      if (globalShortcut.isRegistered(shortcut)) {
        if (allowFallback) {
          const fallbackRes = this.registerFallback();
          if (fallbackRes.success) {
            return fallbackRes;
          }
        }
        return {
          success: false,
          shortcut,
          isFallback: false,
          error: `Shortcut '${shortcut}' is already in use by another application.`,
        };
      }

      const success = globalShortcut.register(shortcut, () => {
        this.windowManager.showAndFocus();
        this.onActivateVoice();
      });

      if (success && globalShortcut.isRegistered(shortcut)) {
        this.registeredShortcut = shortcut;
        return {
          success: true,
          shortcut,
          isFallback: false,
        };
      } else {
        if (allowFallback) {
          return this.registerFallback();
        }
        return {
          success: false,
          shortcut,
          isFallback: false,
          error: `Failed to bind shortcut '${shortcut}'.`,
        };
      }
    } catch (err: any) {
      if (allowFallback) {
        return this.registerFallback();
      }
      return {
        success: false,
        shortcut,
        isFallback: false,
        error: err?.message || String(err),
      };
    }
  }

  private registerFallback(): HotkeyRegistrationResult {
    try {
      if (globalShortcut.isRegistered(this.fallbackShortcut)) {
        return {
          success: false,
          shortcut: this.fallbackShortcut,
          isFallback: true,
          error: `Fallback shortcut '${this.fallbackShortcut}' is also in use.`,
        };
      }

      const success = globalShortcut.register(this.fallbackShortcut, () => {
        this.windowManager.showAndFocus();
        this.onActivateVoice();
      });

      if (success) {
        this.registeredShortcut = this.fallbackShortcut;
        return {
          success: true,
          shortcut: this.fallbackShortcut,
          isFallback: true,
        };
      }
    } catch {}

    return {
      success: false,
      shortcut: this.fallbackShortcut,
      isFallback: true,
      error: "Could not register primary or fallback global hotkey.",
    };
  }

  /**
   * Dynamically reconfigures the global hotkey.
   */
  public changeShortcut(newShortcut: string): HotkeyRegistrationResult {
    return this.register(newShortcut, false);
  }

  public getRegisteredShortcut(): string | null {
    return this.registeredShortcut;
  }

  public isRegistered(): boolean {
    return !!this.registeredShortcut;
  }

  public unregister(): void {
    if (this.registeredShortcut) {
      try {
        globalShortcut.unregister(this.registeredShortcut);
      } catch {}
      this.registeredShortcut = null;
    }
  }

  public unregisterAll(): void {
    try {
      globalShortcut.unregisterAll();
    } catch {}
    this.registeredShortcut = null;
  }
}
