/**
 * ZARVIS Electron Main Process Entry Point.
 * Orchestrates Window Lifecycle, System Tray, Global Hotkeys, Native Notifications,
 * and Child Process Lifecycle Supervision (Python Core & Node Gateway).
 */

import { app, ipcMain } from "electron";
import * as path from "node:path";
import { WindowManager } from "./window-manager";
import { SystemTrayManager } from "./tray";
import { HotkeyManager } from "./hotkeys";
import { NotificationManager, NotificationPayload } from "./notifications";
import { ProcessSupervisor, ServiceConfig } from "./supervisor";

const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  let windowManager: WindowManager | null = null;
  let trayManager: SystemTrayManager | null = null;
  let hotkeyManager: HotkeyManager | null = null;
  let supervisor: ProcessSupervisor | null = null;

  const isDev = !app.isPackaged;
  const projectRoot = isDev ? path.resolve(__dirname, "../../..") : process.resourcesPath;
  const preloadPath = path.join(__dirname, "../preload/index.js");
  const htmlPath = path.join(__dirname, "../renderer/index.html");

  const gatewayUrl = process.env.GATEWAY_URL || "ws://127.0.0.1:3000/ws";

  const pythonExecutable = isDev
    ? (process.platform === "win32"
        ? path.join(projectRoot, ".venv", "Scripts", "python.exe")
        : path.join(projectRoot, ".venv", "bin", "python"))
    : (process.platform === "win32"
        ? path.join(process.resourcesPath, "python", "python.exe")
        : path.join(process.resourcesPath, "python", "bin", "python"));

  const pythonScript = isDev
    ? path.join(projectRoot, "services", "python-core", "jarvis", "__main__.py")
    : path.join(process.resourcesPath, "python-core", "jarvis", "__main__.py");

  const pythonCoreConfig: ServiceConfig = {
    name: "python-core",
    command: pythonExecutable,
    args: [pythonScript],
    port: 8765,
    cwd: isDev ? projectRoot : process.resourcesPath,
  };

  const nodeGatewayScript = isDev
    ? path.join(projectRoot, "services", "node-gateway", "dist", "index.js")
    : path.join(process.resourcesPath, "node-gateway", "dist", "index.js");

  const nodeGatewayConfig: ServiceConfig = {
    name: "node-gateway",
    command: isDev ? "node" : (process.platform === "win32" ? path.join(process.resourcesPath, "node", "node.exe") : "node"),
    args: [nodeGatewayScript],
    port: 3000,
    cwd: isDev ? path.join(projectRoot, "services", "node-gateway") : path.join(process.resourcesPath, "node-gateway"),
  };

  app.on("second-instance", () => {
    if (windowManager) {
      windowManager.showAndFocus();
    }
  });

  app.whenReady().then(async () => {
    // 1. Initialize Window Manager
    windowManager = new WindowManager(preloadPath, htmlPath);
    windowManager.createWindow();

    // 2. Initialize Process Supervisor
    supervisor = new ProcessSupervisor(projectRoot);

    // Supervised start (auto-attach if already running in dev mode, or spawn)
    try {
      await supervisor.startService(pythonCoreConfig);
      await supervisor.startService(nodeGatewayConfig);
    } catch (err) {
      console.warn("Service auto-start warning:", err);
    }

    const onActivateVoice = () => {
      const win = windowManager?.getMainWindow();
      win?.webContents.send("zarvis:voice:activate");
    };

    const onQuit = async () => {
      windowManager?.setQuitting(true);
      if (supervisor) {
        await supervisor.stopAll();
      }
      app.quit();
    };

    const onRestartCore = async () => {
      const win = windowManager?.getMainWindow();
      win?.webContents.send("zarvis:system:restartSubsystem", "python-core");
      NotificationManager.show({
        title: "Process Supervisor",
        body: "Restarting Python Core daemon...",
        level: "info",
      });
      if (supervisor) {
        await supervisor.restartService(pythonCoreConfig);
      }
    };

    const onRestartGateway = async () => {
      const win = windowManager?.getMainWindow();
      win?.webContents.send("zarvis:system:restartSubsystem", "node-gateway");
      NotificationManager.show({
        title: "Process Supervisor",
        body: "Restarting Node Gateway service...",
        level: "info",
      });
      if (supervisor) {
        await supervisor.restartService(nodeGatewayConfig);
      }
    };

    // 3. Initialize System Tray
    trayManager = new SystemTrayManager(windowManager, onQuit, onActivateVoice, {
      onQuit,
      onActivateVoice,
      onRestartCore,
      onRestartGateway,
      onNavigateTab: (tab) => {
        windowManager?.getMainWindow()?.webContents.send("zarvis:navigation:switchTab", tab);
      },
      onTogglePause: (isPaused) => {
        windowManager?.getMainWindow()?.webContents.send("zarvis:assistant:pauseToggle", isPaused);
      },
    });
    trayManager.createTray();

    // 4. Initialize Global Hotkeys
    hotkeyManager = new HotkeyManager(windowManager, onActivateVoice);
    const hotkeyRes = hotkeyManager.register("CommandOrControl+Space");
    if (!hotkeyRes.success) {
      console.warn("Global hotkey registration notice:", hotkeyRes.error);
    }

    // 5. IPC Handlers
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

    ipcMain.handle("zarvis:system:restartProcess", async (_, processName: "python-core" | "node-gateway") => {
      if (processName === "python-core") {
        await onRestartCore();
      } else if (processName === "node-gateway") {
        await onRestartGateway();
      }
      return true;
    });

    ipcMain.handle("zarvis:system:getProcessStatus", () => {
      if (!supervisor) return [];
      return [
        supervisor.getStatus("python-core", 8765),
        supervisor.getStatus("node-gateway", 3000),
      ];
    });
  });

  app.on("before-quit", async (e) => {
    if (supervisor) {
      await supervisor.stopAll();
    }
  });

  app.on("will-quit", () => {
    hotkeyManager?.unregisterAll();
    trayManager?.destroy();
    windowManager?.destroy();
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
      app.quit();
    }
  });
}
