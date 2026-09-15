/**
 * ZARVIS Preload Script.
 * Strictly isolates the renderer and exposes only typed bridge functions.
 */

import { contextBridge, ipcRenderer } from "electron";
import { ZarvisBridgeApi } from "./types";

const api: ZarvisBridgeApi = {
  window: {
    minimize: () => ipcRenderer.send("zarvis:window:minimize"),
    maximize: () => ipcRenderer.send("zarvis:window:maximize"),
    close: () => ipcRenderer.send("zarvis:window:close"),
    setMode: (mode) => ipcRenderer.invoke("zarvis:window:setMode", mode),
    getMode: () => ipcRenderer.invoke("zarvis:window:getMode"),
    togglePin: () => ipcRenderer.invoke("zarvis:window:togglePin"),
    isPinned: () => ipcRenderer.invoke("zarvis:window:isPinned"),
    onModeChange: (callback) => {
      const listener = (_: any, mode: "full" | "hud") => callback(mode);
      ipcRenderer.on("zarvis:mode:changed", listener);
      return () => ipcRenderer.removeListener("zarvis:mode:changed", listener);
    },
  },
  voice: {
    notifyStateChange: (state) => ipcRenderer.send("zarvis:voice:stateChanged", state),
    onActivateVoice: (callback) => {
      const listener = () => callback();
      ipcRenderer.on("zarvis:voice:activate", listener);
      return () => ipcRenderer.removeListener("zarvis:voice:activate", listener);
    },
    onMuteToggle: (callback) => {
      const listener = () => callback();
      ipcRenderer.on("zarvis:voice:muteToggle", listener);
      return () => ipcRenderer.removeListener("zarvis:voice:muteToggle", listener);
    },
  },
  tray: {
    updateStatus: (statusText, stateColor) =>
      ipcRenderer.send("zarvis:tray:updateStatus", { statusText, stateColor }),
  },
  notifications: {
    show: (title, body, level) =>
      ipcRenderer.send("zarvis:notification:show", { title, body, level }),
  },
  system: {
    getGatewayUrl: () => ipcRenderer.invoke("zarvis:system:getGatewayUrl"),
    getVersion: () => "1.0.0",
    onRestartSubsystem: (callback) => {
      const listener = (_: any, subsystem: string) => callback(subsystem);
      ipcRenderer.on("zarvis:system:restartSubsystem", listener);
      return () => ipcRenderer.removeListener("zarvis:system:restartSubsystem", listener);
    },
    onNavigateTab: (callback) => {
      const listener = (_: any, tab: string) => callback(tab);
      ipcRenderer.on("zarvis:navigation:switchTab", listener);
      return () => ipcRenderer.removeListener("zarvis:navigation:switchTab", listener);
    },
    onPauseToggle: (callback) => {
      const listener = (_: any, isPaused: boolean) => callback(isPaused);
      ipcRenderer.on("zarvis:assistant:pauseToggle", listener);
      return () => ipcRenderer.removeListener("zarvis:assistant:pauseToggle", listener);
    },
  },
};

// Expose safe API to the renderer process
contextBridge.exposeInMainWorld("zarvis", api);
