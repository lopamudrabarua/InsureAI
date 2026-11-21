const fs = require("node:fs");
const path = require("node:path");

const apiBase = process.env.INSUREAI_API_BASE;
if (!apiBase) {
  throw new Error("Set the Vercel build environment variable INSUREAI_API_BASE to the Render service URL.");
}

let parsed;
try {
  parsed = new URL(apiBase);
} catch {
  throw new Error("INSUREAI_API_BASE must be a valid absolute URL.");
}
if (parsed.protocol !== "https:" && !["localhost", "127.0.0.1"].includes(parsed.hostname)) {
  throw new Error("INSUREAI_API_BASE must use HTTPS outside local development.");
}

const output = path.join(__dirname, "dist");
fs.rmSync(output, { recursive: true, force: true });
fs.mkdirSync(output, { recursive: true });
for (const filename of ["index.html", "style.css", "script.js"]) {
  fs.copyFileSync(path.join(__dirname, filename), path.join(output, filename));
}
fs.writeFileSync(
  path.join(output, "api-config.js"),
  `window.INSUREAI_API_BASE = ${JSON.stringify(parsed.origin)};\n`,
);
