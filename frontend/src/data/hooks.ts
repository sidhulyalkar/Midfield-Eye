import { useQueries, useQuery } from "@tanstack/react-query";
import { useDataSource } from "../app/providers";
import { loadCounterfactualOptionsArtifact } from "./counterfactualOptionsLoader";
import { queryKeys } from "./queryKeys";

export function useScenarioBundle(scenarioId: string) {
  const source = useDataSource();
  const results = useQueries({
    queries: [
      {
        queryKey: queryKeys.scenario(scenarioId),
        queryFn: () => source.getScenario(scenarioId),
      },
      {
        queryKey: queryKeys.scenarioFrames(scenarioId),
        queryFn: () => source.getScenarioFrames(scenarioId),
      },
      {
        queryKey: queryKeys.scenarioOptions(scenarioId),
        queryFn: () => source.getScenarioOptions(scenarioId),
      },
      {
        queryKey: queryKeys.scenarioTimeline(scenarioId),
        queryFn: () => source.getScenarioTimeline(scenarioId),
      },
      {
        queryKey: queryKeys.scenarioGaze(scenarioId),
        queryFn: () => source.getScenarioGaze(scenarioId),
      },
      {
        queryKey: queryKeys.scenarioBody(scenarioId),
        queryFn: () => source.getScenarioBody(scenarioId),
      },
      {
        queryKey: queryKeys.scenarioRelations(scenarioId),
        queryFn: () => source.getScenarioRelations(scenarioId),
      },
    ],
  });
  const error = results.find((result) => result.isError)?.error;
  return {
    scenario: results[0].data,
    frames: results[1].data,
    options: results[2].data,
    timeline: results[3].data,
    gaze: results[4].data,
    body: results[5].data,
    relations: results[6].data,
    isPending: results.some((result) => result.isPending),
    error,
    retry: () => {
      for (const result of results) void result.refetch();
    },
  };
}

export function useScenarioCounterfactualOptions(scenarioId: string) {
  const source = useDataSource();
  return useQuery({
    queryKey: queryKeys.scenarioCounterfactualOptions(scenarioId),
    queryFn: () => loadCounterfactualOptionsArtifact(source, scenarioId),
  });
}

export function useScenarios() {
  const source = useDataSource();
  return useQuery({
    queryKey: queryKeys.scenarios,
    queryFn: () => source.listScenarios(),
  });
}
