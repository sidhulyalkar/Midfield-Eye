import { afterEach, describe, expect, it, vi } from "vitest";
import { createPitchTransform } from "../visualization/coordinates";
import { pointInPolygon } from "../visualization/TacticalPitch";
import {
  ApiShowcaseDataSource,
  StaticShowcaseDataSource,
  parseJsonLines,
} from "./dataSources";
import { FrameStateSchema, PlayerStudySchema } from "./schemas";

const frame = {
  sequence_id: "sequence-a",
  frame_id: 3,
  timestamp_s: 1.5,
  possession_team: "home",
  ball_x: 50,
  ball_y: 34,
  ball_carrier_id: "h1",
  players: [
    {
      player_id: "h1",
      team: "home",
      x: 50,
      y: 34,
      tracking_status: "observed",
      metadata: {},
    },
  ],
  pitch_length: 105,
  pitch_width: 68,
  source_provider: "fixture",
  quality_flags: [],
  state_version: "0.6",
  metadata: {},
};

describe("external data boundary", () => {
  it("reports the exact invalid JSONL line", () => {
    const text = `${JSON.stringify(frame)}\n\n{"broken":`;
    expect(() =>
      parseJsonLines(text, FrameStateSchema, "frames.jsonl"),
    ).toThrow("frames.jsonl at line 3");
  });

  it("preserves nullable values instead of coercing them", () => {
    const result = FrameStateSchema.parse({
      ...frame,
      players: [{ ...frame.players[0], gaze_angle: null }],
    });
    expect(result.players[0]?.gaze_angle).toBeNull();
  });

  it("rejects unknown player evidence states", () => {
    expect(() =>
      PlayerStudySchema.parse({
        id: "x",
        name: "X",
        cohort: "men's game",
        display_role: "Test",
        primary_archetype: "test",
        signature: "Test",
        study_questions: [],
        showcase_emphasis: {},
        showcase_emphasis_status:
          "illustrative_archetype_emphasis_not_player_rating",
        evidence_status: "probably_measured",
        profile_status: "test",
      }),
    ).toThrow();
  });
});

describe("canonical pitch transform", () => {
  it("round-trips without independent axis stretch", () => {
    const transform = createPitchTransform({
      pitchLength: 105,
      pitchWidth: 68,
      viewportWidth: 900,
      viewportHeight: 500,
      padding: 12,
    });
    const point = { x: 64.2, y: 17.1 };
    const restored = transform.toPitch(transform.toScreen(point));
    expect(restored.x).toBeCloseTo(point.x, 8);
    expect(restored.y).toBeCloseTo(point.y, 8);
    expect(
      transform.metresToPixels(2) / transform.metresToPixels(1),
    ).toBeCloseTo(2);
  });

  it("distinguishes observation masking without deleting canonical points", () => {
    const visibleArea: [number, number][] = [
      [0, 0],
      [85, 0],
      [85, 68],
      [0, 68],
    ];
    expect(pointInPolygon([40, 34], visibleArea)).toBe(true);
    expect(pointInPolygon([95, 34], visibleArea)).toBe(false);
  });
});

describe("static/API normalization", () => {
  afterEach(() => vi.unstubAllGlobals());

  const requestUrl = (input: RequestInfo | URL): string => {
    if (input instanceof URL) return input.href;
    if (input instanceof Request) return input.url;
    return input;
  };

  const experiment = {
    id: "study-1",
    title: "Provider study",
    subject: null,
    source_id: "metrica_sample_data",
    evidence_tier: "provider_tracking",
    modalities: ["full_tracking"],
    measured: ["player_xy"],
    inferred: ["pressure"],
    unavailable: ["literal_gaze"],
    visual: "visuals/study.png",
    source_bundle: "data/empirical/open/study",
    claim_boundary: "Anonymous spatial state only.",
  };

  it("normalizes legacy and current API health while matching an empirical view model", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = requestUrl(input);
        const body = url.endsWith("/api/health")
          ? { status: "ok", version: "0.6.0" }
          : url.endsWith("/api/empirical/experiments/study-1")
            ? experiment
            : url.endsWith("/showcase/empirical/experiments.json")
              ? [experiment]
              : null;
        return Promise.resolve(
          new Response(JSON.stringify(body), {
            status: body == null ? 404 : 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }),
    );
    const api = new ApiShowcaseDataSource("https://api.example/");
    const staticSource = new StaticShowcaseDataSource(
      "https://static.example/showcase/",
    );
    await expect(api.getHealth()).resolves.toMatchObject({
      status: "ok",
      bundle_version: "0.6.0",
    });
    await expect(api.getEmpiricalExperiment("study-1")).resolves.toEqual(
      await staticSource.getEmpiricalExperiment("study-1"),
    );
  });

  it("does not silently fall back when a configured API fails", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      requestUrl(input);
      return Promise.resolve(new Response("down", { status: 503 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const api = new ApiShowcaseDataSource("https://api.example/");
    await expect(api.getManifest()).rejects.toThrow("503");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const requested = fetchMock.mock.calls[0]?.[0];
    expect(requested ? requestUrl(requested) : "").toContain(
      "api/showcase/manifest",
    );
  });
});
