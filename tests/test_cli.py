from typer.testing import CliRunner

from midfielders_eye.cli import app


def test_demo_cli(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "demo",
            "--output-dir",
            str(tmp_path),
            "--sequences",
            "3",
            "--frames-per-sequence",
            "2",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "metrics.json").exists()
    assert (tmp_path / "affordance_demo.png").exists()
