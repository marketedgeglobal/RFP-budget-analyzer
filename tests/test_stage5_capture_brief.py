from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdf_multi_agent_analysis.stage5_capture_brief import MISSING_TEXT, generate_capture_brief


def test_generate_capture_brief_writes_expected_artifacts(tmp_path) -> None:
    final_md = tmp_path / "sample-final.md"
    final_md.write_text(
        "\n".join(
            [
                "<!-- procurement-type: us-federal -->",
                "# Final Synthesized Output: sample",
                "",
                "## Submitted Company Profile",
                "### Example Company LLC",
                "**Team Size:** 11-50",
                "**Key Personnel:** Capture Manager, Technical Lead",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    (tmp_path / "sample-final.executive-summary.md").write_text(
        "## Bid or No-Bid Snapshot\n- Recommendation: Conditional Pursue\n",
        encoding="utf-8",
    )
    (tmp_path / "sample-final.scorecard.md").write_text(
        "Overall BD fit score: 62.5/100 - Conditional Pursue\n\n1. [HIGH] Missing required credential in Section M\n",
        encoding="utf-8",
    )
    (tmp_path / "sample-final.issues.md").write_text(
        "# BD Issues Summary\n\n- Missing required credential in Section M\n",
        encoding="utf-8",
    )

    result = generate_capture_brief(final_md)

    assert result.success
    assert result.capture_brief_path.exists()
    assert result.validation_path.exists()
    assert result.status_path.exists()

    content = result.capture_brief_path.read_text(encoding="utf-8")
    assert "# Capture Intelligence Brief" in content
    assert "## Strategic Recommendations" in content
    assert "Overall BD fit score: 62.5/100 - Conditional Pursue" in content


def test_generate_capture_brief_defaults_to_not_stated_when_missing_inputs(tmp_path) -> None:
    final_md = tmp_path / "minimal-final.md"
    final_md.write_text("# Minimal\n", encoding="utf-8")

    result = generate_capture_brief(final_md)
    assert result.success

    content = result.capture_brief_path.read_text(encoding="utf-8")
    assert MISSING_TEXT in content
