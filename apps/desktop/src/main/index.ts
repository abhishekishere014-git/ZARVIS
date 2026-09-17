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
import { RuntimeResolver } from "./runtime-resolver";

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

  const runtimeResolver = new RuntimeResolver({
    isPackaged: !isDev,
    projectRoot,
    resourcesPath: process.resourcesPath,
  });

  const pyRuntime = runtimeResolver.resolvePythonCore();
  const pythonCoreConfig: ServiceConfig = {
    name: "python-core",
    command: pyRuntime.command,
    args: pyRuntime.args,
    port: 8765,
    cwd: pyRuntime.cwd,
  };

  const nodeRuntime = runtimeResolver.resolveNodeGateway();
  const nodeGatewayConfig: ServiceConfig = {
    name: "node-gateway",
    command: nodeRuntime.command,
    args: nodeRuntime.args,
    port: 3000,
    cwd: nodeRuntime.cwd,
    env: {
      NODE_PATH: path.join(nodeRuntime.cwd, "vendor"),
    },
  };

  app.on("second-instance", () => {
    if (windowManager) {
      windowManager.showAndFocus();
    }
  });

  app.whenReady().then(async () => {
    // 1. Initialize Window Manager and Supervisor instances
    windowManager = new WindowManager(preloadPath, htmlPath);
    supervisor = new ProcessSupervisor(projectRoot);

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

    // 2. Register ALL IPC Handlers BEFORE window creation so renderer never gets unhandled calls
    ipcMain.on("zarvis:window:minimize", () => {
      windowManager?.minimize();
    });

    ipcMain.on("zarvis:window:maximize", () => {
      windowManager?.maximize();
    });

    ipcMain.on("zarvis:window:unmaximize", () => {
      windowManager?.unmaximize();
    });

    ipcMain.handle("zarvis:window:toggleMaximize", () => {
      return windowManager?.toggleMaximize() ?? false;
    });

    ipcMain.handle("zarvis:window:isMaximized", () => {
      return windowManager?.isMaximized() ?? false;
    });

    ipcMain.on("zarvis:window:close", () => {
      windowManager?.close();
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

    ipcMain.handle("zarvis:system:getDiagnostics", () => {
      return {
        validation: runtimeResolver.validateAll(),
        processes: supervisor ? [
          supervisor.getStatus("python-core", 8765),
          supervisor.getStatus("node-gateway", 3000),
        ] : [],
      };
    });

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

    // 5. Create Main Window
    windowManager.createWindow();

    // 6. Validate runtimes before spawning and notify UI if any files missing
    const validation = runtimeResolver.validateAll();
    const win = windowManager.getMainWindow();

    if (!validation.ok) {
      console.warn("Runtime validation warning:", validation.errors);
      win?.webContents.on("did-finish-load", () => {
        win.webContents.send("zarvis:system:runtimeError", {
          errors: validation.errors,
          diagnostics: validation.diagnostics,
        });
      });
      NotificationManager.show({
        title: "ZARVIS Runtime Notice",
        body: "Backend runtime files missing. Running in UI diagnostic mode.",
        level: "warning",
      });
    }

    // 7. Start background services sequentially: Python Core FIRST, then Node Gateway
    (async () => {
      try {
        if (pyRuntime.exists) {
          const pyStatus = await supervisor.startService(pythonCoreConfig);
          console.log(`[Supervisor] Python Core initialized: state=${pyStatus.state}, port=${pyStatus.port}`);
        }
        if (nodeRuntime.exists) {
          const gwStatus = await supervisor.startService(nodeGatewayConfig);
          console.log(`[Supervisor] Node Gateway initialized: state=${gwStatus.state}, port=${gwStatus.port}`);
        }

        const win = windowManager.getMainWindow();
        if (win && !win.isDestroyed()) {
          win.webContents.send("zarvis:system:supervisorReady", {
            python: supervisor.getStatus("python-core", 8765),
            gateway: supervisor.getStatus("node-gateway", 3000),
          });
        }
      } catch (err) {
        console.warn("Service sequential start warning:", err);
      }
    })();
  });

  app.on("before-quit", () => {
    supervisor?.stopAllSync();
  });

  app.on("will-quit", () => {
    supervisor?.stopAllSync();
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
