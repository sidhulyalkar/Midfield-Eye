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
  await expect(page.getByText("Inspector v1.2")).toBeVisible();
  await expect(page.getByTestId("temporal-filter-hud")).toContainText("Full");
});

test("v1.1 forensic inspection remains auditable inside v1.2", async ({
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
  await expect(page.getByTestId("voxel-trajectory")).toContainText(
    "Gaps mean no retained voxel",
  );
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

test("v1.2 dissects retained voxels by integer temporal layer without losing identity", async ({
  page,
}) => {
  await page.goto("/volume");

  const surgery = page.getByTestId("temporal-surgery");
  const inspector = page.getByTestId("voxel-inspector");

  await surgery.getByRole("button", { name: "Slice", exact: true }).click();
  await surgery.getByRole("button", { name: "+0.50 s" }).click();
  await expect(page.getByTestId("temporal-filter-hud")).toHaveText(
    "Slice · +0.50 s",
  );

  await inspector
    .getByRole("button", { name: "Inspect strongest visible voxel" })
    .click();
  await expect(page.getByTestId("voxel-selection-marker")).toBeVisible();
  const trajectory = page.getByTestId("voxel-trajectory");
  await expect(trajectory).toBeVisible();
  await expect(trajectory.locator("li")).toHaveCount(7);
  await expect(trajectory).toContainText(
    "Gaps mean no retained voxel survived threshold/LOD",
  );
  await expect(trajectory).toContainText("They are not zeros");

  await surgery.getByRole("button", { name: "Full", exact: true }).click();
  await expect(page.getByTestId("temporal-filter-hud")).toContainText("Full");
  await expect(page.getByTestId("voxel-selection-marker")).toBeVisible();

  await surgery.getByRole("button", { name: "Slice", exact: true }).click();
  await surgery.getByRole("button", { name: "+1.00 s" }).click();
  await expect(page.getByTestId("temporal-filter-hud")).toHaveText(
    "Slice · +1.00 s",
  );
  await expect(inspector).toContainText("Ask one glowing cell what it means.");

  await surgery.getByRole("button", { name: "Band", exact: true }).click();
  await page.getByLabel("Band start layer").selectOption("1");
  await page.getByLabel("Band end layer").selectOption("4");
  await expect(page.getByTestId("temporal-filter-hud")).toHaveText(
    "Band · +0.25–+1.00 s",
  );
  await expect(page.getByText("2-pass instancing")).toBeVisible();
});

test("v1.2 linked 2D slice shares voxel identity, restores URL state, and exports JSON", async ({
  page,
}) => {
  await page.goto("/volume?scenario=aitana-overload&tm=slice&layer=2");

  await expect(page.getByTestId("temporal-filter-hud")).toHaveText(
    "Slice · +0.50 s",
  );
  const linked = page.getByTestId("linked-temporal-slice");
  await expect(linked).toBeVisible();
  await expect(linked).toContainText("identical IDs and values");

  const firstCell = linked.locator("[data-voxel-id]").first();
  const voxelId = await firstCell.getAttribute("data-voxel-id");
  const voxelValue = await firstCell.getAttribute("data-voxel-value");
  expect(voxelId).toBeTruthy();
  expect(voxelValue).toMatch(/^0\.\d{6}$/u);
  await firstCell.click();
  await expect(firstCell).toHaveClass(/is-selected/u);
  await expect(page.getByTestId("voxel-selection-marker")).toBeVisible();
  await expect(page.getByTestId("voxel-inspector")).toContainText(
    "Forecast horizon",
  );

  const exportButton = page.getByTestId("export-voxel-json");
  await expect(exportButton).toBeEnabled();
  const downloadPromise = page.waitForEvent("download");
  await exportButton.click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(
    /^midfielders-eye-frame-\d+-menu-layer-2\.json$/u,
  );

  const surgery = page.getByTestId("temporal-surgery");
  await surgery.getByRole("button", { name: "+1.00 s" }).click();
  await expect(page).toHaveURL(/tm=slice/u);
  await expect(page).toHaveURL(/layer=4/u);
  await page.reload();
  await expect(page.getByTestId("temporal-filter-hud")).toHaveText(
    "Slice · +1.00 s",
  );
  await expect(page.getByTestId("linked-temporal-slice")).toBeVisible();
});
