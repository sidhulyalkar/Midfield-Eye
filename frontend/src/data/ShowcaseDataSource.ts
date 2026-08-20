import type { CounterfactualOptionsArtifact } from "./counterfactualOptionsSchemas";
import type {
  ActionOption,
  BodyPayload,
  Citation,
  EmpiricalExperiment,
  EmpiricalSource,
  FrameState,
  GazePayload,
  Health,
  PlayerStudy,
  RelationsPayload,
  Scenario,
  ScenarioSummary,
  ShowcaseManifest,
  TimelinePoint,
} from "./schemas";

export type PlayerFilters = {
  cohort?: string;
  archetype?: string;
  query?: string;
};

export interface ShowcaseDataSource {
  readonly mode: "static" | "api";
  getHealth(): Promise<Health>;
  getManifest(): Promise<ShowcaseManifest>;
  listPlayers(filters?: PlayerFilters): Promise<PlayerStudy[]>;
  getPlayer(playerId: string): Promise<PlayerStudy>;
  listScenarios(): Promise<ScenarioSummary[]>;
  getScenario(scenarioId: string): Promise<Scenario>;
  getScenarioFrames(scenarioId: string): Promise<FrameState[]>;
  getScenarioOptions(scenarioId: string): Promise<ActionOption[]>;
  getCounterfactualOptions(scenarioId: string): Promise<CounterfactualOptionsArtifact>;
  getScenarioTimeline(scenarioId: string): Promise<TimelinePoint[]>;
  getScenarioGaze(scenarioId: string): Promise<GazePayload>;
  getScenarioBody(scenarioId: string): Promise<BodyPayload>;
  getScenarioRelations(scenarioId: string): Promise<RelationsPayload>;
  getEmpiricalManifest(): Promise<Record<string, unknown>>;
  listEmpiricalSources(): Promise<EmpiricalSource[]>;
  listEmpiricalExperiments(): Promise<EmpiricalExperiment[]>;
  getEmpiricalExperiment(experimentId: string): Promise<EmpiricalExperiment>;
  getEvidenceLedger(): Promise<Record<string, unknown>[]>;
  getClaimContract(): Promise<Record<string, unknown>>;
  getCitations(): Promise<Citation[]>;
  getAlignmentContract(): Promise<Record<string, unknown>>;
  getDefaultCaptureProtocol(): Promise<Record<string, unknown>>;
  validateCaptureProtocol(
    protocol: Record<string, unknown>,
  ): Promise<{ valid: boolean; errors: string[]; offline: boolean }>;
  assetUrl(relativePath: string): string;
}
