import { expect, test } from "@playwright/test";

const figurePath =
  "/volume/compare?scenario=aitana-overload&fi=10&cmp=earlier-run&lead=0.75&dc=future_space&dq=low&dt=0.200&tm=slice&layer=2&pub=figure";

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
});

test("v1.3 rc publication mode renders a stable evidence-aware figure plate", async ({
  page,
}) => {
  await page.goto(figurePath);
  const plate = page.getByTestId("difference-publication-plate");
  await expect(plate).toBeVisible();
  await expect(plate).toHaveAttribute(
    "data-figure-id",
    "ME-DIFF-aitana-overload-f10-future-space-l2-lead075-qlow-t0200",
  );
  await expect(page.getByText("Synthetic showcase source")).toBeVisible();
  await expect(plate).toContainText("illustrative synthetic reconstruction");
  await expect(plate).toContainText("not_retained ≠ 0");
  await expect(plate).toContainText("Candidate options included: false.");
  await expect(plate).toContainText("Candidate options regenerated: false.");
  await expect(plate).toContainText("Future observed frames used: false.");
  await expect(
    plate.getByRole("region", { name: "Grayscale-safe support legend" }),
  ).toBeVisible();
  await expect(page.getByTestId("difference-volume-3d")).toHaveCount(0);

  const figureId = await plate.getAttribute("data-figure-id");
  await page.reload();
  await expect(page.getByTestId("difference-publication-plate")).toHaveAttribute(
    "data-figure-id",
    figureId ?? "",
  );
});

test("publication mode fails closed outside exact Slice mode", async ({ page }) => {
  await page.goto(
    "/volume/compare?scenario=aitana-overload&fi=10&cmp=earlier-run&lead=0.75&dc=future_space&dq=low&dt=0.200&tm=full&pub=figure",
  );
  await expect(
    page.getByRole("heading", {
      name: "Publication figure mode requires an exact temporal slice",
    }),
  ).toBeVisible();
  await expect(page.getByTestId("difference-publication-plate")).toHaveCount(0);
  await expect(page).toHaveURL(/tm=full/u);
});
