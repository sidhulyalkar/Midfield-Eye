import { lazy, Suspense } from "react";
import { createBrowserRouter } from "react-router";
import { AppShell } from "./AppShell";
import { FeedbackState } from "../components/FeedbackState";

const LandingPage = lazy(() => import("../pages/LandingPage"));
const ScenarioPage = lazy(() => import("../pages/ScenarioPage"));
const PilotPage = lazy(() => import("../pages/PilotPage"));
const VolumePage = lazy(() => import("../pages/VolumePage"));
const EmpiricalPage = lazy(() => import("../pages/EmpiricalPage"));
const EmpiricalExperimentPage = lazy(
  () => import("../pages/EmpiricalExperimentPage"),
);
const AtlasPage = lazy(() => import("../pages/AtlasPage"));
const PlayerPage = lazy(() => import("../pages/PlayerPage"));
const LabPage = lazy(() => import("../pages/LabPage"));
const MethodPage = lazy(() => import("../pages/MethodPage"));

function loading(element: React.ReactNode) {
  return (
    <Suspense
      fallback={
        <FeedbackState
          kind="loading"
          title="Preparing the analysis"
          message="Validating evidence and tactical state…"
        />
      }
    >
      {element}
    </Suspense>
  );
}

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    errorElement: (
      <main className="route-error">
        <FeedbackState
          kind="recoverable_error"
          title="This view could not be opened"
          message="The route or its evidence resource is unavailable."
        />
      </main>
    ),
    children: [
      { index: true, element: loading(<LandingPage />) },
      { path: "scenario/:scenarioId", element: loading(<ScenarioPage />) },
      { path: "pilot", element: loading(<PilotPage />) },
      { path: "volume", element: loading(<VolumePage />) },
      { path: "empirical", element: loading(<EmpiricalPage />) },
      {
        path: "empirical/experiments/:experimentId",
        element: loading(<EmpiricalExperimentPage />),
      },
      { path: "atlas", element: loading(<AtlasPage />) },
      { path: "players/:playerId", element: loading(<PlayerPage />) },
      {
        path: "players/:playerId/perception",
        element: loading(<PlayerPage perception />),
      },
      { path: "gaze-lab", element: loading(<LabPage lab="gaze" />) },
      { path: "body-mechanics", element: loading(<LabPage lab="body" />) },
      {
        path: "orchestration",
        element: loading(<LabPage lab="orchestration" />),
      },
      {
        path: "perception-lab",
        element: loading(<LabPage lab="perception" />),
      },
      { path: "method", element: loading(<MethodPage page="method" />) },
      {
        path: "data-and-rights",
        element: loading(<MethodPage page="rights" />),
      },
      {
        path: "*",
        element: (
          <FeedbackState
            kind="not_found"
            title="That analysis does not exist"
            message="Choose a study from the navigation."
          />
        ),
      },
    ],
  },
]);
