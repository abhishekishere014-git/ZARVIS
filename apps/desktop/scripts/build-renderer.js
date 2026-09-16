/**
 * Build helper for ZARVIS Desktop.
 * Copies static assets (index.html, styles) into dist/renderer for standalone,
 * path-independent execution in both development and production packaged builds.
 */

const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const srcRenderer = path.join(root, "src", "renderer");
const distRenderer = path.join(root, "dist", "renderer");

// 1. Ensure output directories exist
fs.mkdirSync(path.join(distRenderer, "styles"), { recursive: true });

// 2. Copy main.css
const cssSrc = path.join(srcRenderer, "styles", "main.css");
const cssDest = path.join(distRenderer, "styles", "main.css");
if (fs.existsSync(cssSrc)) {
  fs.copyFileSync(cssSrc, cssDest);
}

// 3. Transform and copy index.html
const htmlSrc = path.join(srcRenderer, "index.html");
const htmlDest = path.join(distRenderer, "index.html");
if (fs.existsSync(htmlSrc)) {
  let html = fs.readFileSync(htmlSrc, "utf-8");
  // Normalize script path to local bundle
  html = html.replace('../../dist/renderer/app.js', './app.js');
  fs.writeFileSync(htmlDest, html, "utf-8");
}

console.log("Renderer assets assembled in dist/renderer successfully.");
