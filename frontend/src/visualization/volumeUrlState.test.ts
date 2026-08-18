import { describe, expect, it } from "vitest";
import {
  parseTemporalFilterFromSearchParams,
  temporalFiltersEqual,
  writeTemporalFilterToSearchParams,
} from "./volumeUrlState";

describe("v1.2 temporal URL state", () => {
  it("round-trips exact integer slice and band indices while preserving unrelated state", () => {
    const current = new URLSearchParams("scenario=aitana-overload&foo=bar");
    const slice = writeTemporalFilterToSearchParams(current, {
      mode: "slice",
      layerIndex: 2,
    });
    expect(slice.get("scenario")).toBe("aitana-overload");
    expect(slice.get("foo")).toBe("bar");
    expect(slice.toString()).toContain("tm=slice");
    expect(parseTemporalFilterFromSearchParams(slice, 7)).toEqual({
      mode: "slice",
      layerIndex: 2,
    });

    const band = writeTemporalFilterToSearchParams(slice, {
      mode: "band",
      startLayerIndex: 1,
      endLayerIndex: 4,
    });
    expect(band.get("layer")).toBeNull();
    expect(parseTemporalFilterFromSearchParams(band, 7)).toEqual({
      mode: "band",
      startLayerIndex: 1,
      endLayerIndex: 4,
    });
  });

  it("fails closed to Full for malformed, floating, reversed, or out-of-range indices", () => {
    expect(
      parseTemporalFilterFromSearchParams(
        new URLSearchParams("tm=slice&layer=0.5"),
        7,
      ),
    ).toEqual({ mode: "full" });
    expect(
      parseTemporalFilterFromSearchParams(
        new URLSearchParams("tm=band&from=5&to=2"),
        7,
      ),
    ).toEqual({ mode: "full" });
    expect(
      parseTemporalFilterFromSearchParams(
        new URLSearchParams("tm=slice&layer=99"),
        7,
      ),
    ).toEqual({ mode: "full" });
  });

  it("compares filter semantics rather than object identity", () => {
    expect(
      temporalFiltersEqual(
        { mode: "slice", layerIndex: 2 },
        { mode: "slice", layerIndex: 2 },
      ),
    ).toBe(true);
    expect(
      temporalFiltersEqual(
        { mode: "slice", layerIndex: 2 },
        { mode: "slice", layerIndex: 3 },
      ),
    ).toBe(false);
  });
});
