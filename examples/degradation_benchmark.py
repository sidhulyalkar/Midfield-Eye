from midfielders_eye.robustness import benchmark_degradation, default_degradation_suite
from midfielders_eye.synthetic import generate_dataset

frames = generate_dataset(sequences=2, frames=6, seed=7)
metrics, _ = benchmark_degradation(frames, default_degradation_suite(seed=7))
print(metrics.groupby("degradation").mean(numeric_only=True))
