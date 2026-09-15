/**
 * Process Supervisor for ZARVIS Desktop.
 * Manages Python Core and Node Gateway child processes, preventing orphans,
 * zombies, and duplicate instances across process lifecycle and restarts.
 */

import { spawn, execSync, ChildProcess } from "node:child_process";
import * as fs from "node:fs";
import * as net from "node:net";
import * as path from "node:path";

export interface ServiceConfig {
  name: "python-core" | "node-gateway";
  command: string;
  args: string[];
  port: number;
  cwd: string;
  env?: Record<string, string>;
}

export interface ServiceStatus {
  name: string;
  running: boolean;
  pid: number | null;
  port: number;
  external: boolean;
}

export class ProcessSupervisor {
  private processes: Map<string, ChildProcess> = new Map();
  private pids: Map<string, number> = new Map();
  private pidDir: string;
  private isShuttingDown = false;

  constructor(private readonly projectRoot: string) {
    this.pidDir = path.join(this.projectRoot, ".zarvis", "pids");
    this.ensurePidDirectory();
    this.cleanupStalePids();
  }

  private ensurePidDirectory(): void {
    try {
      if (!fs.existsSync(this.pidDir)) {
        fs.mkdirSync(this.pidDir, { recursive: true });
      }
    } catch {
      // fallback to temp directory
      this.pidDir = path.join(process.env.TEMP || process.cwd(), "zarvis_pids");
      if (!fs.existsSync(this.pidDir)) {
        fs.mkdirSync(this.pidDir, { recursive: true });
      }
    }
  }

  /**
   * Check whether a given TCP port is currently open/bound.
   */
  public async isPortInUse(port: number, host = "127.0.0.1"): Promise<boolean> {
    return new Promise((resolve) => {
      const socket = new net.Socket();
      socket.setTimeout(400);

      socket.once("connect", () => {
        socket.destroy();
        resolve(true);
      });

      socket.once("timeout", () => {
        socket.destroy();
        resolve(false);
      });

      socket.once("error", () => {
        socket.destroy();
        resolve(false);
      });

      socket.connect(port, host);
    });
  }

  /**
   * Cleans up stale PID files left over from prior crashes or forced shutdowns.
   */
  public cleanupStalePids(): void {
    try {
      if (!fs.existsSync(this.pidDir)) return;
      const files = fs.readdirSync(this.pidDir);
      for (const file of files) {
        if (file.endsWith(".pid")) {
          const filePath = path.join(this.pidDir, file);
          try {
            const pid = parseInt(fs.readFileSync(filePath, "utf-8").trim(), 10);
            if (!isNaN(pid) && pid > 0) {
              if (this.isProcessRunning(pid)) {
                // Terminate stale zombie process
                this.killProcessTree(pid);
              }
            }
            fs.unlinkSync(filePath);
          } catch {
            // Ignore if file cannot be parsed or unlinked
          }
        }
      }
    } catch {
      // non-fatal
    }
  }

  /**
   * Checks if a process with the given PID is actively running.
   */
  public isProcessRunning(pid: number): boolean {
    if (!Number.isInteger(pid) || pid <= 0 || pid > 2147483647) {
      return false;
    }
    try {
      if (process.platform === "win32") {
        const stdout = execSync(`tasklist /FI "PID eq ${pid}" /NH`, { encoding: "utf-8" });
        return stdout.toLowerCase().includes(String(pid));
      } else {
        process.kill(pid, 0);
        return true;
      }
    } catch {
      return false;
    }
  }

  /**
   * Recursively terminates a process and all of its child processes to prevent orphans.
   */
  public killProcessTree(pid: number): void {
    if (!Number.isInteger(pid) || pid <= 0 || pid > 2147483647) {
      return;
    }
    try {
      if (process.platform === "win32") {
        execSync(`taskkill /pid ${pid} /T /F`, { stdio: "ignore" });
      } else {
        process.kill(-pid, "SIGKILL");
      }
    } catch {
      // Process may already have terminated
    }
  }

  /**
   * Starts a service if it is not already running.
   * Prevents duplicate instances.
   */
  public async startService(config: ServiceConfig): Promise<ServiceStatus> {
    const portActive = await this.isPortInUse(config.port);
    if (portActive) {
      // Service is already running externally (e.g. in dev mode or prior instance)
      return {
        name: config.name,
        running: true,
        pid: null,
        port: config.port,
        external: true,
      };
    }

    if (this.processes.has(config.name)) {
      const existing = this.processes.get(config.name)!;
      if (existing.exitCode === null && !existing.killed) {
        return {
          name: config.name,
          running: true,
          pid: existing.pid ?? null,
          port: config.port,
          external: false,
        };
      }
    }

    // Spawn child process
    const child = spawn(config.command, config.args, {
      cwd: config.cwd,
      env: { ...process.env, ...config.env },
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
      detached: false,
    });

    if (child.pid) {
      this.processes.set(config.name, child);
      this.pids.set(config.name, child.pid);
      this.writePidFile(config.name, child.pid);

      child.on("exit", (code, signal) => {
        this.processes.delete(config.name);
        this.pids.delete(config.name);
        this.removePidFile(config.name);
      });
    }

    // Wait briefly for service port to become available (up to 3s)
    let ready = false;
    for (let i = 0; i < 30; i++) {
      if (await this.isPortInUse(config.port)) {
        ready = true;
        break;
      }
      await new Promise((res) => setTimeout(res, 100));
    }

    return {
      name: config.name,
      running: ready,
      pid: child.pid ?? null,
      port: config.port,
      external: false,
    };
  }

  /**
   * Stops a specific managed service cleanly.
   */
  public async stopService(name: string): Promise<boolean> {
    const child = this.processes.get(name);
    const pid = this.pids.get(name);

    if (!child && !pid) {
      return false;
    }

    if (child && child.pid) {
      try {
        child.kill("SIGTERM");
      } catch {}

      // Wait up to 1000ms for graceful exit
      const exited = await new Promise<boolean>((resolve) => {
        const timer = setTimeout(() => resolve(false), 1000);
        child.once("exit", () => {
          clearTimeout(timer);
          resolve(true);
        });
      });

      if (!exited && child.pid) {
        this.killProcessTree(child.pid);
      }
    } else if (pid) {
      this.killProcessTree(pid);
    }

    this.processes.delete(name);
    this.pids.delete(name);
    this.removePidFile(name);
    return true;
  }

  /**
   * Cleanly restarts a managed service.
   */
  public async restartService(config: ServiceConfig): Promise<ServiceStatus> {
    await this.stopService(config.name);

    // Wait until port is freed
    for (let i = 0; i < 20; i++) {
      if (!(await this.isPortInUse(config.port))) {
        break;
      }
      await new Promise((res) => setTimeout(res, 100));
    }

    return this.startService(config);
  }

  /**
   * Gracefully shuts down all managed child processes.
   * Guarantees zero orphan processes on application exit.
   */
  public async stopAll(): Promise<void> {
    if (this.isShuttingDown) return;
    this.isShuttingDown = true;

    for (const [name, child] of this.processes.entries()) {
      if (child.pid) {
        try {
          child.kill("SIGINT");
        } catch {}
      }
    }

    // Wait up to 500ms
    await new Promise((res) => setTimeout(res, 500));

    // Forcefully kill process trees for any remaining processes
    for (const [name, child] of this.processes.entries()) {
      if (child.pid && child.exitCode === null) {
        this.killProcessTree(child.pid);
      }
      this.removePidFile(name);
    }

    this.processes.clear();
    this.pids.clear();
  }

  public getStatus(name: string, port: number): ServiceStatus {
    const child = this.processes.get(name);
    const isManaged = !!(child && child.exitCode === null);
    return {
      name,
      running: isManaged,
      pid: child?.pid ?? null,
      port,
      external: !isManaged,
    };
  }

  private writePidFile(name: string, pid: number): void {
    try {
      const filePath = path.join(this.pidDir, `${name}.pid`);
      fs.writeFileSync(filePath, String(pid), "utf-8");
    } catch {}
  }

  private removePidFile(name: string): void {
    try {
      const filePath = path.join(this.pidDir, `${name}.pid`);
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    } catch {}
  }
}
