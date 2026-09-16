/**
 * Automated GitHub Release Publisher for ZARVIS.
 * Uses GitHub REST API to publish v0.1.0 release with installer & checksum assets.
 */

const fs = require("node:fs");
const path = require("node:path");
const https = require("node:https");
const { execSync } = require("node:child_process");

// 1. Retrieve Git token
function getGitHubToken() {
  try {
    const stdout = execSync("git credential fill", {
      input: "protocol=https\nhost=github.com\n",
      encoding: "utf-8",
    });
    const match = stdout.match(/password=(.+)/);
    if (match && match[1]) {
      return match[1].trim();
    }
  } catch (err) {
    console.error("Failed to retrieve git credentials:", err);
  }
  return null;
}

const token = getGitHubToken();
if (!token) {
  console.error("Could not obtain GitHub authorization token.");
  process.exit(1);
}

const OWNER = "abhishekishere014-git";
const REPO = "ZARVIS";
const TAG = "v0.1.0";
const RELEASE_NAME = "ZARVIS v0.1.0 - Production Release";
const NOTES_PATH = path.join(__dirname, "..", "RELEASE_v0.1.0.md");
const notesContent = fs.existsSync(NOTES_PATH) ? fs.readFileSync(NOTES_PATH, "utf-8") : "Initial Production Release";

function request(options, postData = null) {
  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        let json = null;
        try {
          json = JSON.parse(data);
        } catch {
          json = data;
        }
        resolve({ statusCode: res.statusCode, data: json });
      });
    });
    req.on("error", reject);
    if (postData) {
      req.write(postData);
    }
    req.end();
  });
}

async function main() {
  console.log("Checking for existing release for tag:", TAG);
  let release = null;

  const getRes = await request({
    hostname: "api.github.com",
    path: `/repos/${OWNER}/${REPO}/releases/tags/${TAG}`,
    method: "GET",
    headers: {
      "User-Agent": "ZARVIS-Release-Script",
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
    },
  });

  if (getRes.statusCode === 200) {
    release = getRes.data;
    console.log(`Found existing release: ID ${release.id}`);
    console.log("Updating release body and name...");
    const updateBody = JSON.stringify({
      name: RELEASE_NAME,
      body: notesContent,
    });
    await request(
      {
        hostname: "api.github.com",
        path: `/repos/${OWNER}/${REPO}/releases/${release.id}`,
        method: "PATCH",
        headers: {
          "User-Agent": "ZARVIS-Release-Script",
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(updateBody),
        },
      },
      updateBody
    );
  } else {
    console.log("Creating new GitHub release...");
    const createBody = JSON.stringify({
      tag_name: TAG,
      target_commitish: "master",
      name: RELEASE_NAME,
      body: notesContent,
      draft: false,
      prerelease: false,
    });

    const createRes = await request(
      {
        hostname: "api.github.com",
        path: `/repos/${OWNER}/${REPO}/releases`,
        method: "POST",
        headers: {
          "User-Agent": "ZARVIS-Release-Script",
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(createBody),
        },
      },
      createBody
    );

    if (createRes.statusCode === 201) {
      release = createRes.data;
      console.log(`Created release successfully: ID ${release.id}`);
    } else {
      console.error("Failed to create release:", createRes.statusCode, createRes.data);
      process.exit(1);
    }
  }

  const releaseId = release.id;

  // Helper to upload assets
  async function uploadFile(filePath, contentType) {
    const fileName = path.basename(filePath);
    console.log(`\nPreparing ${fileName}...`);
    const fileStats = fs.statSync(filePath);

    // Refresh live assets from GitHub
    const assetsRes = await request({
      hostname: "api.github.com",
      path: `/repos/${OWNER}/${REPO}/releases/${releaseId}/assets`,
      method: "GET",
      headers: {
        "User-Agent": "ZARVIS-Release-Script",
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
      },
    });

    if (assetsRes.statusCode === 200 && Array.isArray(assetsRes.data)) {
      const existing = assetsRes.data.find((a) => a.name === fileName);
      if (existing) {
        console.log(`Deleting duplicate existing asset (ID: ${existing.id})...`);
        await request({
          hostname: "api.github.com",
          path: `/repos/${OWNER}/${REPO}/releases/assets/${existing.id}`,
          method: "DELETE",
          headers: {
            "User-Agent": "ZARVIS-Release-Script",
            Authorization: `Bearer ${token}`,
            Accept: "application/vnd.github+json",
          },
        });
        // Small pause after deletion
        await new Promise((res) => setTimeout(res, 2000));
      }
    }

    console.log(`Uploading ${fileName} (${(fileStats.size / (1024 * 1024)).toFixed(1)} MB) via curl.exe...`);
    const uploadUrl = `https://uploads.github.com/repos/${OWNER}/${REPO}/releases/${releaseId}/assets?name=${encodeURIComponent(fileName)}`;

    const curlCmd = [
      "curl.exe",
      "-sS",
      "--fail-with-body",
      "--connect-timeout", "30",
      "--max-time", "600",
      "--retry", "3",
      "--retry-delay", "5",
      "-X", "POST",
      "-H", "User-Agent: ZARVIS-Release-Script",
      "-H", `Authorization: Bearer ${token}`,
      "-H", "Accept: application/vnd.github+json",
      "-H", `Content-Type: ${contentType}`,
      "--data-binary", `@${filePath}`,
      uploadUrl,
    ];

    try {
      const result = execSync(curlCmd.map((arg) => (arg.startsWith("@") || arg.includes(" ") || arg.includes(":") || arg.includes("?")) ? `"${arg}"` : arg).join(" "), {
        encoding: "utf-8",
        maxBuffer: 20 * 1024 * 1024,
      });
      console.log(`Uploaded ${fileName} successfully!`);
      return JSON.parse(result);
    } catch (err) {
      console.error(`Curl upload failed for ${fileName}:`, err.message);
      if (err.stdout) console.error("Stdout:", err.stdout);
      if (err.stderr) console.error("Stderr:", err.stderr);
      throw err;
    }
  }

  // 1. Upload SHA256SUMS.txt
  const checksumPath = path.join(__dirname, "..", "apps", "desktop", "release", "SHA256SUMS.txt");
  if (fs.existsSync(checksumPath)) {
    await uploadFile(checksumPath, "text/plain");
  }

  // 2. Upload Installer
  const installerPath = path.join(__dirname, "..", "apps", "desktop", "release", "ZARVIS-Setup-0.1.0.exe");
  if (fs.existsSync(installerPath)) {
    await uploadFile(installerPath, "application/vnd.microsoft.portable-executable");
  } else {
    console.error("Installer not found at:", installerPath);
  }

  // 3. Upload Portable Executable
  const portablePath = path.join(__dirname, "..", "apps", "desktop", "release", "ZARVIS 0.1.0.exe");
  if (fs.existsSync(portablePath)) {
    await uploadFile(portablePath, "application/vnd.microsoft.portable-executable");
  } else {
    console.warn("Portable executable not found at:", portablePath);
  }

  console.log("\n========================================================");
  console.log("GitHub Release Published Successfully!");
  console.log(`URL: ${release.html_url}`);
  console.log("========================================================");
}

main().catch((err) => {
  console.error("Fatal release publication error:", err);
  process.exit(1);
});
