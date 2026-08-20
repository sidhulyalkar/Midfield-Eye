import type { ShowcaseDataSource } from "./ShowcaseDataSource";
import { validateCounterfactualOptionsArtifact } from "./counterfactualOptionsContract";
import {
  CounterfactualOptionsArtifactSchema,
  type CounterfactualOptionsArtifact,
} from "./counterfactualOptionsSchemas";

export function counterfactualOptionsAssetPath(scenarioId: string): string {
  const normalized = scenarioId.trim();
  if (!normalized) {
    throw new Error("Counterfactual options require a non-empty scenario ID.");
  }
  return `scenarios/${encodeURIComponent(normalized)}/counterfactual_options.json`;
}

export async function loadCounterfactualOptionsArtifact(
  source: Pick<ShowcaseDataSource, "assetUrl">,
  scenarioId: string,
): Promise<CounterfactualOptionsArtifact> {
  const path = counterfactualOptionsAssetPath(scenarioId);
  const url = source.assetUrl(path);
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(
      `${response.status} ${response.statusText} while loading counterfactual options for ${scenarioId}`,
    );
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`Invalid JSON returned by ${url}`);
  }
  const artifact = CounterfactualOptionsArtifactSchema.parse(payload);
  return validateCounterfactualOptionsArtifact(artifact, scenarioId);
}
