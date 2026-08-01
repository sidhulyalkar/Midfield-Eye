import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router";
import { useDataSource } from "../app/providers";
import { EvidenceBadge } from "../components/Evidence";
import { FeedbackState } from "../components/FeedbackState";
import { queryKeys } from "../data/queryKeys";

export default function AtlasPage() {
  const source = useDataSource();
  const [params, setParams] = useSearchParams();
  const players = useQuery({
    queryKey: queryKeys.players,
    queryFn: () => source.listPlayers(),
  });
  const cohort = params.get("cohort") ?? "";
  const query = params.get("q") ?? "";
  const compared = (params.get("compare") ?? "").split(",").filter(Boolean);
  const filtered = useMemo(
    () =>
      players.data?.filter(
        (player) =>
          (!cohort || player.cohort === cohort) &&
          (!query ||
            player.name
              .toLocaleLowerCase()
              .includes(query.toLocaleLowerCase()) ||
            player.signature
              .toLocaleLowerCase()
              .includes(query.toLocaleLowerCase())),
      ) ?? [],
    [cohort, players.data, query],
  );

  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };
  const toggleCompare = (id: string) => {
    const exists = compared.includes(id);
    const nextCompared = exists
      ? compared.filter((item) => item !== id)
      : [...compared, id].slice(-4);
    update("compare", nextCompared.join(","));
  };

  if (players.isPending) {
    return (
      <FeedbackState
        kind="loading"
        title="Opening the perception atlas"
        message="Validating all 100 balanced study profiles."
      />
    );
  }
  if (players.isError) {
    return (
      <FeedbackState
        kind="recoverable_error"
        title="The atlas contract failed"
        message={players.error.message}
        onRetry={() => void players.refetch()}
      />
    );
  }

  return (
    <div className="atlas-page page-pad">
      <header className="page-heading">
        <div>
          <p className="eyebrow">
            Curated research cohort · no ordinal ranking
          </p>
          <h1>100 ways to ask a sharper question.</h1>
          <p>
            Fifty profiles from the men&apos;s game and fifty from the
            women&apos;s game. Every card is a hypothesis, not measured player
            performance.
          </p>
        </div>
        <div className="atlas-balance" aria-label="Cohort balance">
          <span>50</span> men&apos;s game <i /> <span>50</span> women&apos;s
          game
        </div>
      </header>
      <section className="atlas-controls" aria-label="Atlas filters">
        <label>
          <span>Search studies</span>
          <input
            type="search"
            value={query}
            onChange={(event) => update("q", event.target.value)}
            placeholder="Name, role, or research question"
          />
        </label>
        <label>
          <span>Cohort</span>
          <select
            value={cohort}
            onChange={(event) => update("cohort", event.target.value)}
          >
            <option value="">Both cohorts</option>
            <option value="men's game">Men&apos;s game</option>
            <option value="women's game">Women&apos;s game</option>
          </select>
        </label>
        <p>{filtered.length} profiles shown</p>
      </section>
      {filtered.length ? (
        <section className="atlas-grid" aria-label="Player study profiles">
          {filtered.map((player) => (
            <article key={player.id} className="profile-card">
              <div className="profile-card-topline">
                <span>{player.cohort}</span>
                <EvidenceBadge
                  kind="synthetic"
                  source="Editorial research hypothesis"
                />
              </div>
              <Link to={`/players/${player.id}`}>
                <h2>{player.name}</h2>
                <p className="profile-role">{player.display_role}</p>
                <p>{player.signature}</p>
              </Link>
              <div
                className="emphasis-preview"
                aria-label="Research emphasis, not an ability score"
              >
                <span>Research emphasis</span>
                {Object.entries(player.showcase_emphasis)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 3)
                  .map(([name, value]) => (
                    <div key={name}>
                      <span>{name.replaceAll("_", " ")}</span>
                      <i
                        style={{ "--emphasis": value } as React.CSSProperties}
                      />
                    </div>
                  ))}
              </div>
              <label className="compare-toggle">
                <input
                  type="checkbox"
                  checked={compared.includes(player.id)}
                  disabled={
                    !compared.includes(player.id) && compared.length >= 4
                  }
                  onChange={() => toggleCompare(player.id)}
                />
                Add research lenses to tray
              </label>
            </article>
          ))}
        </section>
      ) : (
        <FeedbackState
          kind="empty_filter_result"
          title="No studies match those filters"
          message="Clear the search or include both cohorts."
        />
      )}
      {compared.length >= 2 ? (
        <aside
          className="comparison-tray"
          aria-label="Research comparison tray"
        >
          <span>{compared.length} hypotheses selected</span>
          <p>
            Context-free numeric comparison is blocked; compare questions and
            evidence coverage instead.
          </p>
          <button
            type="button"
            className="button button-secondary"
            onClick={() => update("compare", "")}
          >
            Clear tray
          </button>
        </aside>
      ) : null}
    </div>
  );
}
