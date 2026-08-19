import { describe, expect, it } from "vitest";
import type { FrameState, PlayerState } from "../data/schemas";
import { buildEarlierRunIntervention } from "./volumeIntervention";

function player(
  playerId: string,
  team: "home" | "away",
  x: number,
  y: number,
  vx: number,
  vy: number,
): PlayerState {
  return {
    player_id: playerId,
    team,
    x,
    y,
    vx,
    vy,
    tracking_status: "observed",
    metadata: {},
  };
}

function frame(players: PlayerState[]): FrameState {
  return {
    sequence_id: "test",
    frame_id: 4,
    timestamp_s: 1.2,
    possession_team: "home",
    ball_x: 30,
    ball_y: 20,
    ball_carrier_id: "carrier",
    players,
    pitch_length: 105,
    pitch_width: 68,
    source_provider: "synthetic",
    quality_flags: [],
    state_version: "test",
    metadata: {},
  };
}

describe("earlier-run teaching intervention", () => {
  it("moves the fastest eligible off-ball teammate along their existing velocity", () => {
    const original = frame([
      player("carrier", "home", 30, 20, 0.3, 0),
      player("runner-a", "home", 45, 30, 2, 0),
      player("runner-b", "home", 50, 35, 1, 1),
      player("defender", "away", 55, 32, 4, 0),
    ]);

    const result = buildEarlierRunIntervention(original, 0.75);
    expect(result).not.toBeNull();
    expect(result?.playerId).toBe("runner-a");
    expect(result?.from).toEqual([45, 30]);
    expect(result?.to).toEqual([46.5, 30]);
    expect(result?.displacementM).toBeCloseTo(1.5);
    expect(result?.baselineFrame).toBe(original);
    expect(result?.alternativeFrame).not.toBe(original);

    const moved = result?.alternativeFrame.players.find(
      (candidate) => candidate.player_id === "runner-a",
    );
    expect(moved?.x).toBeCloseTo(46.5);
    expect(moved?.y).toBeCloseTo(30);
    expect(moved?.vx).toBe(2);
    expect(moved?.vy).toBe(0);
    expect(original.players[1]?.x).toBe(45);
  });

  it("breaks equal-speed ties by stable player id", () => {
    const result = buildEarlierRunIntervention(
      frame([
        player("carrier", "home", 30, 20, 0, 0),
        player("z-runner", "home", 45, 30, 1, 0),
        player("a-runner", "home", 42, 28, 1, 0),
      ]),
    );
    expect(result?.playerId).toBe("a-runner");
  });

  it("clips the earlier arrival to the declared pitch", () => {
    const result = buildEarlierRunIntervention(
      frame([
        player("carrier", "home", 30, 20, 0, 0),
        player("runner", "home", 104.5, 67.5, 3, 3),
      ]),
      0.75,
    );
    expect(result?.to).toEqual([105, 68]);
    expect(result?.displacementM).toBeCloseTo(Math.sqrt(0.5));
  });

  it("fails closed when no off-ball teammate has meaningful finite motion", () => {
    expect(
      buildEarlierRunIntervention(
        frame([
          player("carrier", "home", 30, 20, 1, 0),
          player("still", "home", 42, 28, 0.1, 0.1),
          player("opponent", "away", 48, 28, 5, 0),
        ]),
      ),
    ).toBeNull();
  });

  it("rejects invalid lead durations", () => {
    const input = frame([
      player("carrier", "home", 30, 20, 0, 0),
      player("runner", "home", 42, 28, 1, 0),
    ]);
    expect(() => buildEarlierRunIntervention(input, 0)).toThrow(/within/u);
    expect(() => buildEarlierRunIntervention(input, 2.1)).toThrow(/within/u);
  });
});
