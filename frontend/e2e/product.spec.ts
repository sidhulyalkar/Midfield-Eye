import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(() => {
    Object.defineProperty(window, "requestAnimationFrame", {
      configurable: true,
      value: (callback: FrameRequestCallback) =>
        window.setTimeout(() => callback(performance.now()), 16),
    });
  });
});

test("synthetic scenario stays synchronized and keyboard addressable", async ({
  page,
}) => {
  await page.goto("/scenario/aitana-overload?frame=0");
  await expect(
    page.getByRole("heading", { name: "Overload, escape, arrive" }),
  ).toBeVisible();
  await expect(page.getByText("Not measured player performance")).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/frame=1/u);
  await page.getByRole("button", { name: "Lock selected option" }).click();
  await expect(
    page.getByRole("button", { name: "Release option lock" }),
  ).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(
    page.getByRole("button", { name: "Lock selected option" }),
  ).toBeVisible();
});

test("empirical slice preserves snapshot and missing-signal boundaries", async ({
  page,
}) => {
  await page.goto("/empirical/experiments/statsbomb-pedri-3857263-28ff205e");
  await expect(
    page.getByText("Event-centered snapshot", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("No temporal playback or velocity claim"),
  ).toBeVisible();
  await expect(page.getByText("literal gaze", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Retrospective event label", { exact: true }),
  ).toBeVisible();
});

test("atlas contains exactly 100 balanced, unranked research profiles", async ({
  page,
}) => {
  await page.goto("/atlas");
  await expect(page.locator(".profile-card")).toHaveCount(100);
  await expect(page.getByLabel("Cohort balance")).toContainText("50");
  await expect(page.getByText("Research emphasis").first()).toBeVisible();
  await expect(page.locator(".profile-card [data-rank]")).toHaveCount(0);
});

test("perception mask preserves physical candidates and changes observation style only", async ({
  page,
}) => {
  await page.goto("/perception-lab");
  const panels = page.locator(".comparison-pitches article");
  await expect(panels).toHaveCount(2);
  const completePlayers = await panels.nth(0).locator(".player").count();
  const maskedPlayers = await panels.nth(1).locator(".player").count();
  const completeOptions = await panels
    .nth(0)
    .locator(".option-corridor")
    .count();
  const maskedOptions = await panels.nth(1).locator(".option-corridor").count();
  expect(maskedPlayers).toBe(completePlayers);
  expect(maskedOptions).toBe(completeOptions);
  await expect(
    panels.nth(1).locator(".outside-observation").first(),
  ).toBeVisible();
  await expect(page.getByText(/remain physical candidates/u)).toBeVisible();
});

test("URL state restores layers without autoplay", async ({ page }) => {
  await page.goto(
    "/scenario/aitana-overload?frame=3&rate=0.5&layers=gaze&edge=ignored&evidence=observed",
  );
  await expect(
    page.getByRole("button", { name: /View proxy/u }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("button", { name: /Visible area/u }),
  ).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByRole("button", { name: "Play" })).toBeVisible();
  await expect(page).toHaveURL(/frame=3/u);
});

test("required routes have no console errors or broken visible images", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  for (const route of [
    "/",
    "/scenario/aitana-overload?frame=10",
    "/empirical/experiments/statsbomb-pedri-3857263-28ff205e",
    "/atlas",
    "/gaze-lab",
  ]) {
    await page.goto(route);
    await page.waitForLoadState("networkidle");
    for (const image of await page.locator("img:visible").all()) {
      await expect(image).toHaveJSProperty("complete", true);
      await expect(image).toHaveAttribute("src", /.+/u);
    }
  }
  expect(errors).toEqual([]);
});

test("captures deterministic representative routes", async ({
  page,
}, testInfo) => {
  const output = testInfo.outputPath("visuals");
  await mkdir(output, { recursive: true });
  for (const [name, route] of [
    ["landing", "/"],
    ["synthetic", "/scenario/aitana-overload?frame=10"],
    ["empirical", "/empirical/experiments/statsbomb-pedri-3857263-28ff205e"],
    ["atlas", "/atlas?cohort=women%27s+game"],
    ["gaze-lab", "/gaze-lab"],
  ] as const) {
    await page.goto(route);
    await page.waitForLoadState("networkidle");
    await page.screenshot({
      path: `${output}/${name}.png`,
      fullPage: true,
      animations: "disabled",
    });
  }
});
