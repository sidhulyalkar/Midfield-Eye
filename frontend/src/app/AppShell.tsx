import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet } from "react-router";
import { useDataSource } from "./providers";
import { queryKeys } from "../data/queryKeys";
import { FeedbackState } from "../components/FeedbackState";

const navItems = [
  ["/", "Eye", "Overview"],
  ["/scenario/aitana-overload", "Menu", "Action menu"],
  ["/volume", "3D", "Affordance volume"],
  ["/volume/compare", "Δ", "Difference volume"],
  ["/pilot", "R1", "Real pilot"],
  ["/empirical", "Data", "Evidence"],
  ["/atlas", "100", "Atlas"],
  ["/gaze-lab", "Lab", "Laboratories"],
] as const;

function exactNavMatch(path: string) {
  return path === "/" || path === "/volume";
}

export function AppShell() {
  const source = useDataSource();
  const manifest = useQuery({
    queryKey: queryKeys.manifest,
    queryFn: () => source.getManifest(),
  });

  if (manifest.isPending) {
    return (
      <FeedbackState
        kind="loading"
        title="Validating the evidence contract"
        message="The application will open after the bundle version and required fields pass validation."
      />
    );
  }
  if (manifest.isError) {
    return (
      <FeedbackState
        kind="version_mismatch"
        title="The showcase contract could not be validated"
        message={manifest.error.message}
        onRetry={() => void manifest.refetch()}
      />
    );
  }

  return (
    <div className="app-shell">
      <aside className="nav-rail" aria-label="Primary navigation">
        <NavLink
          className="brand-mark"
          to="/"
          aria-label="The Midfielder's Eye"
        >
          ME
        </NavLink>
        <nav>
          {navItems.map(([to, short, label]) => (
            <NavLink key={to} to={to} end={exactNavMatch(to)} title={label}>
              <span aria-hidden="true">{short}</span>
              <span className="sr-only">{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="app-column">
        <header className="context-bar">
          <NavLink to="/" className="wordmark">
            The Midfielder&apos;s Eye
          </NavLink>
          <div className="context-actions">
            <span className="contract-state">
              <i aria-hidden="true" /> Evidence-aware
            </span>
            <details className="diagnostics">
              <summary>Diagnostics</summary>
              <div>
                <strong>
                  {source.mode === "api" ? "API mode" : "Static bundle"}
                </strong>
                <span>Contract {manifest.data.bundle_version}</span>
                <span>{manifest.data.player_count} study profiles</span>
                <span>
                  {manifest.data.scenario_count} illustrative scenarios
                </span>
              </div>
            </details>
          </div>
        </header>
        <main id="main-content">
          <Outlet />
        </main>
        <nav className="bottom-nav" aria-label="Mobile navigation">
          {navItems.slice(0, 4).map(([to, short, label]) => (
            <NavLink key={to} to={to} end={exactNavMatch(to)}>
              <span aria-hidden="true">{short}</span>
              <small>{label}</small>
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}
