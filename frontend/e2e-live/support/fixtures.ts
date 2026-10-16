import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import path from "node:path";

import { chromium } from "@playwright/test";

import { REPO_ROOT, SEED_DIR } from "./stack";

// Page height by document type, mirrored from seed/__main__.py (_PAGE_HEIGHT): a photo frames
// the content and the shadow crosses the text.
const PAGE_HEIGHT: Record<string, number> = {
  "10th_marksheet": 600,
  "12th_marksheet": 600,
  id_proof: 340,
  transfer_certificate: 340,
};

function seed(...args: string[]): void {
  execFileSync("uv", ["run", "python", "-m", "seed", "--out", SEED_DIR, ...args], {
    cwd: REPO_ROOT,
    stdio: "pipe",
  });
}

function pagesOf(): { stem: string; height: number }[] {
  const labels = JSON.parse(readFileSync(path.join(SEED_DIR, "labels.json"), "utf8")) as {
    documents: { application_id: string; doc_type: string }[];
  };
  return labels.documents.map((d) => ({
    stem: `${d.application_id}_${d.doc_type}`,
    height: PAGE_HEIGHT[d.doc_type] ?? 600,
  }));
}

/**
 * The synthetic documents are generated, not committed (data/seed is ignored). Build them here
 * the way seed/__main__.py documents it: HTML pages, a clean screenshot of each in Chromium,
 * then the OpenCV photo noise. Deterministic from the fixed seed. Skipped when already built.
 */
export async function ensureSeedPngs(): Promise<string> {
  const pngDir = path.join(SEED_DIR, "png");
  if (existsSync(path.join(pngDir, "SYN-APP-003_10th_marksheet.png"))) {
    return pngDir;
  }
  seed();
  mkdirSync(path.join(SEED_DIR, "clean"), { recursive: true });
  const browser = await chromium.launch();
  try {
    const htmlDir = path.join(SEED_DIR, "html");
    for (const { stem, height } of pagesOf()) {
      const page = await browser.newPage({ viewport: { width: 800, height } });
      await page.goto(`file://${path.join(htmlDir, `${stem}.html`)}`);
      await page.screenshot({ path: path.join(SEED_DIR, "clean", `${stem}.png`) });
      await page.close();
    }
  } finally {
    await browser.close();
  }
  seed("--noise");
  return pngDir;
}

/** The synthetic applications as a CSV: the header line, then one line per reference. */
export function csvRows(refs: string[]): string {
  const lines = readFileSync(path.join(SEED_DIR, "applications.csv"), "utf8").trimEnd().split("\n");
  const header = lines[0];
  if (header === undefined) {
    throw new Error("applications.csv is empty");
  }
  const wanted = refs.map((ref) => {
    const line = lines.find((l) => l.startsWith(`${ref},`));
    if (!line) {
      throw new Error(`${ref} is not in applications.csv`);
    }
    return line;
  });
  return `${[header, ...wanted].join("\n")}\n`;
}
