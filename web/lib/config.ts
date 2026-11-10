import path from "node:path";

/** The repo root: the view is started from web/. */
export const REPO_ROOT = path.resolve(/*turbopackIgnore: true*/ process.cwd(), "..");
export const RULES_DIR = path.join(/*turbopackIgnore: true*/ REPO_ROOT, "rules");
export const LOCALES_DIR = path.join(/*turbopackIgnore: true*/ REPO_ROOT, "locales");

/** Folder with <order>/v<N>/extraction.json and validation.json (SDI_VIEW_DATA_DIR, relative to the repo root). */
export const DATA_DIR_NAME = process.env.SDI_VIEW_DATA_DIR || "runs/phase4-view";
export const DATA_DIR = path.resolve(/*turbopackIgnore: true*/ REPO_ROOT, DATA_DIR_NAME);
