import { describe, expect, it, vi } from "vitest";
import { updateDifferenceRenderer } from "./volumeDifferenceRendererAdapter";

describe("difference renderer adapter", () => {
  it("forwards the exact solid and field arrays without manufacturing comparison metadata", () => {
    const solids = new Float32Array([1, 2, 3]);
    const field = new Float32Array([4, 5, 6]);
    const update = vi.fn();

    updateDifferenceRenderer({ update }, { solids, field });

    expect(update).toHaveBeenCalledTimes(1);
    const scene = update.mock.calls[0]?.[0] as {
      solids: Float32Array;
      field: Float32Array;
    };
    expect(scene.solids).toBe(solids);
    expect(scene.field).toBe(field);
    expect(Object.keys(scene).sort()).toEqual(["field", "solids"]);
  });
});
