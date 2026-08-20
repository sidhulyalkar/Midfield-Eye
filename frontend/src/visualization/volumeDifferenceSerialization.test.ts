import { describe, expect, it } from "vitest";
import type { VolumeDifferenceInspection } from "./volumeDifferenceInspector";
import {
  differenceInspectionFilename,
  serializeDifferenceInspection,
} from "./volumeDifferenceSerialization";
import type { EarlierRunIntervention } from "./volumeIntervention";

const inspection: VolumeDifferenceInspection = {
  key: "2:3:4",
  support: "left_only",
  numericComparisonAvailable: false,
  signConvention: "condition_b_minus_condition_a",
  delta: null,
  absoluteDelta: null,
  conditionA: {
    conditionId: "baseline",
    retained: true,
    voxelId: "a",
    value: 0.62,
    voxel: null,
  },
  conditionB: {
    conditionId: "earlier-run:p:0.75",
    retained: false,
    voxelId: null,
    value: null,
    voxel: null,
  },
  claimBoundary: {
    oneSidedPresenceIsNumericalZero: false,
    missingSupportInterpolated: false,
    calibratedProbability: false,
    futureObservedFramesUsed: false,
  },
};

const intervention = {
  id: "earlier-run:p:0.75",
  playerId: "p",
  leadSeconds: 0.75,
  speedMps: 2,
  displacementM: 1.5,
  from: [40, 20],
  to: [41.5, 20],
  baselineFrame: {
    metadata: {
      evidence_status: "illustrative_synthetic_reconstruction",
    },
  },
} as unknown as EarlierRunIntervention;

describe("v1.3 difference export", () => {
  it("keeps one-sided support null and labels the state-derived comparison scope", () => {
    const record = serializeDifferenceInspection(
      "aitana-overload",
      10,
      "future_space",
      { mode: "slice", layerIndex: 2 },
      inspection,
      intervention,
    );
    expect(record.schemaVersion).toBe("1.3.0");
    expect(record.sourceEvidenceStatus).toBe(
      "illustrative_synthetic_reconstruction",
    );
    expect(record.comparison.support).toBe("left_only");
    expect(record.comparison.delta).toBeNull();
    expect(record.comparison.conditionB.retained).toBe(false);
    expect(record.intervention).toMatchObject({
      id: "earlier-run:p:0.75",
      playerId: "p",
      leadSeconds: 0.75,
      status: "synthetic_teaching_intervention_not_observed_or_causal",
    });
    expect(record.claimBoundary).toMatchObject({
      oneSidedPresenceIsNumericalZero: false,
      missingSupportInterpolated: false,
      futureObservedFramesUsed: false,
      activeChannels: "state_derived_future_space_or_option_creation_only",
      candidateOptionsIncluded: false,
      candidateOptionsRegenerated: false,
    });
  });

  it("creates a stable filename from the comparison key", () => {
    expect(
      differenceInspectionFilename(
        "aitana-overload",
        10,
        "option_creation",
        "2:3:4",
      ),
    ).toBe(
      "midfield-eye-difference-aitana-overload-f10-option_creation-2-3-4.json",
    );
  });
});
