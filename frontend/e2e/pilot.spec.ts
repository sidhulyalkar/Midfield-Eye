import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
});

test("R1 showcase explains the real-evidence gate without inventing a result", async ({ page }) => {
  await page.goto("/pilot");
  await expect(
    page.getByRole("heading", { name: "Can we predict the menu, not just the move?" }),
  ).toBeVisible();
  await expect(page.getByText("No empirical model result yet.")).toBeVisible();
  await expect(page.getByText("Five locks between an idea and a claim.")).toBeVisible();
  await expect(page.locator(".pilot-ladder li")).toHaveCount(5);
  await expect(page.getByText("Receipts under pressure")).toBeVisible();
  await expect(page.getByText("Outcome blind")).toBeVisible();
  await expect(page.getByText("Model-score blind")).toBeVisible();
  await expect(page.getByText("Causal history only")).toBeVisible();
  await expect(page.getByText("No benchmark number is allowed here yet.")).toBeVisible();
  await expect(page.getByRole("table", { name: "R1 benchmark metrics" })).toHaveCount(0);
});
