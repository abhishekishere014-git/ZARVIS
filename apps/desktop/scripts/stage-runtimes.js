/**
 * ZARVIS Packaged Runtime Staging Helper.
 * Prepares fully self-contained, path-independent runtimes for:
 *   - Python 3.12 (standalone interpreter + stdlib + .venv site-packages)
 *   - Python Core (services/python-core/jarvis)
 *   - Node.js (standalone node.exe)
 *   - Node Gateway (services/node-gateway/dist + bundled node_modules)
 *
 * Staged into `apps/desktop/build-resources/` for electron-builder `extraResources`.
 * Guarantees that installed builds contain genuine executables and resolve from
 * `process.resourcesPath` without host machine dependencies.
 */

const fs = require("node:fs");
const path = require("node:path");
const { execSync } = require("node:child_process");

const repoRoot = path.resolve(__dirname, "../../..");
const desktopDir = path.resolve(__dirname, "..");
const buildResourcesDir = path.join(desktopDir, "build-resources");

function copyDirRecursive(src, dest, filterFn) {
  if (!fs.existsSync(src)) return;
  fs.mkdirSync(dest, { recursive: true });
  const entries = fs.readdirSync(src, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (filterFn && !filterFn(srcPath, entry)) {
      continue;
    }

    if (entry.isDirectory()) {
      copyDirRecursive(srcPath, destPath, filterFn);
    } else if (entry.isFile()) {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

function findHostPythonDir() {
  const defaultDir = "C:\\Users\\abhis\\AppData\Local\\Programs\\Python\\Python312";
  if (fs.existsSync(path.join(defaultDir, "python.exe"))) {
    return defaultDir;
  }
  try {
    const whereOut = execSync("where.exe python", { encoding: "utf-8" }).trim();
    const firstLine = whereOut.split(/\r?\n/)[0];
    if (firstLine && fs.existsSync(firstLine)) {
      return path.dirname(firstLine);
    }
  } catch {}
  return null;
}

function findHostNodeExe() {
  const preferred = "C:\\Users\\abhis\\.node\\node-v22.23.2-win-x64\\node.exe";
  if (fs.existsSync(preferred)) {
    return preferred;
  }
  try {
    const whereOut = execSync("where.exe node", { encoding: "utf-8" }).trim();
    const firstLine = whereOut.split(/\r?\n/)[0];
    if (firstLine && fs.existsSync(firstLine)) {
      return firstLine;
    }
  } catch {}
  return null;
}

async function stageAll() {
  console.log("=== STAGING ZARVIS PACKAGED RUNTIMES ===");
  console.log("Target staging directory:", buildResourcesDir);

  // 1. Stage Python Runtime
  const pythonDest = path.join(buildResourcesDir, "python");
  console.log("\n[1/4] Staging Standalone Python Runtime into:", pythonDest);
  fs.mkdirSync(pythonDest, { recursive: true });

  const hostPyDir = findHostPythonDir();
  if (!hostPyDir) {
    throw new Error("Cannot find host Python 3.12 installation to stage standalone runtime.");
  }
  console.log("Using Host Python source:", hostPyDir);

  // Copy Python binaries
  const pyBinaries = [
    "python.exe",
    "python3.dll",
    "python312.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
  ];
  for (const bin of pyBinaries) {
    const src = path.join(hostPyDir, bin);
    if (fs.existsSync(src)) {
      fs.copyFileSync(src, path.join(pythonDest, bin));
    }
  }

  // Copy DLLs
  const dllsSrc = path.join(hostPyDir, "DLLs");
  if (fs.existsSync(dllsSrc)) {
    copyDirRecursive(dllsSrc, path.join(pythonDest, "DLLs"), (srcPath, entry) => {
      return !entry.name.endsWith(".pdb");
    });
  }

  // Copy Python standard library (excluding test directories to save space)
  const libSrc = path.join(hostPyDir, "Lib");
  if (fs.existsSync(libSrc)) {
    copyDirRecursive(libSrc, path.join(pythonDest, "Lib"), (srcPath, entry) => {
      const lower = entry.name.toLowerCase();
      return lower !== "test" && lower !== "tests" && lower !== "idlelib" && lower !== "turtledemo";
    });
  }

  // Copy .venv site-packages into python/Lib/site-packages
  const venvSitePackages = path.join(repoRoot, ".venv", "Lib", "site-packages");
  const destSitePackages = path.join(pythonDest, "Lib", "site-packages");
  console.log("Copying site-packages from:", venvSitePackages);
  if (fs.existsSync(venvSitePackages)) {
    copyDirRecursive(venvSitePackages, destSitePackages, (srcPath, entry) => {
      return entry.name !== "__pycache__" && !entry.name.endsWith(".dist-info");
    });
  }

  // Write isolated python312._pth file for 100% path independence
  const pthContent = [
    "python312.zip",
    ".",
    "DLLs",
    "Lib",
    "Lib/site-packages",
    "../python-core",
  ].join("\r\n");
  fs.writeFileSync(path.join(pythonDest, "python312._pth"), pthContent, "utf-8");
  console.log("Configured python312._pth with isolated relative paths.");

  // 2. Stage Python Core
  const pyCoreDest = path.join(buildResourcesDir, "python-core");
  console.log("\n[2/4] Staging Python Core into:", pyCoreDest);
  if (fs.existsSync(pyCoreDest)) {
    fs.rmSync(pyCoreDest, { recursive: true, force: true });
  }
  fs.mkdirSync(pyCoreDest, { recursive: true });

  const pyCoreSrc = path.join(repoRoot, "services", "python-core", "jarvis");
  copyDirRecursive(pyCoreSrc, path.join(pyCoreDest, "jarvis"), (srcPath, entry) => {
    return entry.name !== "__pycache__" && entry.name !== ".pytest_cache";
  });

  // 3. Stage Node Runtime
  const nodeDest = path.join(buildResourcesDir, "node");
  console.log("\n[3/4] Staging Standalone Node Runtime into:", nodeDest);
  fs.mkdirSync(nodeDest, { recursive: true });

  const hostNodeExe = findHostNodeExe();
  if (!hostNodeExe) {
    throw new Error("Cannot find host node.exe to stage standalone Node runtime.");
  }
  console.log("Using Host Node executable:", hostNodeExe);
  fs.copyFileSync(hostNodeExe, path.join(nodeDest, "node.exe"));

  // 4. Stage Node Gateway
  const nodeGatewayDest = path.join(buildResourcesDir, "node-gateway");
  console.log("\n[4/4] Staging Node Gateway into:", nodeGatewayDest);
  if (fs.existsSync(nodeGatewayDest)) {
    fs.rmSync(nodeGatewayDest, { recursive: true, force: true });
  }
  fs.mkdirSync(nodeGatewayDest, { recursive: true });

  // Copy dist
  copyDirRecursive(
    path.join(repoRoot, "services", "node-gateway", "dist"),
    path.join(nodeGatewayDest, "dist")
  );

  // Copy package.json
  fs.copyFileSync(
    path.join(repoRoot, "services", "node-gateway", "package.json"),
    path.join(nodeGatewayDest, "package.json")
  );

  // Stage self-contained vendor modules for node-gateway (avoids electron-builder node_modules filter)
  const destModules = path.join(nodeGatewayDest, "vendor");
  fs.mkdirSync(destModules, { recursive: true });

  // Copy @jarvis/protocol
  const protocolDest = path.join(destModules, "@jarvis", "protocol");
  fs.mkdirSync(protocolDest, { recursive: true });
  copyDirRecursive(
    path.join(repoRoot, "packages", "protocol", "dist"),
    path.join(protocolDest, "dist")
  );
  fs.copyFileSync(
    path.join(repoRoot, "packages", "protocol", "package.json"),
    path.join(protocolDest, "package.json")
  );

  // Copy ws and zod from node-gateway node_modules, protocol node_modules, or root node_modules
  const searchRoots = [
    path.join(repoRoot, "services", "node-gateway", "node_modules"),
    path.join(repoRoot, "packages", "protocol", "node_modules"),
    path.join(repoRoot, "node_modules"),
  ];

  ["ws", "zod"].forEach((mod) => {
    let found = false;
    for (const sRoot of searchRoots) {
      const srcMod = path.join(sRoot, mod);
      if (fs.existsSync(srcMod)) {
        copyDirRecursive(srcMod, path.join(destModules, mod));
        found = true;
        break;
      }
    }
    if (!found) {
      console.warn(`Warning: Could not find module '${mod}' in search roots`);
    }
  });

  console.log("\n=== RUNTIME STAGING COMPLETE ===");
}

stageAll().catch((err) => {
  console.error("FATAL: Failed to stage runtimes:", err);
  process.exit(1);
});
