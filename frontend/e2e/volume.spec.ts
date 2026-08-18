import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
});

test("3D affordance volume exposes scientific channels and evidence boundaries", async ({
  page,
}) => {
  await page.goto("/volume");
  await expect(
    page.getByRole("heading", {
      name: "See the next second of football as a field you can move through.",
    }),
  ).toBeVisible();
  await expect(page.getByText("Height means when, not where.")).toBeVisible();
  await expect(page.getByRole("button", { name: /Pressure fronts/u })).toBeVisible();
  await expect(page.getByRole("button", { name: /Pressure shadows/u })).toBeVisible();
  await expect(page.getByRole("button", { name: /Passing corridors/u })).toBeVisible();
  await expect(page.getByRole("button", { name: /Option creation/u })).toBeVisible();
  await expect(page.getByLabel("Voxel signal threshold")).toBeVisible();
  await expect(page.getByText("A beautiful forecast is still a forecast.")).toBeVisible();
  await expect(page.getByText("2-pass instancing")).toBeVisible();
});
