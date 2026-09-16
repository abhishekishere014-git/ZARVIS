/**
 * Authoritative Runtime Resolver for ZARVIS Desktop.
 * Resolves and validates Python Core and Node Gateway executables and entrypoints
 * for both development and packaged (production) environments.
 * Strictly guarantees that missing runtimes produce structured diagnostic errors
 * rather than unhandled spawn ENOENT exceptions.
 */

import * as fs from "node:fs";
import * as path from "node:path";

export interface ResolvedServiceRuntime {
  name: "python-core" | "node-gateway";
  command: string;
  args: string[];
  cwd: string;
  exists: boolean;
  error?: string;
}

export interface RuntimeValidationResult {
  ok: boolean;
  services: {
    pythonCore: ResolvedServiceRuntime;
    nodeGateway: ResolvedServiceRuntime;
  };
  errors: string[];
  diagnostics: {
    isPackaged: boolean;
    resourcesPath: string;
    projectRoot: string;
  };
}

export class RuntimeResolver {
  private readonly isPackaged: boolean;
  private readonly projectRoot: string;
  private readonly resourcesPath: string;

  constructor(options?: { isPackaged?: boolean; projectRoot?: string; resourcesPath?: string }) {
    this.isPackaged = options?.isPackaged ?? false;
    this.projectRoot = options?.projectRoot ?? path.resolve(__dirname, "../../..");
    this.resourcesPath = options?.resourcesPath ?? process.resourcesPath ?? this.projectRoot;
  }

  public resolvePythonCore(): ResolvedServiceRuntime {
    const isWin = process.platform === "win32";

    let executable: string;
    let script: string;
    let cwd: string;

    if (this.isPackaged) {
      executable = isWin
        ? path.join(this.resourcesPath, "python", "python.exe")
        : path.join(this.resourcesPath, "python", "bin", "python");
      script = path.join(this.resourcesPath, "python-core", "jarvis", "__main__.py");
      cwd = path.join(this.resourcesPath, "python-core");
    } else {
      executable = isWin
        ? path.join(this.projectRoot, ".venv", "Scripts", "python.exe")
        : path.join(this.projectRoot, ".venv", "bin", "python");
      script = path.join(this.projectRoot, "services", "python-core", "jarvis", "__main__.py");
      cwd = path.join(this.projectRoot, "services", "python-core");
    }

    const exeExists = fs.existsSync(executable);
    const scriptExists = fs.existsSync(script);
    const exists = exeExists && scriptExists;

    let error: string | undefined;
    if (!exeExists) {
      error = `Python interpreter executable not found: "${executable}"`;
    } else if (!scriptExists) {
      error = `Python Core entrypoint script not found: "${script}"`;
    }

    return {
      name: "python-core",
      command: executable,
      args: [script],
      cwd,
      exists,
      error,
    };
  }

  public resolveNodeGateway(): ResolvedServiceRuntime {
    const isWin = process.platform === "win32";

    let executable: string;
    let script: string;
    let cwd: string;

    if (this.isPackaged) {
      executable = isWin
        ? path.join(this.resourcesPath, "node", "node.exe")
        : path.join(this.resourcesPath, "node", "bin", "node");
      script = path.join(this.resourcesPath, "node-gateway", "dist", "index.js");
      cwd = path.join(this.resourcesPath, "node-gateway");
    } else {
      executable = isWin ? "node.exe" : "node";
      script = path.join(this.projectRoot, "services", "node-gateway", "dist", "index.js");
      cwd = path.join(this.projectRoot, "services", "node-gateway");
    }

    // In dev mode, 'node' is assumed to be in system PATH if executable is not an absolute path
    const exeExists = path.isAbsolute(executable) ? fs.existsSync(executable) : true;
    const scriptExists = fs.existsSync(script);
    const exists = exeExists && scriptExists;

    let error: string | undefined;
    if (!exeExists) {
      error = `Node.js runtime executable not found: "${executable}"`;
    } else if (!scriptExists) {
      error = `Node Gateway entrypoint script not found: "${script}"`;
    }

    return {
      name: "node-gateway",
      command: executable,
      args: [script],
      cwd,
      exists,
      error,
    };
  }

  public validateAll(): RuntimeValidationResult {
    const pythonCore = this.resolvePythonCore();
    const nodeGateway = this.resolveNodeGateway();

    const errors: string[] = [];
    if (!pythonCore.exists && pythonCore.error) {
      errors.push(pythonCore.error);
    }
    if (!nodeGateway.exists && nodeGateway.error) {
      errors.push(nodeGateway.error);
    }

    return {
      ok: errors.length === 0,
      services: {
        pythonCore,
        nodeGateway,
      },
      errors,
      diagnostics: {
        isPackaged: this.isPackaged,
        resourcesPath: this.resourcesPath,
        projectRoot: this.projectRoot,
      },
    };
  }
}
