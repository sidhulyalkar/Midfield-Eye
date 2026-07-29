import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { useDataSource } from "../app/providers";
import { EvidenceBadge, MissingSignal } from "../components/Evidence";
import { FeedbackState } from "../components/FeedbackState";
import { queryKeys } from "../data/queryKeys";

export default function PlayerPage({
  perception = false,
}: {
  perception?: boolean;
}) {
  const { playerId = "" } = useParams();
  const source = useDataSource();
  const player = useQuery({
    queryKey: queryKeys.player(playerId),
    queryFn: () => source.getPlayer(playerId),
  });

  if (player.isPending) {
    return (
      <FeedbackState
        kind="loading"
        title="Opening the study profile"
        message="Checking evidence status and editorial hypotheses."
      />
    );
  }
  if (player.isError) {
    return (
      <FeedbackState
        kind="not_found"
        title="Study profile unavailable"
        message={player.error.message}
      />
    );
  }

  const item = player.data;
  return (
    <div className="player-page page-pad">
      <header className="player-hero">
        <div>
          <p className="eyebrow">
            {item.cohort} · {item.display_role}
          </p>
          <h1>{item.name}</h1>
          <p>{item.signature}</p>
          <EvidenceBadge
            kind="synthetic"
            source="Editorial research hypothesis"
          />
        </div>
        {item.profile_card ? (
          <img
            src={source.assetUrl(item.profile_card)}
            alt={`${item.name} research profile card without player photography`}
            width="1600"
            height="900"
          />
        ) : null}
      </header>
      <nav className="subnav" aria-label="Player study views">
        <Link
          className={!perception ? "active" : ""}
          to={`/players/${item.id}`}
        >
          Study
        </Link>
        <Link
          className={perception ? "active" : ""}
          to={`/players/${item.id}/perception`}
        >
          Perception questions
        </Link>
      </nav>
      {perception ? (
        <section className="profile-section-grid">
          <article className="question-panel">
            <p className="eyebrow">Questions to test</p>
            <h2>Perception is not yet measured here.</h2>
            <ol>
              {item.study_questions.map((question) => (
                <li key={question}>{question}</li>
              ))}
            </ol>
          </article>
          <MissingSignal
            signal="Named-player gaze timeline"
            reason="No calibrated, source-pinned eye-gaze record is attached to this profile."
            path="Upgrade with consented eye-gaze plus synchronized wide tracking."
          />
          <MissingSignal
            signal="Direct biomechanics"
            reason="Illustrative body mechanics are proxies; force and weight transfer are not directly measured."
            path="Upgrade with a registered kinematics or kinetics source."
          />
        </section>
      ) : (
        <>
          <section className="profile-section-grid">
            <article className="question-panel">
              <p className="eyebrow">Editorial hypothesis</p>
              <h2>What this profile helps us notice.</h2>
              <ul>
                {item.talent_lenses?.map((lens) => (
                  <li key={lens}>{lens}</li>
                ))}
              </ul>
            </article>
            <article className="question-panel">
              <p className="eyebrow">Falsification</p>
              <h2>What would weaken the hypothesis.</h2>
              <p>
                Context-balanced, rights-cleared sequences that show no reliable
                change in option availability, visibility, value, or creation
                under the stated lens.
              </p>
            </article>
          </section>
          <section className="emphasis-detail">
            <header>
              <p className="eyebrow">Illustrative archetype profile</p>
              <h2>Research emphasis—not ability, rank, or percentile.</h2>
            </header>
            <div>
              {Object.entries(item.showcase_emphasis).map(([name, value]) => (
                <div key={name}>
                  <span>{name.replaceAll("_", " ")}</span>
                  <i style={{ "--emphasis": value } as React.CSSProperties} />
                  <code>{value.toFixed(2)}</code>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
