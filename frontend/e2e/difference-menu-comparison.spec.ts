import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
});

test("v1.4 switches from state-only to regenerated MENU, survives reload, and exports provenance", async ({
  page,
}) => {
  await page.goto(
    "/volume/compare?scenario=aitana-overload&fi=10&cmp=earlier-run&lead=0.75&dc=future_space&dq=low&dt=0.200&tm=slice&layer=2",
  );

  await expect(page.getByText("State-only comparison", { exact: true })).toBeVisible();
  await expect(page).toHaveURL(/dc=future_space/u);

  await page
    .locator(".difference-button-grid button")
    .filter({ hasText: "MENU" })
    .click();

  await expect(page).toHaveURL(/dc=menu/u);
  await expect(
    page.getByText("Regenerated candidates, not causal evidence", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Regenerated candidate evidence" }),
  ).toBeVisible();
  await expect(page.getByText(/AffordanceEngine/u).first()).toBeVisible();
  await expect(page.getByText(/semantic_action_candidate_v1/u)).toBeVisible();

  await page.reload();
  await expect(page).toHaveURL(/dc=menu/u);
  await expect(
    page.getByText("Regenerated candidates, not causal evidence", { exact: true }),
  ).toBeVisible();

  await page
    .getByRole("button", { name: "Inspect most informative visible cell" })
    .click();
  await expect(page.getByTestId("difference-inspector")).toContainText(
    "DIFFERENCE FORENSICS",
  );
  await expect(
    page.getByText("Condition A local option contributions"),
  ).toBeVisible();
  await expect(
    page.getByText("Condition B local option contributions"),
  ).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByTestId("export-difference-json").click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(
    /^midfield-eye-difference-aitana-overload-f\d+-menu-/u,
  );

  const downloadPath = await download.path();
  expect(downloadPath).not.toBeNull();
  const exported = JSON.parse(await readFile(downloadPath!, "utf8")) as {
    schemaVersion: string;
    channel: string;
    candidateEvidence: {
      mode: string;
      generator: { name: string; configSha256: string } | null;
    };
    claimBoundary: {
      candidateOptionsIncluded: boolean;
      candidateOptionsRegenerated: boolean;
      futureObservedFramesUsed: boolean;
      activeChannels: string;
    };
  };

  expect(exported.schemaVersion).toBe("1.4.0-d");
  expect(exported.channel).toBe("menu");
  expect(exported.candidateEvidence.mode).toBe(
    "regenerated_counterfactual_candidates",
  );
  expect(exported.candidateEvidence.generator?.name).toBe("AffordanceEngine");
  expect(exported.candidateEvidence.generator?.configSha256).toMatch(/^[a-f0-9]{64}$/u);
  expect(exported.claimBoundary).toMatchObject({
    candidateOptionsIncluded: true,
    candidateOptionsRegenerated: true,
    futureObservedFramesUsed: false,
    activeChannels: "regenerated_passing_corridors_or_action_menu",
  });
});

test("v1.4 regenerated channels fail closed when the frozen candidate artifact is missing", async ({
  page,
}) => {
  await page.route("**/counterfactual_options.json", async (route) => {
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: "{}",
    });
  });

  await page.goto(
    "/volume/compare?scenario=aitana-overload&fi=10&cmp=earlier-run&lead=0.75&dc=menu&dq=low&dt=0.200&tm=full",
  );

  await expect(
    page.getByRole("heading", {
      name: "Regenerated candidate comparison failed closed",
    }),
  ).toBeVisible();
  await expect(page.getByText(/404/u)).toBeVisible();
  await expect(page.getByTestId("difference-volume-3d")).toHaveCount(0);
});
