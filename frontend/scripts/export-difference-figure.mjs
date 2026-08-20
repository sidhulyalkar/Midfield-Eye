import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "@playwright/test";

const DEFAULT_BASE_URL = "http://127.0.0.1:4173";
const DEFAULT_OUTPUT_DIR = "artifacts/publication";
const VIEWPORT = { width: 1600, height: 1200 };
const LEAD_PRESETS = new Set([0.5, 0.75, 1]);
const CHANNELS = new Set(["future_space", "option_creation"]);
const QUALITIES = new Set(["low", "medium", "high"]);

function argument(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] ?? null : null;
}

function integerParameter(url, name) {
  const value = url.searchParams.get(name);
  if (!value || !/^\d+$/u.test(value)) {
    throw new Error(`Difference figure export requires integer ${name}=...`);
  }
  return Number(value);
}

function finiteParameter(url, name) {
  const raw = url.searchParams.get(name);
  const value = Number(raw);
  if (!raw || !Number.isFinite(value)) {
    throw new Error(`Difference figure export requires finite ${name}=...`);
  }
  return value;
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
  if (url.searchParams.get("cmp") !== "earlier-run") {
    throw new Error("Difference figure export requires cmp=earlier-run.");
  }
  if (url.searchParams.get("tm") !== "slice") {
    throw new Error("Difference figure export requires tm=slice.");
  }
  integerParameter(url, "layer");
  integerParameter(url, "fi");

  const scenario = url.searchParams.get("scenario");
  if (!scenario?.trim()) {
    throw new Error("Difference figure export requires a non-empty scenario parameter.");
  }

  const lead = finiteParameter(url, "lead");
  if (!LEAD_PRESETS.has(lead)) {
    throw new Error("Difference figure export lead must be 0.50, 0.75, or 1.00 seconds.");
  }
  const channel = url.searchParams.get("dc");
  if (!channel || !CHANNELS.has(channel)) {
    throw new Error("Difference figure export dc must be future_space or option_creation.");
  }
  const quality = url.searchParams.get("dq");
  if (!quality || !QUALITIES.has(quality)) {
    throw new Error("Difference figure export dq must be low, medium, or high.");
  }
  const threshold = finiteParameter(url, "dt");
  if (threshold < 0.05 || threshold > 0.65) {
    throw new Error("Difference figure export dt must be within [0.05, 0.65].");
  }
  const snappedThreshold = Math.round(threshold / 0.025) * 0.025;
  if (Math.abs(snappedThreshold - threshold) > 1e-9) {
    throw new Error("Difference figure export dt must lie on the 0.025 retention grid.");
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
      publicationSpecificScientificFormulaUsed: false,
      sameComparisonBuilderAsWorkbench: true,
      publicationRequiresExactSlice: true,
      notRetainedIsNumericalZero: false,
    },
  };
  await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  console.log(JSON.stringify({ figureId, pngPath, pdfPath, manifestPath }));
} finally {
  await browser.close();
}
