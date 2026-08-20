import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "@playwright/test";

const DEFAULT_BASE_URL = "http://127.0.0.1:4173";
const DEFAULT_OUTPUT_DIR = "artifacts/publication";
const VIEWPORT = { width: 1600, height: 1200 };

function argument(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] ?? null : null;
}

function publicationUrl(raw) {
  if (!raw) {
    throw new Error(
      "Missing --url. Provide the exact /volume/compare?...&pub=figure&tm=slice&layer=<integer> state.",
    );
  }
  const base = process.env.FIGURE_BASE_URL ?? DEFAULT_BASE_URL;
  const url = new URL(raw, base);
  if (url.pathname !== "/volume/compare") {
    throw new Error("Difference figure export requires the /volume/compare route.");
  }
  if (url.searchParams.get("pub") !== "figure") {
    throw new Error("Difference figure export requires pub=figure.");
  }
  if (url.searchParams.get("tm") !== "slice") {
    throw new Error("Difference figure export requires tm=slice.");
  }
  const layer = url.searchParams.get("layer");
  if (!layer || !/^\d+$/u.test(layer)) {
    throw new Error("Difference figure export requires an integer layer parameter.");
  }
  for (const required of ["scenario", "fi", "lead", "dc", "dq", "dt"]) {
    if (!url.searchParams.has(required)) {
      throw new Error(`Difference figure export requires ${required}=... in the URL.`);
    }
  }
  return url;
}

function safeFigureId(value) {
  if (!value || !/^ME-DIFF-[a-z0-9-]+$/u.test(value)) {
    throw new Error(`Publication plate returned an invalid figure ID: ${value ?? "missing"}`);
  }
  return value;
}

const url = publicationUrl(argument("--url"));
const outputDirectory = resolve(argument("--output") ?? DEFAULT_OUTPUT_DIR);
await mkdir(outputDirectory, { recursive: true });

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: VIEWPORT, deviceScaleFactor: 1 });
  await page.emulateMedia({ reducedMotion: "reduce", media: "screen" });
  await page.goto(url.toString(), { waitUntil: "networkidle" });

  const plate = page.getByTestId("difference-publication-plate");
  await plate.waitFor({ state: "visible" });
  const figureId = safeFigureId(await plate.getAttribute("data-figure-id"));
  const pngPath = resolve(outputDirectory, `${figureId}.png`);
  const pdfPath = resolve(outputDirectory, `${figureId}.pdf`);
  const manifestPath = resolve(outputDirectory, `${figureId}.json`);

  await plate.screenshot({ path: pngPath, animations: "disabled" });
  await page.emulateMedia({ reducedMotion: "reduce", media: "print" });
  await page.pdf({
    path: pdfPath,
    printBackground: true,
    preferCSSPageSize: true,
    landscape: true,
  });

  const manifest = {
    schemaVersion: "1.3.0-rc",
    figureId,
    sourceUrl: url.toString(),
    viewport: VIEWPORT,
    png: pngPath,
    pdf: pdfPath,
    generatedAt: new Date().toISOString(),
    claimBoundary: {
      publicationOnlyRecomputedScientificField: false,
      publicationRequiresExactSlice: true,
      notRetainedIsNumericalZero: false,
    },
  };
  await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  console.log(JSON.stringify({ figureId, pngPath, pdfPath, manifestPath }));
} finally {
  await browser.close();
}
