from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from .pipeline import _derive_company_capacity_signals, _detect_procurement_type, _read_submission_metadata_for_source

MISSING_TEXT = "Not stated in provided text"

REQUIRED_HEADINGS: tuple[str, ...] = (
    "# Capture Intelligence Brief",
    "## BD Opportunity Assessment (Bid/No-Bid Gate Review)",
    "## Executive Summary",
    "## Opportunity Summary",
    "## Requirements Extraction",
    "## Evaluation Criteria and Weightings",
    "## Overall Fit Score",
    "## Proposal Compliance Matrix",
    "## Strategic Recommendations",
)


@dataclass(frozen=True)
class Stage5Result:
    capture_brief_path: Path
    validation_path: Path
    status_path: Path
    procurement_type: str
    success: bool
    missing_headings: list[str]


def _extract_overall_fit_line(scorecard_text: str) -> str:
    for line in scorecard_text.splitlines():
        if line.lower().startswith("overall bd fit score:"):
            return line.strip()
    return f"Overall BD fit score: {MISSING_TEXT}"


def _extract_top_issues(scorecard_text: str, limit: int = 3) -> list[str]:
    issues: list[str] = []
    for line in scorecard_text.splitlines():
        stripped = line.strip()
        if re.match(r"^\d+\.\s+\[(HIGH|MEDIUM|LOW)\]\s+", stripped):
            issues.append(stripped)
        if len(issues) >= limit:
            break
    if issues:
        return issues
    return ["1. [LOW] No high-impact BD issues were identified in source artifacts."]


def _extract_company_name(markdown_text: str, metadata: dict[str, str]) -> str:
    if metadata.get("company"):
        return str(metadata["company"])

    profile_match = re.search(r"^##\s+Submitted Company Profile\s*$", markdown_text, flags=re.MULTILINE)
    if not profile_match:
        return MISSING_TEXT

    profile_slice = markdown_text[profile_match.end() :]
    heading_match = re.search(r"^###\s+(.+)$", profile_slice, flags=re.MULTILINE)
    if heading_match:
        return heading_match.group(1).strip()
    return MISSING_TEXT


def _extract_submission_id(source_path: str, metadata: dict[str, str]) -> str:
    if metadata.get("submissionId"):
        return str(metadata["submissionId"])
    match = re.search(r"sub_\d+", source_path)
    if match:
        return match.group(0)
    return MISSING_TEXT


def _extract_metadata_for_markdown(markdown_path: Path) -> dict[str, str]:
    from_source = _read_submission_metadata_for_source(markdown_path.as_posix())
    normalized: dict[str, str] = {}
    for key, value in from_source.items():
        normalized[str(key)] = str(value)
    return normalized


def _resolve_capture_brief_path(markdown_path: Path, out_path: Path | None) -> Path:
    if out_path is not None:
        return out_path

    base_stem = markdown_path.stem
    if base_stem.endswith("-final"):
        base_stem = base_stem[:-6]
    return markdown_path.parent / f"{base_stem}-capture-brief.md"


def _load_companion_file(markdown_path: Path, suffix: str) -> str:
    base = markdown_path.with_suffix("")
    companion = Path(f"{base}{suffix}")
    if companion.exists():
        return companion.read_text(encoding="utf-8")
    return ""


def _build_capture_brief(
    markdown_text: str,
    markdown_path: Path,
    metadata: dict[str, str],
    procurement_type: str,
    executive_summary: str,
    scorecard: str,
    issues_report: str,
) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    company_name = _extract_company_name(markdown_text, metadata)
    submission_id = _extract_submission_id(markdown_path.as_posix(), metadata)
    overall_fit = _extract_overall_fit_line(scorecard)
    top_issues = _extract_top_issues(scorecard)
    capacity = _derive_company_capacity_signals(markdown_text, markdown_path.as_posix())

    team_size = str(capacity.get("team_size", "")).strip() or MISSING_TEXT
    key_personnel = str(capacity.get("key_personnel", "")).strip() or MISSING_TEXT
    contact = metadata.get("contact", MISSING_TEXT)
    email = metadata.get("email", MISSING_TEXT)
    submitted_at = metadata.get("submittedAt", MISSING_TEXT)

    recommendations: list[str] = [
        "Confirm bid/no-bid decision with leadership using the fit score and top issues.",
        "Map each Section M evaluation factor to a proposal owner and response evidence.",
        "Address capability gaps through teaming, hiring, or explicit scope shaping before submission.",
    ]
    if procurement_type == "intl-dev":
        recommendations.append("Validate donor compliance obligations and GEDSI approach against team composition.")

    issues_lines: list[str] = []
    for line in issues_report.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and len(issues_lines) < 8:
            issues_lines.append(stripped)
    if not issues_lines:
        issues_lines = [f"- {MISSING_TEXT}"]

    executive_lines = [line for line in executive_summary.splitlines() if line.strip()]
    executive_bullets = [line for line in executive_lines if line.startswith("-")][:4]
    if not executive_bullets:
        executive_bullets = [f"- {overall_fit}"]

    lines = [
        "# Capture Intelligence Brief",
        f"**{company_name}**",
        "Prepared by MarketEdge RFP Budget Analyzer",
        f"Submission ID: {submission_id}",
        f"Analysis Date: {today}",
        "",
        "## BD Opportunity Assessment (Bid/No-Bid Gate Review)",
        "This brief consolidates the solicitation analysis into a decision-ready capture view.",
        "",
        "## Executive Summary",
        *executive_bullets,
        "",
        "## Opportunity Summary",
        "| Field | Value |",
        "|---|---|",
        f"| Company | {company_name} |",
        f"| Contact | {contact} |",
        f"| Email | {email} |",
        f"| Submission ID | {submission_id} |",
        f"| Submitted | {submitted_at} |",
        f"| Procurement Type | {procurement_type} |",
        f"| Team Size | {team_size} |",
        f"| Key Personnel | {key_personnel} |",
        "",
        "## Requirements Extraction",
        "Mandatory Qualifications and Eligibility Gates:",
        f"- {MISSING_TEXT}",
        "",
        "Technical Requirements by PWS Section:",
        f"- {MISSING_TEXT}",
        "",
        "## Evaluation Criteria and Weightings",
        "| Evaluation Factor | Weight / Importance | Relative to Price | Pass/Fail Gate |",
        "|---|---|---|---|",
        f"| {MISSING_TEXT} | {MISSING_TEXT} | {MISSING_TEXT} | {MISSING_TEXT} |",
        "",
        "## Overall Fit Score",
        f"- {overall_fit}",
        "",
        "Top 3 highest-priority BD issues:",
        *top_issues,
        "",
        "## Proposal Compliance Matrix",
        "| Requirement | Source Section | Proposal Volume | Compliant Y/N | Action Required |",
        "|---|---|---|---|---|",
        f"| {MISSING_TEXT} | {MISSING_TEXT} | {MISSING_TEXT} | TBD | Review solicitation source text |",
        "",
        "## Strategic Recommendations",
        *[f"- {item}" for item in recommendations],
        "",
        "## Supporting Issue Signals",
        *issues_lines,
    ]
    return "\n".join(lines).strip() + "\n"


def _validate_capture_brief(content: str) -> list[str]:
    missing: list[str] = []
    for heading in REQUIRED_HEADINGS:
        if heading not in content:
            missing.append(heading)
    return missing


def generate_capture_brief(
    markdown_path: Path,
    out_path: Path | None = None,
    metadata_path: Path | None = None,
) -> Stage5Result:
    markdown_text = markdown_path.read_text(encoding="utf-8")
    metadata = _extract_metadata_for_markdown(markdown_path)

    if metadata_path is not None and metadata_path.exists():
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                for key, value in payload.items():
                    if isinstance(value, (str, int, float, bool)):
                        metadata[str(key)] = str(value)
        except json.JSONDecodeError:
            pass

    procurement_type = _detect_procurement_type(markdown_text, markdown_path.as_posix())
    executive_summary = _load_companion_file(markdown_path, ".executive-summary.md")
    scorecard = _load_companion_file(markdown_path, ".scorecard.md")
    issues_report = _load_companion_file(markdown_path, ".issues.md")

    capture_brief = _build_capture_brief(
        markdown_text=markdown_text,
        markdown_path=markdown_path,
        metadata=metadata,
        procurement_type=procurement_type,
        executive_summary=executive_summary,
        scorecard=scorecard,
        issues_report=issues_report,
    )
    missing_headings = _validate_capture_brief(capture_brief)

    target_path = _resolve_capture_brief_path(markdown_path, out_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(capture_brief, encoding="utf-8")

    validation_path = target_path.with_suffix(".validation.json")
    status_path = target_path.with_suffix(".status.json")

    validation_payload = {
        "captureBriefPath": target_path.as_posix(),
        "missingHeadings": missing_headings,
        "requiredHeadingCount": len(REQUIRED_HEADINGS),
    }
    validation_path.write_text(json.dumps(validation_payload, indent=2) + "\n", encoding="utf-8")

    success = len(missing_headings) == 0 and len(capture_brief.strip()) > 0
    status_payload = {
        "success": success,
        "procurementType": procurement_type,
        "captureBriefPath": target_path.as_posix(),
        "validationPath": validation_path.as_posix(),
        "missingHeadings": missing_headings,
    }
    status_path.write_text(json.dumps(status_payload, indent=2) + "\n", encoding="utf-8")

    return Stage5Result(
        capture_brief_path=target_path,
        validation_path=validation_path,
        status_path=status_path,
        procurement_type=procurement_type,
        success=success,
        missing_headings=missing_headings,
    )
