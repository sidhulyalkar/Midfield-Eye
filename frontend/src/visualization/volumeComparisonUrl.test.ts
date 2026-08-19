import { describe, expect, it } from "vitest";
import {
  parseComparisonFrameIndex,
  parseVolumeComparisonUrl,
  writeComparisonFrameIndex,
  writeVolumeComparisonUrl,
} from "./volumeComparisonUrl";

describe("v1.3 comparison URL state", () => {
  it("parses and writes deterministic comparison state while preserving unrelated params", () => {
    const original = new URLSearchParams(
      "scenario=aitana-overload&cmp=earlier-run&dc=option_creation&lead=1.00&dq=high&dt=0.275&tm=slice&layer=3",
    );
    const state = parseVolumeComparisonUrl(original);
    expect(state).toEqual({
      comparisonId: "earlier-run",
      channel: "option_creation",
      leadSeconds: 1,
      quality: "high",
      threshold: 0.275,
    });

    const written = writeVolumeComparisonUrl(original, {
      ...state,
      channel: "future_space",
      leadSeconds: 0.5,
      quality: "low",
      threshold: 0.2,
    });
    expect(written.get("scenario")).toBe("aitana-overload");
    expect(written.get("tm")).toBe("slice");
    expect(written.get("layer")).toBe("3");
    expect(written.get("dc")).toBe("future_space");
    expect(written.get("lead")).toBe("0.50");
    expect(written.get("dq")).toBe("low");
    expect(written.get("dt")).toBe("0.200");
  });

  it("fails closed to deterministic defaults for malformed comparison state", () => {
    const state = parseVolumeComparisonUrl(
      new URLSearchParams("cmp=unknown&dc=menu&lead=0.73&dq=auto&dt=NaN"),
    );
    expect(state).toEqual({
      comparisonId: "earlier-run",
      channel: "future_space",
      leadSeconds: 0.75,
      quality: "medium",
      threshold: 0.2,
    });
  });

  it("snaps threshold to the supported deterministic retention grid", () => {
    expect(
      parseVolumeComparisonUrl(new URLSearchParams("dt=0.286")).threshold,
    ).toBe(0.275);
    expect(
      parseVolumeComparisonUrl(new URLSearchParams("dt=0.661")).threshold,
    ).toBe(0.2);
  });

  it("round-trips only valid focal frame indices", () => {
    const params = new URLSearchParams("fi=4&scenario=x");
    expect(parseComparisonFrameIndex(params, 12, 7)).toBe(4);
    expect(
      parseComparisonFrameIndex(new URLSearchParams("fi=12"), 12, 7),
    ).toBe(7);
    expect(
      parseComparisonFrameIndex(new URLSearchParams("fi=3.5"), 12, 7),
    ).toBe(7);

    const written = writeComparisonFrameIndex(params, 9);
    expect(written.get("fi")).toBe("9");
    expect(written.get("scenario")).toBe("x");
    expect(() => writeComparisonFrameIndex(params, -1)).toThrow(
      /non-negative integer/u,
    );
  });
});
