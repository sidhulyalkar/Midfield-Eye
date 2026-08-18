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
  await expect(
    page.getByRole("button", { name: /Pressure fronts/u }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Pressure shadows/u }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Passing corridors/u }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Option creation/u }),
  ).toBeVisible();
  await expect(page.getByLabel("Voxel signal threshold")).toBeVisible();
  await expect(
    page.getByText("A beautiful forecast is still a forecast."),
  ).toBeVisible();
  await expect(page.getByText("2-pass instancing")).toBeVisible();
  await expect(page.getByText("Inspector v1.1")).toBeVisible();
});

test("v1.1 turns a rendered voxel into an auditable forensic record", async ({
  page,
}) => {
  await page.goto("/volume");

  const inspector = page.getByTestId("voxel-inspector");
  await expect(inspector).toContainText("Ask one glowing cell what it means.");

  await inspector
    .getByRole("button", { name: "Inspect strongest visible voxel" })
    .click();
  await expect(page.getByTestId("voxel-selection-marker")).toBeVisible();
  await expect(inspector).toContainText("Forecast horizon");
  await expect(inspector).toContainText("Focal-state kinematics");
  await expect(inspector).toContainText("Carrier orientation proxy");
  await expect(inspector).toContainText("Component field");
  await expect(inspector).toContainText("Nearest defender");
  await expect(inspector).toContainText("not a calibrated probability");
  await expect(
    inspector.getByRole("button", { name: "Clear inspected voxel" }),
  ).toBeVisible();

  await page.getByRole("button", { name: /Pressure fronts/u }).click();
  await expect(inspector).toContainText("Ask one glowing cell what it means.");
  await inspector
    .getByRole("button", { name: "Inspect strongest visible voxel" })
    .click();
  await expect(inspector).toContainText("Pressure");
});
