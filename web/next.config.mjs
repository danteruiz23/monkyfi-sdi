// Read-only view (D45). The only setting it takes from the repo's .env is the run folder to show.
import fs from "node:fs";
import path from "node:path";

const VARIABLE = "SDI_VIEW_DATA_DIR";
const envFile = path.resolve(process.cwd(), "..", ".env");
if (!process.env[VARIABLE] && fs.existsSync(envFile)) {
  for (const line of fs.readFileSync(envFile, "utf8").split("\n")) {
    const match = line.match(/^\s*SDI_VIEW_DATA_DIR\s*=\s*(.*?)\s*$/);
    if (match && match[1]) process.env[VARIABLE] = match[1].replace(/^["']|["']$/g, "");
  }
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  async redirects() {
    return [{ source: "/", destination: "/en", permanent: false }];
  },
};

export default nextConfig;
