/**
 * Windows System Tray integration for ZARVIS.
 * Provides instant access, voice triggers, mute, pause, activity, settings,
 * process restart controls, and clean shutdown.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { Menu, Tray, nativeImage, app } from "electron";
import { WindowManager } from "./window-manager";

export interface TrayCallbacks {
  onQuit: () => void;
  onActivateVoice: () => void;
  onTogglePause?: (isPaused: boolean) => void;
  onNavigateTab?: (tab: string) => void;
  onRestartCore?: () => void;
  onRestartGateway?: () => void;
}

export class SystemTrayManager {
  private tray: Tray | null = null;
  private statusText = "Online • Ready";
  private isMuted = false;
  private isPaused = false;

  constructor(
    private readonly windowManager: WindowManager,
    private readonly onQuit: () => void,
    private readonly onActivateVoice: () => void,
    private readonly callbacks?: Partial<TrayCallbacks>
  ) {}

  public createTray(): Tray {
    const icon = this.loadTrayIcon();
    this.tray = new Tray(icon);
    this.tray.setToolTip(`ZARVIS — ${this.statusText}`);

    this.updateContextMenu();

    this.tray.on("click", () => {
      this.windowManager.showAndFocus();
    });

    return this.tray;
  }

  public updateStatus(newStatus: string): void {
    this.statusText = newStatus;
    if (this.tray) {
      this.tray.setToolTip(`ZARVIS — ${this.statusText}`);
      this.updateContextMenu();
    }
  }

  public setMuted(muted: boolean): void {
    this.isMuted = muted;
    this.updateContextMenu();
  }

  public setPaused(paused: boolean): void {
    this.isPaused = paused;
    this.updateContextMenu();
  }

  public updateContextMenu(): void {
    if (!this.tray) return;

    const contextMenu = Menu.buildFromTemplate([
      {
        label: `ZARVIS (${this.statusText})`,
        enabled: false,
      },
      { type: "separator" },
      {
        label: "Open ZARVIS",
        click: () => this.windowManager.showAndFocus(),
      },
      {
        label: "Start Listening",
        click: () => {
          this.windowManager.showAndFocus();
          this.onActivateVoice();
        },
      },
      {
        label: "Mute Microphone",
        type: "checkbox",
        checked: this.isMuted,
        click: () => {
          this.isMuted = !this.isMuted;
          const win = this.windowManager.getMainWindow();
          win?.webContents.send("zarvis:voice:muteToggle");
          this.updateContextMenu();
        },
      },
      {
        label: this.isPaused ? "Resume Assistant" : "Pause Assistant",
        type: "checkbox",
        checked: this.isPaused,
        click: () => {
          this.isPaused = !this.isPaused;
          const win = this.windowManager.getMainWindow();
          win?.webContents.send("zarvis:assistant:pauseToggle", this.isPaused);
          this.callbacks?.onTogglePause?.(this.isPaused);
          this.updateContextMenu();
        },
      },
      { type: "separator" },
      {
        label: "Activity",
        click: () => {
          this.windowManager.showAndFocus();
          const win = this.windowManager.getMainWindow();
          win?.webContents.send("zarvis:navigation:switchTab", "activity");
          this.callbacks?.onNavigateTab?.("activity");
        },
      },
      {
        label: "Settings",
        click: () => {
          this.windowManager.showAndFocus();
          const win = this.windowManager.getMainWindow();
          win?.webContents.send("zarvis:navigation:switchTab", "settings");
          this.callbacks?.onNavigateTab?.("settings");
        },
      },
      {
        label: "Switch to Compact HUD",
        click: () => this.windowManager.setMode("hud"),
      },
      {
        label: "Open Full Workspace",
        click: () => this.windowManager.setMode("full"),
      },
      { type: "separator" },
      {
        label: "Restart Python Core",
        click: () => {
          if (this.callbacks?.onRestartCore) {
            this.callbacks.onRestartCore();
          } else {
            const win = this.windowManager.getMainWindow();
            win?.webContents.send("zarvis:system:restartSubsystem", "python-core");
          }
        },
      },
      {
        label: "Restart Node Gateway",
        click: () => {
          if (this.callbacks?.onRestartGateway) {
            this.callbacks.onRestartGateway();
          } else {
            const win = this.windowManager.getMainWindow();
            win?.webContents.send("zarvis:system:restartSubsystem", "node-gateway");
          }
        },
      },
      { type: "separator" },
      {
        label: "Quit ZARVIS",
        click: () => this.onQuit(),
      },
    ]);

    this.tray.setContextMenu(contextMenu);
  }

  private loadTrayIcon(): Electron.NativeImage {
    const candidatePaths = [
      path.join(__dirname, "../../assets/tray.png"),
      path.join(__dirname, "../assets/tray.png"),
      path.join(process.cwd(), "apps/desktop/assets/tray.png"),
      path.join(process.cwd(), "assets/tray.png"),
    ];

    for (const p of candidatePaths) {
      if (fs.existsSync(p)) {
        return nativeImage.createFromPath(p);
      }
    }

    return nativeImage.createEmpty();
  }

  public destroy(): void {
    if (this.tray) {
      this.tray.destroy();
      this.tray = null;
    }
  }
}
