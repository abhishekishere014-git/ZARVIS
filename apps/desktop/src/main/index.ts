/**
 * ZARVIS Electron Main Process Entry Point.
 */

import { app, ipcMain } from "electron";
import * as path from "node:path";
import { WindowManager } from "./window-manager";
import { SystemTrayManager } from "./tray";
import { HotkeyManager } from "./hotkeys";
import { NotificationManager, NotificationPayload } from "./notifications";

const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  let windowManager: WindowManager | null = null;
  let trayManager: SystemTrayManager | null = null;
  let hotkeyManager: HotkeyManager | null = null;

  const preloadPath = path.join(__dirname, "../preload/index.js");
  const htmlPath = path.join(__dirname, "../renderer/index.html");

  const gatewayUrl = process.env.GATEWAY_URL || "ws://127.0.0.1:3000/ws";

  app.on("second-instance", () => {
    if (windowManager) {
      windowManager.showAndFocus();
    }
  });

  app.whenReady().then(() => {
    windowManager = new WindowManager(preloadPath, htmlPath);
    windowManager.createWindow();

    const onActivateVoice = () => {
      const win = windowManager?.getMainWindow();
      win?.webContents.send("zarvis:voice:activate");
    };

    const onQuit = () => {
      windowManager?.setQuitting(true);
      app.quit();
    };

    trayManager = new SystemTrayManager(windowManager, onQuit, onActivateVoice);
    trayManager.createTray();

    hotkeyManager = new HotkeyManager(windowManager, onActivateVoice);
    hotkeyManager.register("CommandOrControl+Space");

    // IPC Handlers
    ipcMain.on("zarvis:window:minimize", () => {
      windowManager?.getMainWindow()?.minimize();
    });

    ipcMain.on("zarvis:window:maximize", () => {
      const win = windowManager?.getMainWindow();
      if (win?.isMaximized()) {
        win.unmaximize();
      } else {
        win?.maximize();
      }
    });

    ipcMain.on("zarvis:window:close", () => {
      windowManager?.getMainWindow()?.close();
    });

    ipcMain.handle("zarvis:window:setMode", async (_, mode: "full" | "hud") => {
      await windowManager?.setMode(mode);
    });

    ipcMain.handle("zarvis:window:getMode", () => {
      return windowManager?.getMode() ?? "full";
    });

    ipcMain.handle("zarvis:window:togglePin", () => {
      return windowManager?.togglePin() ?? false;
    });

    ipcMain.handle("zarvis:window:isPinned", () => {
      return windowManager?.getIsPinned() ?? false;
    });

    ipcMain.on("zarvis:voice:stateChanged", (_, state: string) => {
      trayManager?.updateStatus(state);
    });

    ipcMain.on("zarvis:tray:updateStatus", (_, { statusText }: { statusText: string }) => {
      trayManager?.updateStatus(statusText);
    });

    ipcMain.on("zarvis:notification:show", (_, payload: NotificationPayload) => {
      NotificationManager.show(payload);
    });

    ipcMain.handle("zarvis:system:getGatewayUrl", () => {
      return gatewayUrl;
    });
  });

  app.on("will-quit", () => {
    hotkeyManager?.unregisterAll();
    trayManager?.destroy();
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
      app.quit();
    }
  });
}
