from pathlib import Path

from midfielders_eye.dataset_shift import provider_shift_report
from midfielders_eye.multisource_demo import generate_provider_views
from midfielders_eye.provider_benchmark import benchmark_provider_frames
from midfielders_eye.quality import assess_frames

output = Path("artifacts/example_multi_provider")
output.mkdir(parents=True, exist_ok=True)

provider_frames = generate_provider_views(sequences=3, frames_per_sequence=8)
for provider_id, frames in provider_frames.items():
    print(provider_id, assess_frames(frames, provider_id).to_dict())

summary, options = benchmark_provider_frames(provider_frames)
shift = provider_shift_report(options)

summary.to_csv(output / "summary.csv", index=False)
options.to_csv(output / "options.csv", index=False)
shift.to_csv(output / "shift.csv", index=False)
print(summary)
