import { z, type ZodType } from "zod";
import {
  ActionOptionSchema,
  ApiHealthSchema,
  BodyPayloadSchema,
  CitationSchema,
  EmpiricalExperimentSchema,
  EmpiricalSourcesEnvelopeSchema,
  FrameStateSchema,
  GazePayloadSchema,
  GenericObjectSchema,
  ManifestSchema,
  PlayerStudySchema,
  RelationsPayloadSchema,
  ScenarioSchema,
  ScenarioSummarySchema,
  TimelinePointSchema,
  type ActionOption,
  type BodyPayload,
  type Citation,
  type EmpiricalExperiment,
  type EmpiricalSource,
  type FrameState,
  type GazePayload,
  type Health,
  type PlayerStudy,
  type RelationsPayload,
  type Scenario,
  type ScenarioSummary,
  type ShowcaseManifest,
  type TimelinePoint,
} from "./schemas";
import type { PlayerFilters, ShowcaseDataSource } from "./ShowcaseDataSource";

const arrays = {
  players: z.array(PlayerStudySchema),
  scenarios: z.array(ScenarioSummarySchema),
  frames: z.array(FrameStateSchema),
  options: z.array(ActionOptionSchema),
  timeline: z.array(TimelinePointSchema),
  experiments: z.array(EmpiricalExperimentSchema),
  ledger: z.array(GenericObjectSchema),
};

function joinUrl(root: string, path: string): string {
  return `${root.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
}

async function fetchText(url: string): Promise<string> {
  const response = await fetch(url, {
    headers: { Accept: "application/json, text/plain" },
  });
  if (!response.ok) {
    throw new Error(
      `${response.status} ${response.statusText} while loading ${url}`,
    );
  }
  return response.text();
}

async function fetchValidated<T>(url: string, schema: ZodType<T>): Promise<T> {
  const text = await fetchText(url);
  let payload: unknown;
  try {
    payload = JSON.parse(text);
  } catch {
    throw new Error(`Invalid JSON returned by ${url}`);
  }
  return schema.parse(payload);
}

export function parseJsonLines<T>(
  text: string,
  schema: ZodType<T>,
  resource: string,
): T[] {
  const values: T[] = [];
  text.split(/\r?\n/u).forEach((line, index) => {
    if (!line.trim()) return;
    let payload: unknown;
    try {
      payload = JSON.parse(line);
    } catch {
      throw new Error(`Invalid JSON in ${resource} at line ${index + 1}`);
    }
    const result = schema.safeParse(payload);
    if (!result.success) {
      throw new Error(
        `Contract error in ${resource} at line ${index + 1}: ${result.error.message}`,
      );
    }
    values.push(result.data);
  });
  return values;
}

function assertVersion(manifest: ShowcaseManifest): void {
  const [major, minor] = manifest.bundle_version.split(".").map(Number);
  if (major !== 0) {
    throw new Error(
      `Incompatible showcase major version ${manifest.bundle_version}; expected 0.x`,
    );
  }
  if ((minor ?? 0) > 6) {
    console.warn(
      `Showcase ${manifest.bundle_version} is newer than the tested 0.6 contract.`,
    );
  }
}

function assertAtlas(players: PlayerStudy[]): void {
  const men = players.filter((player) => player.cohort === "men's game").length;
  const women = players.filter(
    (player) => player.cohort === "women's game",
  ).length;
  if (players.length !== 100 || men !== 50 || women !== 50) {
    throw new Error(
      `Atlas contract requires exactly 100 profiles balanced 50/50; received ${men}/${women}.`,
    );
  }
  for (const player of players) {
    if ("rank" in player || "rating" in player) {
      throw new Error(`Forbidden rank/rating field found for ${player.id}.`);
    }
  }
}

function filterPlayers(
  players: PlayerStudy[],
  filters?: PlayerFilters,
): PlayerStudy[] {
  if (!filters) return players;
  const query = filters.query?.trim().toLocaleLowerCase();
  return players.filter(
    (player) =>
      (!filters.cohort || player.cohort === filters.cohort) &&
      (!filters.archetype || player.primary_archetype === filters.archetype) &&
      (!query ||
        player.name.toLocaleLowerCase().includes(query) ||
        player.signature.toLocaleLowerCase().includes(query)),
  );
}

abstract class BaseDataSource implements ShowcaseDataSource {
  abstract readonly mode: "static" | "api";
  abstract getHealth(): Promise<Health>;
  abstract getManifest(): Promise<ShowcaseManifest>;
  abstract listPlayers(filters?: PlayerFilters): Promise<PlayerStudy[]>;
  abstract getPlayer(playerId: string): Promise<PlayerStudy>;
  abstract listScenarios(): Promise<ScenarioSummary[]>;
  abstract getScenario(scenarioId: string): Promise<Scenario>;
  abstract getScenarioFrames(scenarioId: string): Promise<FrameState[]>;
  abstract getScenarioOptions(scenarioId: string): Promise<ActionOption[]>;
  abstract getScenarioTimeline(scenarioId: string): Promise<TimelinePoint[]>;
  abstract getScenarioGaze(scenarioId: string): Promise<GazePayload>;
  abstract getScenarioBody(scenarioId: string): Promise<BodyPayload>;
  abstract getScenarioRelations(scenarioId: string): Promise<RelationsPayload>;
  abstract assetUrl(relativePath: string): string;

  abstract resource(path: string): string;

  getEmpiricalManifest(): Promise<Record<string, unknown>> {
    return fetchValidated(
      this.resource("empirical/manifest.json"),
      GenericObjectSchema,
    );
  }
  async listEmpiricalSources(): Promise<EmpiricalSource[]> {
    return (
      await fetchValidated(
        this.resource("empirical/sources.json"),
        EmpiricalSourcesEnvelopeSchema,
      )
    ).sources;
  }
  listEmpiricalExperiments(): Promise<EmpiricalExperiment[]> {
    return fetchValidated(
      this.resource("empirical/experiments.json"),
      arrays.experiments,
    );
  }
  async getEmpiricalExperiment(
    experimentId: string,
  ): Promise<EmpiricalExperiment> {
    const found = (await this.listEmpiricalExperiments()).find(
      (experiment) => experiment.id === experimentId,
    );
    if (!found)
      throw new Error(`Empirical experiment ${experimentId} was not found.`);
    return found;
  }
  getEvidenceLedger(): Promise<Record<string, unknown>[]> {
    return fetchValidated(
      this.resource("empirical/player_evidence_ledger.json"),
      arrays.ledger,
    );
  }
  getClaimContract(): Promise<Record<string, unknown>> {
    return fetchValidated(
      this.resource("empirical/claim_contract.json"),
      GenericObjectSchema,
    );
  }
  async getCitations(): Promise<Citation[]> {
    const payload = await fetchValidated(
      this.resource("empirical/citation_index.json"),
      z.record(z.string(), CitationSchema.omit({ id: true })),
    );
    return Object.entries(payload).map(([id, citation]) =>
      CitationSchema.parse({ id, ...citation }),
    );
  }
  getAlignmentContract(): Promise<Record<string, unknown>> {
    return fetchValidated(
      this.resource("empirical/alignment_contract.json"),
      GenericObjectSchema,
    );
  }
  getDefaultCaptureProtocol(): Promise<Record<string, unknown>> {
    return fetchValidated(
      this.resource("empirical/capture_protocol.json"),
      GenericObjectSchema,
    );
  }
  validateCaptureProtocol(
    protocol: Record<string, unknown>,
  ): Promise<{ valid: boolean; errors: string[]; offline: boolean }> {
    const required = ["protocol_id", "version"];
    const errors = required
      .filter((field) => protocol[field] === undefined)
      .map((field) => `Missing required field: ${field}`);
    return Promise.resolve({
      valid: errors.length === 0,
      errors,
      offline: true,
    });
  }
}

export class StaticShowcaseDataSource extends BaseDataSource {
  readonly mode = "static" as const;
  constructor(private readonly root: string) {
    super();
  }
  resource(path: string): string {
    return joinUrl(this.root, path);
  }
  assetUrl(relativePath: string): string {
    return this.resource(relativePath);
  }
  async getHealth(): Promise<Health> {
    const manifest = await this.getManifest();
    return { status: "ok", bundle_version: manifest.bundle_version };
  }
  async getManifest(): Promise<ShowcaseManifest> {
    const manifest = await fetchValidated(
      this.resource("manifest.json"),
      ManifestSchema,
    );
    assertVersion(manifest);
    return manifest;
  }
  async listPlayers(filters?: PlayerFilters): Promise<PlayerStudy[]> {
    const players = await fetchValidated(
      this.resource("players/index.json"),
      arrays.players,
    );
    assertAtlas(players);
    return filterPlayers(players, filters);
  }
  getPlayer(playerId: string): Promise<PlayerStudy> {
    return fetchValidated(
      this.resource(`players/${encodeURIComponent(playerId)}/profile.json`),
      PlayerStudySchema,
    );
  }
  listScenarios(): Promise<ScenarioSummary[]> {
    return fetchValidated(
      this.resource("scenarios/index.json"),
      arrays.scenarios,
    );
  }
  getScenario(scenarioId: string): Promise<Scenario> {
    return fetchValidated(
      this.resource(
        `scenarios/${encodeURIComponent(scenarioId)}/scenario.json`,
      ),
      ScenarioSchema,
    );
  }
  async getScenarioFrames(scenarioId: string): Promise<FrameState[]> {
    const url = this.resource(
      `scenarios/${encodeURIComponent(scenarioId)}/frames.jsonl`,
    );
    return parseJsonLines(await fetchText(url), FrameStateSchema, url);
  }
  getScenarioOptions(scenarioId: string): Promise<ActionOption[]> {
    return fetchValidated(
      this.resource(`scenarios/${encodeURIComponent(scenarioId)}/options.json`),
      arrays.options,
    );
  }
  getScenarioTimeline(scenarioId: string): Promise<TimelinePoint[]> {
    return fetchValidated(
      this.resource(
        `scenarios/${encodeURIComponent(scenarioId)}/timeline.json`,
      ),
      arrays.timeline,
    );
  }
  getScenarioGaze(scenarioId: string): Promise<GazePayload> {
    return fetchValidated(
      this.resource(`scenarios/${encodeURIComponent(scenarioId)}/gaze.json`),
      GazePayloadSchema,
    );
  }
  getScenarioBody(scenarioId: string): Promise<BodyPayload> {
    return fetchValidated(
      this.resource(
        `scenarios/${encodeURIComponent(scenarioId)}/body_mechanics.json`,
      ),
      BodyPayloadSchema,
    );
  }
  getScenarioRelations(scenarioId: string): Promise<RelationsPayload> {
    return fetchValidated(
      this.resource(
        `scenarios/${encodeURIComponent(scenarioId)}/relational_control.json`,
      ),
      RelationsPayloadSchema,
    );
  }
}

export class ApiShowcaseDataSource extends BaseDataSource {
  readonly mode = "api" as const;
  constructor(private readonly root: string) {
    super();
  }
  resource(path: string): string {
    const mapping: Record<string, string> = {
      "empirical/manifest.json": "api/empirical",
      "empirical/sources.json": "api/empirical/sources",
      "empirical/experiments.json": "api/empirical/experiments",
      "empirical/player_evidence_ledger.json": "api/empirical/player-ledger",
      "empirical/claim_contract.json": "api/empirical/claim-contract",
      "empirical/citation_index.json": "api/empirical/citations",
      "empirical/alignment_contract.json": "api/empirical/alignment-contract",
      "empirical/capture_protocol.json": "api/capture-protocol/default",
    };
    return joinUrl(this.root, mapping[path] ?? path);
  }
  assetUrl(relativePath: string): string {
    return joinUrl(this.root, `api/assets/${relativePath}`);
  }
  getHealth(): Promise<Health> {
    return fetchValidated(joinUrl(this.root, "api/health"), ApiHealthSchema);
  }
  async getManifest(): Promise<ShowcaseManifest> {
    const manifest = await fetchValidated(
      joinUrl(this.root, "api/showcase/manifest"),
      ManifestSchema,
    );
    assertVersion(manifest);
    return manifest;
  }
  async listPlayers(filters?: PlayerFilters): Promise<PlayerStudy[]> {
    const players = await fetchValidated(
      joinUrl(this.root, "api/atlas"),
      arrays.players,
    );
    assertAtlas(players);
    return filterPlayers(players, filters);
  }
  getPlayer(playerId: string): Promise<PlayerStudy> {
    return fetchValidated(
      joinUrl(this.root, `api/players/${encodeURIComponent(playerId)}`),
      PlayerStudySchema,
    );
  }
  listScenarios(): Promise<ScenarioSummary[]> {
    return fetchValidated(
      joinUrl(this.root, "api/scenarios"),
      arrays.scenarios,
    );
  }
  getScenario(scenarioId: string): Promise<Scenario> {
    return fetchValidated(
      joinUrl(this.root, `api/scenarios/${encodeURIComponent(scenarioId)}`),
      ScenarioSchema,
    );
  }
  getScenarioFrames(scenarioId: string): Promise<FrameState[]> {
    return fetchValidated(
      joinUrl(
        this.root,
        `api/scenarios/${encodeURIComponent(scenarioId)}/frames`,
      ),
      arrays.frames,
    );
  }
  getScenarioOptions(scenarioId: string): Promise<ActionOption[]> {
    return fetchValidated(
      joinUrl(
        this.root,
        `api/scenarios/${encodeURIComponent(scenarioId)}/options`,
      ),
      arrays.options,
    );
  }
  getScenarioTimeline(scenarioId: string): Promise<TimelinePoint[]> {
    return fetchValidated(
      joinUrl(
        this.root,
        `api/scenarios/${encodeURIComponent(scenarioId)}/timeline`,
      ),
      arrays.timeline,
    );
  }
  getScenarioGaze(scenarioId: string): Promise<GazePayload> {
    return fetchValidated(
      joinUrl(
        this.root,
        `api/scenarios/${encodeURIComponent(scenarioId)}/gaze`,
      ),
      GazePayloadSchema,
    );
  }
  getScenarioBody(scenarioId: string): Promise<BodyPayload> {
    return fetchValidated(
      joinUrl(
        this.root,
        `api/scenarios/${encodeURIComponent(scenarioId)}/body-mechanics`,
      ),
      BodyPayloadSchema,
    );
  }
  getScenarioRelations(scenarioId: string): Promise<RelationsPayload> {
    return fetchValidated(
      joinUrl(
        this.root,
        `api/scenarios/${encodeURIComponent(scenarioId)}/relational-control`,
      ),
      RelationsPayloadSchema,
    );
  }
  override getEmpiricalExperiment(
    experimentId: string,
  ): Promise<EmpiricalExperiment> {
    return fetchValidated(
      joinUrl(
        this.root,
        `api/empirical/experiments/${encodeURIComponent(experimentId)}`,
      ),
      EmpiricalExperimentSchema,
    );
  }
  override async getCitations(): Promise<Citation[]> {
    const payload = await fetchValidated(
      joinUrl(this.root, "api/empirical/citations"),
      z.union([
        z.array(CitationSchema),
        z.record(z.string(), CitationSchema.omit({ id: true })),
      ]),
    );
    return Array.isArray(payload)
      ? payload
      : Object.entries(payload).map(([id, citation]) =>
          CitationSchema.parse({ id, ...citation }),
        );
  }
  override async validateCaptureProtocol(
    protocol: Record<string, unknown>,
  ): Promise<{ valid: boolean; errors: string[]; offline: boolean }> {
    const response = await fetch(
      joinUrl(this.root, "api/capture-protocol/validate"),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(protocol),
      },
    );
    if (!response.ok)
      throw new Error(`${response.status} while validating capture protocol`);
    const parsed = z
      .object({ valid: z.boolean(), errors: z.array(z.string()) })
      .parse(await response.json());
    return { ...parsed, offline: false };
  }
}

export function createDataSource(): ShowcaseDataSource {
  const configured = import.meta.env.VITE_MIDFIELDERS_EYE_API_URL?.trim();
  if (configured) {
    let parsed: URL;
    try {
      parsed = new URL(configured);
    } catch {
      throw new Error("VITE_MIDFIELDERS_EYE_API_URL must be an absolute URL.");
    }
    if (!["http:", "https:"].includes(parsed.protocol)) {
      throw new Error("VITE_MIDFIELDERS_EYE_API_URL must use http or https.");
    }
    return new ApiShowcaseDataSource(parsed.toString());
  }
  return new StaticShowcaseDataSource(`${import.meta.env.BASE_URL}showcase/`);
}
