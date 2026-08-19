import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
});

test("v1.3 comparison workbench restores a citable state and links 3D to the exact slice", async ({
  page,
}) => {
  await page.goto(
    "/volume/compare?scenario=aitana-overload&fi=10&cmp=earlier-run&lead=0.75&dc=future_space&dq=low&dt=0.200&tm=slice&layer=2",
  );

  await expect(
    page.getByRole("heading", {
      name: "Compare what changed without turning missing evidence into zero.",
    }),
  ).toBeVisible();
  await expect(page.getByTestId("difference-volume-3d")).toBeVisible();
  await expect(page.getByTestId("linked-difference-slice")).toBeVisible();
  await expect(
    page.getByText("Teaching intervention, not causal evidence"),
  ).toBeVisible();
  await expect(
    page.getByText(/candidate pass scores are intentionally omitted/u),
  ).toBeVisible();
  await expect(page).toHaveURL(/lead=0\.75/u);
  await expect(page).toHaveURL(/dc=future_space/u);
  await expect(page).toHaveURL(/dq=low/u);
  await expect(page).toHaveURL(/dt=0\.200/u);
  await expect(page).toHaveURL(/tm=slice/u);
  await expect(page).toHaveURL(/layer=2/u);

  await page
    .getByRole("button", { name: "Inspect most informative visible cell" })
    .click();
  await expect(page.getByTestId("difference-selection-marker")).toBeVisible();
  const inspector = page.getByTestId("difference-inspector");
  await expect(inspector).toContainText("DIFFERENCE FORENSICS");
  await expect(inspector).toContainText(/Condition A/u);
  await expect(inspector).toContainText(/Condition B/u);
  await expect(inspector).toContainText(/B−A/u);

  const downloadPromise = page.waitForEvent("download");
  await page.getByTestId("export-difference-json").click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(
    /^midfield-eye-difference-aitana-overload-f\d+-future_space-/u,
  );

  const temporalControls = page.getByTestId("difference-temporal-controls");
  await temporalControls
    .getByRole("button", { name: "+1.00", exact: true })
    .click();
  await expect(page).toHaveURL(/layer=4/u);
  await page.reload();
  await expect(page.getByTestId("linked-difference-slice")).toContainText(
    "+1.00 s",
  );
});

test("v1.3 comparison keeps one-sided evidence categorical in explanatory copy", async ({
  page,
}) => {
  await page.goto(
    "/volume/compare?scenario=aitana-overload&fi=10&cmp=earlier-run&lead=1.00&dc=option_creation&dq=medium&dt=0.200&tm=full",
  );
  await expect(
    page.getByText(
      "Color says direction. Shape says whether a number exists.",
    ),
  ).toBeVisible();
  await expect(
    page.getByText(/Vertical gold rails: retained only in A, no numeric Δ/u),
  ).toBeVisible();
  await expect(
    page.getByText(/Horizontal blue rails: retained only in B, no numeric Δ/u),
  ).toBeVisible();
  await expect(page.getByText(/One-sided presence is not zero/u)).toBeVisible();
});
