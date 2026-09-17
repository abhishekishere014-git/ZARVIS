/**
 * Desktop Window Manager.
 * Orchestrates Full Workspace and Compact Floating HUD window lifecycle.
 */

import { BrowserWindow, screen } from "electron";
import * as path from "node:path";
import { DesktopWindowMode, WindowState } from "./types";

export class WindowManager {
  private window: BrowserWindow | null = null;
  private mode: DesktopWindowMode = "full";
  private isPinned = false;
  private isQuitting = false;

  // Stored dimensions
  private fullBounds = { width: 1280, height: 800 };
  private hudBounds = { width: 380, height: 64 };

  constructor(private readonly preloadPath: string, private readonly htmlPath: string) {}

  public getMainWindow(): BrowserWindow | null {
    return this.window;
  }

  public getMode(): DesktopWindowMode {
    return this.mode;
  }

  public getIsPinned(): boolean {
    return this.isPinned;
  }

  public setQuitting(quitting: boolean): void {
    this.isQuitting = quitting;
  }

  public createWindow(): BrowserWindow {
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

    const initialX = Math.round((screenWidth - this.fullBounds.width) / 2);
    const initialY = Math.round((screenHeight - this.fullBounds.height) / 2);

    this.window = new BrowserWindow({
      width: this.fullBounds.width,
      height: this.fullBounds.height,
      x: initialX,
      y: initialY,
      minWidth: 1024,
      minHeight: 640,
      backgroundColor: "#0B0F19",
      frame: false,
      show: false,
      title: "ZARVIS",
      webPreferences: {
        preload: this.preloadPath,
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
        webSecurity: true,
        allowRunningInsecureContent: false,
        navigateOnDragDrop: false,
      },
    });

    // Navigation lockdown: prevent navigating away from local package
    this.window.webContents.on("will-navigate", (event, url) => {
      if (!url.startsWith("file://")) {
        event.preventDefault();
      }
    });

    // Deny popup / new window creation
    this.window.webContents.setWindowOpenHandler(() => {
      return { action: "deny" };
    });

    this.window.loadFile(this.htmlPath);

    this.window.once("ready-to-show", () => {
      this.window?.show();
    });

    // Forward maximize / unmaximize state to renderer
    this.window.on("maximize", () => {
      this.window?.webContents.send("zarvis:window:maximizedChange", true);
    });

    this.window.on("unmaximize", () => {
      this.window?.webContents.send("zarvis:window:maximizedChange", false);
    });

    // Close-to-tray behavior
    this.window.on("close", (event) => {
      if (!this.isQuitting) {
        event.preventDefault();
        this.window?.hide();
      }
    });

    return this.window;
  }

  public async setMode(newMode: DesktopWindowMode): Promise<void> {
    if (!this.window) return;
    this.mode = newMode;

    const primaryDisplay = screen.getPrimaryDisplay();
    const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

    if (newMode === "hud") {
      // Position HUD at bottom-right of screen
      const hudX = screenWidth - this.hudBounds.width - 24;
      const hudY = screenHeight - this.hudBounds.height - 24;

      this.window.setMinimumSize(320, 56);
      this.window.setBounds({
        x: hudX,
        y: hudY,
        width: this.hudBounds.width,
        height: this.hudBounds.height,
      });
      this.window.setAlwaysOnTop(true, "floating");
      this.isPinned = true;
    } else {
      // Restore Full Workspace
      const fullX = Math.round((screenWidth - this.fullBounds.width) / 2);
      const fullY = Math.round((screenHeight - this.fullBounds.height) / 2);

      this.window.setMinimumSize(1024, 640);
      this.window.setBounds({
        x: fullX,
        y: fullY,
        width: this.fullBounds.width,
        height: this.fullBounds.height,
      });
      this.window.setAlwaysOnTop(this.isPinned);
    }

    this.window.webContents.send("zarvis:mode:changed", newMode);
  }

  public togglePin(): boolean {
    if (!this.window) return false;
    this.isPinned = !this.isPinned;
    this.window.setAlwaysOnTop(this.isPinned, this.mode === "hud" ? "floating" : "normal");
    return this.isPinned;
  }

  public minimize(): void {
    this.window?.minimize();
  }

  public maximize(): void {
    this.window?.maximize();
  }

  public unmaximize(): void {
    this.window?.unmaximize();
  }

  public toggleMaximize(): boolean {
    if (!this.window) return false;
    if (this.window.isMaximized()) {
      this.window.unmaximize();
      return false;
    } else {
      this.window.maximize();
      return true;
    }
  }

  public isMaximized(): boolean {
    return this.window?.isMaximized() ?? false;
  }

  public close(): void {
    this.window?.close();
  }

  public showAndFocus(): void {
    if (!this.window) return;
    if (this.window.isMinimized()) {
      this.window.restore();
    }
    this.window.show();
    this.window.focus();
  }

  public destroy(): void {
    if (this.window) {
      this.isQuitting = true;
      try {
        this.window.removeAllListeners();
        if (!this.window.isDestroyed()) {
          this.window.destroy();
        }
      } catch {}
      this.window = null;
    }
  }
}
