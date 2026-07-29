from pathlib import Path

from midfielders_eye.affordance import AffordanceEngine
from midfielders_eye.synthetic import generate_sequence
from midfielders_eye.visualization import plot_affordance_frame

frame = generate_sequence(sequence_index=0, frames=1)[0]
options = AffordanceEngine().generate(frame)

for option in sorted(options, key=lambda item: item.geometric_score, reverse=True)[:5]:
    print(
        option.kind,
        option.target_player_id,
        round(option.geometric_score, 3),
        round(option.features["visibility"], 3),
        round(option.features["interception_margin_s"], 3),
    )

plot_affordance_frame(frame, options, Path("artifacts/quickstart.png"))
