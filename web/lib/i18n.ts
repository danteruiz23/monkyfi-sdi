// All user-facing text comes from locales/ (SPEC 7.4). No string is written in the components.
import fs from "node:fs";
import path from "node:path";
import { LOCALES_DIR } from "./config";

export const LANGUAGES = ["en", "es"] as const;
export type Language = (typeof LANGUAGES)[number];
export type Params = Record<string, string | number>;
export type Translate = (key: string, params?: Params) => string;

export function isLanguage(value: string): value is Language {
  return (LANGUAGES as readonly string[]).includes(value);
}

function load(language: Language): Record<string, Record<string, string>> {
  return JSON.parse(fs.readFileSync(path.join(/*turbopackIgnore: true*/ LOCALES_DIR, `${language}.json`), "utf8"));
}

/** Text for "area.name". A missing key is an error, never a silent fallback. */
export function translator(language: Language): Translate {
  const locale = load(language);
  return (key, params) => {
    const dot = key.indexOf(".");
    const text = locale[key.slice(0, dot)]?.[key.slice(dot + 1)];
    if (typeof text !== "string") throw new Error(`locales/${language}.json has no key "${key}"`);
    return text.replace(/\{(\w+)\}/g, (whole, name) => (params && name in params ? String(params[name]) : whole));
  };
}
