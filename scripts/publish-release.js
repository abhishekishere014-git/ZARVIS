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
    console.log(`Uploading ${fileName}...`);
    const fileStats = fs.statSync(filePath);

    // Delete existing asset with same name if present
    if (release.assets && Array.isArray(release.assets)) {
      const existing = release.assets.find((a) => a.name === fileName);
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
      }
    }

    return new Promise((resolve, reject) => {
      const options = {
        hostname: "uploads.github.com",
        path: `/repos/${OWNER}/${REPO}/releases/${releaseId}/assets?name=${encodeURIComponent(fileName)}`,
        method: "POST",
        headers: {
          "User-Agent": "ZARVIS-Release-Script",
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
          "Content-Type": contentType,
          "Content-Length": fileStats.size,
        },
      };

      const req = https.request(options, (res) => {
        let respData = "";
        res.on("data", (chunk) => (respData += chunk));
        res.on("end", () => {
          if (res.statusCode === 201) {
            console.log(`Uploaded ${fileName} successfully!`);
            resolve(JSON.parse(respData));
          } else {
            console.error(`Upload error for ${fileName} (${res.statusCode}):`, respData);
            reject(new Error(`Failed to upload ${fileName}`));
          }
        });
      });

      req.on("error", reject);

      const stream = fs.createReadStream(filePath);
      stream.pipe(req);
    });
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

  console.log("\n========================================================");
  console.log("GitHub Release Published Successfully!");
  console.log(`URL: ${release.html_url}`);
  console.log("========================================================");
}

main().catch((err) => {
  console.error("Fatal release publication error:", err);
  process.exit(1);
});
