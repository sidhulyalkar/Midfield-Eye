export const queryKeys = {
  manifest: ["showcase", "manifest"] as const,
  players: ["showcase", "players"] as const,
  player: (id: string) => ["showcase", "players", id] as const,
  scenarios: ["showcase", "scenarios"] as const,
  scenario: (id: string) => ["showcase", "scenarios", id] as const,
  scenarioFrames: (id: string) =>
    ["showcase", "scenarios", id, "frames"] as const,
  scenarioOptions: (id: string) =>
    ["showcase", "scenarios", id, "options"] as const,
  scenarioTimeline: (id: string) =>
    ["showcase", "scenarios", id, "timeline"] as const,
  scenarioGaze: (id: string) => ["showcase", "scenarios", id, "gaze"] as const,
  scenarioBody: (id: string) => ["showcase", "scenarios", id, "body"] as const,
  scenarioRelations: (id: string) =>
    ["showcase", "scenarios", id, "relations"] as const,
  empiricalSources: ["showcase", "empirical", "sources"] as const,
  empiricalExperiments: ["showcase", "empirical", "experiments"] as const,
  empiricalExperiment: (id: string) =>
    ["showcase", "empirical", "experiments", id] as const,
  citations: ["showcase", "empirical", "citations"] as const,
};
