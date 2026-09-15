/**
 * Windows System Tray integration for ZARVIS.
 */

import { Menu, Tray, nativeImage, app } from "electron";
import { WindowManager } from "./window-manager";

export class SystemTrayManager {
  private tray: Tray | null = null;
  private statusText = "Online • Ready";

  constructor(
    private readonly windowManager: WindowManager,
    private readonly onQuit: () => void,
    private readonly onActivateVoice: () => void
  ) {}

  public createTray(): Tray {
    // Generate a simple circular 16x16 icon programmatically if file not found
    const icon = this.createDefaultIcon();
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
        click: () => {
          // Toggle mute event
          const win = this.windowManager.getMainWindow();
          win?.webContents.send("zarvis:voice:muteToggle");
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
          const win = this.windowManager.getMainWindow();
          win?.webContents.send("zarvis:system:restartSubsystem", "python-core");
        },
      },
      {
        label: "Restart Node Gateway",
        click: () => {
          const win = this.windowManager.getMainWindow();
          win?.webContents.send("zarvis:system:restartSubsystem", "node-gateway");
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

  private createDefaultIcon(): Electron.NativeImage {
    // 16x16 transparent PNG with a cyan/blue circle dot
    const size = 16;
    const canvas = nativeImage.createEmpty();
    // Return empty image or 16x16 standard icon
    return canvas;
  }

  public destroy(): void {
    if (this.tray) {
      this.tray.destroy();
      this.tray = null;
    }
  }
}
