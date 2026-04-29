from pathlib import Path
from datetime import datetime, timezone
import json
import os
import re
from difflib import SequenceMatcher

from .agents import AnalystAgent, ExtractorAgent, LegalRiskAgent, ReviewerAgent, SynthesizerAgent
from .assets_context import build_assets_context_with_status
from .chunking import chunk_markdown
from .config import PipelineConfig
from .converter import pdf_to_markdown


FINAL_OUTPUT_DIR = Path("rfp-markdown/generated")
AUDIT_ROOT_DIR = Path("rfp-markdown/audit")

BD_SCORE_DIMENSIONS: list[dict[str, object]] = [
    {
        "name": "Technical Capability",
        "weight": 30,
        "positive_terms": (
            "performance work statement",
            "pws",
            "technical approach",
            "quality control",
            "deliverable",
            "methodology",
            "task order",
            "statement of work",
            "scope",
        ),
        "negative_terms": (
            "ambiguous",
            "unclear",
            "contradict",
            "conflict",
            "not stated",
            "gap",
        ),
    },
    {
        "name": "Past Performance Relevance",
        "weight": 25,
        "positive_terms": (
            "past performance",
            "cpars",
            "relevancy",
            "recency",
            "reference",
            "similar scope",
        ),
        "negative_terms": (
            "minimum of",
            "within the last",
            "must demonstrate",
            "required examples",
            "same or similar",
        ),
    },
    {
        "name": "Certifications and Socioeconomic",
        "weight": 20,
        "positive_terms": (
            "small business",
            "set-aside",
            "8(a)",
            "hubzone",
            "sdvosb",
            "wosb",
            "certification",
            "sam registration",
        ),
        "negative_terms": (
            "ineligible",
            "size standard",
            "excluding",
            "must be certified",
            "disqual",
        ),
    },
    {
        "name": "Contract Vehicle Access",
        "weight": 15,
        "positive_terms": (
            "contract vehicle",
            "idiq",
            "bpa",
            "schedule",
            "gwac",
            "naics",
            "ordering period",
        ),
        "negative_terms": (
            "vehicle holder",
            "restricted",
            "incumbent",
            "only",
            "limited to",
        ),
    },
    {
        "name": "Team Capacity",
        "weight": 10,
        "positive_terms": (
            "key personnel",
            "resume",
            "labor category",
            "fte",
            "hours",
            "transition",
            "mobilization",
            "clearance",
            "staffing",
        ),
        "negative_terms": (
            "within 15 days",
            "within 30 days",
            "immediate",
            "hard-to-fill",
            "scarce",
            "high risk",
        ),
    },
]

RECOMMENDATION_BANDS: tuple[tuple[int, str], ...] = (
    (75, "Strong Pursue"),
    (60, "Conditional Pursue"),
    (45, "Selective Pursue"),
    (0, "Pass"),
)

BD_ISSUE_BONUS_TERMS: tuple[tuple[tuple[str, ...], int], ...] = (
    (("disqual", "ineligible", "non-responsive", "unacceptable", "must have"), 6),
    (("fail", "rejected", "not receive an award", "will not receive an award"), 5),
    (("evaluation", "section m", "best value", "lpta", "tradeoff"), 4),
    (("incumbent", "brand-name", "sole source", "restricted"), 3),
    (("cost realism", "ceiling", "nte", "budget"), 3),
    (("past performance", "cpars", "relevancy", "recency"), 3),
    (("set-aside", "naics", "size standard", "small business"), 3),
    (("transition", "mobilization", "key personnel", "clearance"), 2),
    (("unclear", "ambiguous", "conflict", "contradict"), 2),
)

BD_ISSUE_PENALTY_TERMS: tuple[tuple[str, ...], ...] = (
    ("incorporated by reference", "same force and effect", "computer generated forms"),
    ("government will", "contractor shall"),
)

DEFAULT_FIRST_SECTION_HEADING = "Opportunity Scope"

PIPELINE_STAGE_LABELS: tuple[str, ...] = (
    "Stage C Final Markdown",
    "Stage B Executive Refinement",
    "Stage A Notes",
    "Stage A Critique",
    "Stage D",
)

KNOWN_CONTRACT_SECTION_HEADINGS: tuple[str, ...] = (
    "Definitions",
    "Definitions and Interpretation",
    "Services and Fees",
    "Services",
    "Term",
    "Termination",
    "Confidentiality",
    "Indemnification",
    "Limitation of Liability",
    "Data Protection",
    "Governing Law",
    "Notices",
    "Miscellaneous",
)

KNOWN_COMPLETE_LEADING_WORDS: set[str] = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "if",
    "in",
    "is",
    "it",
    "may",
    "must",
    "of",
    "on",
    "or",
    "shall",
    "the",
    "to",
    "with",
    "without",
    "will",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _make_audit_run_id() -> str:
    run_id = os.getenv("GITHUB_RUN_ID", "").strip()
    run_attempt = os.getenv("GITHUB_RUN_ATTEMPT", "").strip()
    if run_id and run_attempt:
        return f"{run_id}-{run_attempt}"
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _normalize_bullet_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _truncate_at_word_boundary(text: str, limit: int) -> str:
    normalized = _normalize_bullet_text(text)
    if len(normalized) <= limit:
        return normalized
    window = normalized[:limit].rstrip()
    cut = window.rfind(" ")
    if cut >= max(40, int(limit * 0.6)):
        return window[:cut].rstrip() + "..."
    return window + "..."


def _looks_like_far_clause_dump(text: str) -> bool:
    normalized = _normalize_bullet_text(text)
    if len(normalized) < 220:
        return False
    clause_hits = len(re.findall(r"\b52\.\d{3}-\d+\b", normalized))
    return clause_hits >= 3


def _contains_bd_decision_signal(text: str) -> bool:
    lowered = _normalize_bullet_text(text).lower()
    signal_terms = (
        "award",
        "evaluation",
        "set-aside",
        "small business",
        "naics",
        "past performance",
        "technical evaluation",
        "dispatch",
        "price reasonableness",
        "cost realism",
        "incumbent",
        "transition",
        "mobilization",
        "labor category",
        "key personnel",
        "ceiling",
        "budget",
        "ige",
        "disqual",
        "unacceptable",
        "ranking",
    )
    return any(term in lowered for term in signal_terms)


def _is_low_signal_finding(text: str) -> bool:
    normalized = _normalize_bullet_text(text)
    if not normalized:
        return True

    lowered = normalized.lower()
    if _is_pipeline_stage_label(normalized):
        return True

    # Drop obvious extraction fragments and repetitive clause carryover.
    if len(normalized) < 28:
        return True
    if re.match(r"^[A-Z]\.\d+\s*--\s*\|", normalized):
        return True
    if re.match(r"^\([a-z0-9]+\)\s", lowered):
        return True
    if normalized[0].islower():
        return True
    if "|" in normalized:
        return True
    if re.match(r"^[a-z]{1,3}\s", normalized) and _strip_leading_partial_word(normalized) != normalized:
        return True
    if _looks_like_far_clause_dump(normalized):
        return True
    if "incorporates one or more solicitation provisions by reference" in lowered:
        return True
    if not _contains_bd_decision_signal(normalized):
        return True
    return False


def _summarize_finding_for_reader(text: str) -> str:
    normalized = _normalize_bullet_text(text)
    lowered = normalized.lower()

    if "operational acceptability" in lowered and "price reasonableness" in lowered and "past performance" in lowered:
        return "Award appears to be based on a three-part screen: operational acceptability, price reasonableness, and past performance dependability risk."

    if "set-aside" in lowered and "small business" in lowered:
        return "Set-aside language indicates award access may depend on small-business status and NAICS eligibility."

    if "technical evaluation" in lowered and ("must pass" in lowered or "pass" in lowered):
        return "A pass/fail technical evaluation gate appears before award consideration."

    if "will not receive an award" in lowered or "may be found unacceptable" in lowered or "rejected" in lowered:
        return "The solicitation includes explicit disqualification language for non-compliant technical submissions."

    if "dispatch" in lowered and "lowest price" in lowered:
        return "Dispatch priority appears to favor lower-priced offers within category constraints."

    if "socioeconomic" in lowered and "advantage" in lowered:
        return "Socioeconomic status appears to influence dispatch ranking, which can affect win probability after award."

    if "incident" in lowered and "host agency" in lowered:
        return "Order execution and invoicing may vary by host agency, so performance operations should plan for multi-agency administration."

    if "will not receive pay" in lowered or ("demobilized" in lowered and "cannot become compliant" in lowered):
        return "Non-compliant resources may be demobilized without pay, creating a direct execution and financial risk if readiness checks are weak."

    if "ordering procedures" in lowered and "mobilization guides" in lowered:
        return "Ordering appears tied to national and regional mobilization guides, so dispatch operations should be aligned before kickoff."

    if "dispatch ranking" in lowered and "may not be used" in lowered:
        return "Dispatch ranking may not always apply for prescribed project work, which can reduce predictability of assignment volume."

    if "award evaluation factors" in lowered and "dispatch priority" in lowered:
        return "Award evaluation and dispatch-priority criteria appear linked for some resource categories, so pricing and capability positioning should be coordinated."

    return ""


def _rewrite_pipeline_jargon(text: str) -> str:
    rewritten = _normalize_bullet_text(text)
    replacements: tuple[tuple[str, str], ...] = (
        ("cross-chunk synthesis", "full-document synthesis"),
        ("Classify this chunk as pursue, conditional pursue, or pass based on bid-impact evidence.", "Set a preliminary bid posture (pursue, conditional pursue, or pass) based on the evidence in this section."),
        ("chunk", "solicitation section"),
        ("decision-neutral in isolation", "not decisive on its own"),
        ("Classify this chunk", "Classify this solicitation section"),
    )
    for old, new in replacements:
        rewritten = re.sub(re.escape(old), new, rewritten, flags=re.IGNORECASE)
    return rewritten


def _is_reader_friendly_duplicate(existing: list[str], candidate: str) -> bool:
    canonical = _canonicalize_bullet_text(candidate)
    if not canonical:
        return True
    for item in existing:
        if _are_near_duplicate_bullets(item, candidate):
            return True
    return False


def _canonicalize_exact_clause_text(text: str) -> str:
    # Exact-match dedupe key for legal clause extracts: case-insensitive + trim-only.
    return text.strip().lower()


def _canonicalize_bullet_text(text: str) -> str:
    normalized = _normalize_bullet_text(text).lower()
    # Strip punctuation for stable deduplication keys while preserving token order.
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _is_reference_assets_boilerplate(text: str) -> bool:
    canonical = _canonicalize_bullet_text(text)
    if not canonical:
        return False

    has_reference_assets = bool(
        re.search(r"\b(reference\s+assets?|assets?)\b", canonical)
        and re.search(r"\b(available|loaded|load|provided|included|attached|supplied|present)\b", canonical)
    )
    has_redline_strategy = bool(
        re.search(r"\bredline\w*\b", canonical)
        and re.search(r"\b(strategy|strategic|approach|plan|playbook|method)\b", canonical)
    )
    has_internal_standards = bool(re.search(r"\binternal\s+(standard|standards|baseline|playbook|templates?)\b", canonical))
    return has_reference_assets and has_redline_strategy and has_internal_standards


def _strip_numbered_heading_prefix(text: str) -> str:
    stripped = text.strip()
    return re.sub(r"^\d+\.\s*", "", stripped).strip()


def _looks_like_known_heading_vocabulary(text: str) -> bool:
    base = _strip_numbered_heading_prefix(text).lower()
    return any(base == heading.lower() for heading in KNOWN_CONTRACT_SECTION_HEADINGS)


def _contains_action_verb(text: str) -> bool:
    lowered = _strip_numbered_heading_prefix(text).lower()
    return bool(
        re.search(
            r"\b(?:maintain(?:s|ed|ing)?|provide(?:s|d|ing)?|terminate(?:s|d|ing)?|perform(?:s|ed|ing)?|deliver(?:s|ed|ing)?|execute(?:s|d|ing)?|shall|may|agree(?:s|d|ing)?)\b",
            lowered,
        )
    )


def _strip_leading_partial_word(text: str) -> str:
    stripped = text.strip()
    match = re.match(r"^([a-z]{1,3})\s+(.+)$", stripped)
    if not match:
        return stripped
    leading = match.group(1)
    if leading in KNOWN_COMPLETE_LEADING_WORDS:
        return stripped
    return match.group(2).strip()


def _canonicalize_legal_risk_text(text: str) -> str:
    stripped = _normalize_bullet_text(text)
    if not stripped:
        return ""
    lowered = _strip_leading_partial_word(stripped).strip().lower()
    lowered = re.sub(r"^(?:the|a|an)\s+", "", lowered)
    return re.sub(r"\s+", " ", lowered)


def _is_more_complete_legal_risk(candidate: str, existing: str) -> bool:
    candidate_clean = _normalize_bullet_text(candidate)
    existing_clean = _normalize_bullet_text(existing)
    if len(candidate_clean) != len(existing_clean):
        return len(candidate_clean) > len(existing_clean)

    candidate_has_partial_prefix = _strip_leading_partial_word(candidate_clean) != candidate_clean
    existing_has_partial_prefix = _strip_leading_partial_word(existing_clean) != existing_clean
    if candidate_has_partial_prefix != existing_has_partial_prefix:
        return not candidate_has_partial_prefix

    return candidate_clean < existing_clean


def _are_near_duplicate_bullets(existing: str, candidate: str) -> bool:
    existing_key = _canonicalize_bullet_text(existing)
    candidate_key = _canonicalize_bullet_text(candidate)
    if not existing_key or not candidate_key:
        return False
    if existing_key == candidate_key:
        return True

    existing_tokens = set(existing_key.split())
    candidate_tokens = set(candidate_key.split())
    if not existing_tokens or not candidate_tokens:
        return False

    intersection = existing_tokens & candidate_tokens
    union = existing_tokens | candidate_tokens
    token_jaccard = len(intersection) / len(union)
    overlap_existing = len(intersection) / len(existing_tokens)
    overlap_candidate = len(intersection) / len(candidate_tokens)
    seq_ratio = SequenceMatcher(None, existing_key, candidate_key).ratio()

    # Conservative near-duplicate rules to avoid collapsing distinct legal insights.
    if seq_ratio >= 0.95 and token_jaccard >= 0.8:
        return True
    if min(len(existing_key), len(candidate_key)) >= 50 and (
        existing_key in candidate_key or candidate_key in existing_key
    ) and max(overlap_existing, overlap_candidate) >= 0.9:
        return True
    return False


def _append_unique_bullet(
    items: list[str],
    seen_exact_keys: set[str],
    candidate: str,
) -> bool:
    normalized = _normalize_bullet_text(candidate)
    key = _canonicalize_bullet_text(normalized)
    if not normalized or not key or key in seen_exact_keys:
        return False
    if any(_are_near_duplicate_bullets(existing, normalized) for existing in items):
        return False
    seen_exact_keys.add(key)
    items.append(normalized)
    return True


def _parse_assets_context_sections(assets_context: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_name: str | None = None

    for line in assets_context.splitlines():
        header = re.match(r"^##\s+(.+)$", line.strip())
        if header:
            current_name = header.group(1).strip()
            sections[current_name] = []
            continue
        if current_name is None:
            continue
        sections[current_name].append(line)

    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def _append_reference_assets_section(
    lines: list[str],
    assets_context: str,
    asset_statuses: list[dict[str, str]],
) -> None:
    if not asset_statuses:
        return

    content_by_asset = _parse_assets_context_sections(assets_context)
    lines.append("## Reference Assets")
    lines.append("")

    for entry in asset_statuses:
        name = entry.get("name", "")
        status = entry.get("status", "")
        message = entry.get("message", "")
        if not name:
            continue

        lines.append(f"### {name}")
        if status == "failed":
            lines.append(f"- {message}")
            lines.append("")
            continue

        content = content_by_asset.get(name, "")
        if content:
            lines.append(content)
        elif message:
            lines.append(f"- {message}")
        lines.append("")


def _append_reference_document_status_section(lines: list[str], asset_statuses: list[dict[str, str]]) -> None:
    if not asset_statuses:
        return

    lines.append("## Reference Document Status")
    lines.append("")
    for entry in asset_statuses:
        message = entry.get("message", "")
        if message:
            lines.append(f"- {message}")
    lines.append("")


def _extract_synth_list(synth_content: str, heading: str) -> list[str]:
    heading_key = heading.strip().lower()
    lines = synth_content.splitlines()
    collecting = False
    collected_lines: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if collecting:
                collected_lines.append(line)
            continue

        canonical_heading = line.lower().lstrip("#").strip().rstrip(":").strip()
        is_heading_line = canonical_heading == heading_key
        is_other_heading = bool(re.match(r"^[A-Z][^\n]*:\s*$", line)) or line.startswith("#")

        if is_heading_line:
            collecting = True
            continue

        if collecting and is_other_heading:
            break

        if collecting:
            collected_lines.append(line)

    if not collected_lines:
        return []

    bullets: list[str] = []
    for line in collected_lines:
        if line.startswith("- "):
            cleaned = _normalize_bullet_text(line[2:])
            if cleaned and not _is_pipeline_stage_label(cleaned):
                bullets.append(cleaned)
        elif re.match(r"^\d+\.\s+", line):
            cleaned = _normalize_bullet_text(re.sub(r"^\d+\.\s+", "", line))
            if cleaned and not _is_pipeline_stage_label(cleaned):
                bullets.append(cleaned)
    return bullets


def _topic_from_legal_risk(text: str) -> str | None:
    lowered = text.lower()
    topics: list[tuple[str, tuple[str, ...]]] = [
        ("Opportunity Summary", ("solicitation", "agency", "contract type", "naics", "set-aside", "response due")),
        ("Evaluation and Win Strategy", ("section m", "evaluation", "factor", "tradeoff", "best value", "lpta")),
        ("Requirements and Deliverables", ("pws", "statement of work", "deliverable", "reporting", "technical")),
        ("Staffing and Transition", ("key personnel", "labor category", "fte", "transition", "mobilization", "clearance")),
        ("Pricing and Price to Win", ("price", "cost", "ceiling", "budget", "ige", "cost realism")),
        ("Teaming and Competitive Position", ("incumbent", "teaming", "joint venture", "mentor protege", "subcontracting")),
    ]

    best_topic: str | None = None
    best_score = 0
    for label, keywords in topics:
        score = sum(lowered.count(keyword) for keyword in keywords)
        if score > best_score:
            best_topic = label
            best_score = score
    if best_score <= 0:
        return None
    return best_topic


def _is_pipeline_stage_label(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return False
    if re.match(r"^stage\b", normalized, flags=re.IGNORECASE):
        return True
    return normalized.lower() in {label.lower() for label in PIPELINE_STAGE_LABELS}


def _clean_heading_candidate(text: str | None) -> str | None:
    if text is None:
        return None

    heading = re.sub(r"\s+", " ", text).strip().rstrip(":")
    if not heading or _is_pipeline_stage_label(heading):
        return None

    # Apply promotion rejection rules before any heading promotion logic.
    if len(heading.split()) > 15:
        return None

    if not _looks_like_known_heading_vocabulary(heading) and _contains_action_verb(heading):
        return None

    numbered_match = re.match(r"^(\d+)\.\s+([A-Z][^\n]{1,200})$", heading)
    if numbered_match:
        return f"{numbered_match.group(1)}. {numbered_match.group(2).strip()}"

    if re.match(r"^\d+\.\d+", heading):
        return None

    for allowed in KNOWN_CONTRACT_SECTION_HEADINGS:
        if heading.lower() == allowed.lower():
            return allowed

    return None


def _filter_pipeline_stage_lines(text: str) -> str:
    if not text.strip():
        return text

    filtered_lines: list[str] = []
    for line in text.splitlines():
        if _is_pipeline_stage_label(line.strip()):
            continue
        filtered_lines.append(line)
    return "\n".join(filtered_lines).strip()


def _find_heading_candidate(text: str) -> str | None:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines:
        if line == "---" or re.match(r"^(title|source|last_run)\s*:", line, flags=re.IGNORECASE):
            continue

        detected_match = re.match(r"^Detected section heading:\s*(.+)$", line, flags=re.IGNORECASE)
        if detected_match:
            heading = _clean_heading_candidate(detected_match.group(1))
            if heading is not None:
                return heading
            continue

        md_match = re.match(r"^#{1,6}\s+(.+)$", line)
        if md_match:
            heading = _clean_heading_candidate(md_match.group(1))
            if heading is not None:
                return heading
            continue

        formal_patterns = [
            r"^(\d+)\.\s+([A-Z][^\n]{2,140})$",
            r"^(Section\s+[A-Za-z0-9.\-]+\s*[:.-]?\s*[^\n]{2,160})$",
            r"^(Article\s+[A-Za-z0-9.\-]+\s*[:.-]?\s*[^\n]{2,160})$",
        ]
        for pattern in formal_patterns:
            match = re.match(pattern, line, flags=re.IGNORECASE)
            if not match:
                continue
            if len(match.groups()) >= 2:
                heading = _clean_heading_candidate(f"{match.group(1)}. {match.group(2).strip()}")
            else:
                heading = _clean_heading_candidate(match.group(1).strip())
            if heading is not None:
                return heading
    return None


def _extract_legal_risk_bullets(legal_risk_content: str) -> list[str]:
    bullets: list[str] = []
    for line in legal_risk_content.splitlines():
        line = line.strip()
        if line.startswith("- "):
            cleaned = _normalize_bullet_text(line[2:])
            if cleaned and not _is_pipeline_stage_label(cleaned):
                bullets.append(cleaned)
    return bullets


def _build_diagnostics_report(report_title: str, chunk_diagnostics: list[dict[str, str]]) -> str:
    lines = [f"# Chunk Diagnostics: {report_title}", ""]
    if not chunk_diagnostics:
        lines.append("No chunk diagnostics were generated.")
        return "\n".join(lines).strip() + "\n"

    for item in chunk_diagnostics:
        lines.append(f"## Chunk {item['chunk_index']}")
        lines.append(f"### Section assignment")
        lines.append(item["section_name"])
        lines.append("")
        lines.append("### extractor")
        lines.append(item["extractor"])
        lines.append("")
        lines.append("### reviewer")
        lines.append(item["reviewer"])
        lines.append("")
        lines.append("### analyst")
        lines.append(item["analyst"])
        lines.append("")
        lines.append("### synthesizer")
        lines.append(item["synthesizer"])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _build_sectioned_analysis_report(
    report_title: str,
    chunk_count: int,
    section_order: list[str],
    section_buckets: dict[str, dict[str, list[str]]],
    assets_context: str,
    asset_statuses: list[dict[str, str]],
) -> str:
    lines = [f"# Analysis Report: {report_title}", ""]
    lines.append("## Document Overview")
    lines.append(f"- Chunks processed: {chunk_count}. Sections detected: {len(section_order)}.")
    lines.append("")

    legal_risk_index_by_key: dict[str, tuple[str, int]] = {}
    deduped_by_section: dict[str, dict[str, list[str]]] = {}

    for section_name in section_order:
        bucket = section_buckets[section_name]
        deduped_legal_risks: list[str] = []
        deduped_takeaways: list[str] = []
        deduped_actions: list[str] = []
        seen_takeaways_section: set[str] = set()
        seen_actions_section: set[str] = set()

        for risk in bucket["legal_risks"]:
            normalized = _normalize_bullet_text(risk)
            key = _canonicalize_legal_risk_text(normalized)
            if not normalized or not key:
                continue
            existing_location = legal_risk_index_by_key.get(key)
            if existing_location is None:
                legal_risk_index_by_key[key] = (section_name, len(deduped_legal_risks))
                deduped_legal_risks.append(normalized)
                continue

            existing_section, existing_index = existing_location
            existing_text = deduped_by_section.get(existing_section, {}).get("legal_risks", [])
            if existing_index >= len(existing_text):
                continue
            if _is_more_complete_legal_risk(normalized, existing_text[existing_index]):
                deduped_by_section[existing_section]["legal_risks"][existing_index] = normalized

        for takeaway in bucket["takeaways"]:
            _append_unique_bullet(deduped_takeaways, seen_takeaways_section, takeaway)

        for action in bucket["actions"]:
            _append_unique_bullet(deduped_actions, seen_actions_section, action)

        deduped_by_section[section_name] = {
            "legal_risks": deduped_legal_risks,
            "takeaways": deduped_takeaways,
            "actions": deduped_actions,
        }

    for section_name in section_order:
        legal_risks = deduped_by_section[section_name]["legal_risks"]
        takeaways = deduped_by_section[section_name]["takeaways"]
        actions = deduped_by_section[section_name]["actions"]

        lines.append(f"## {section_name}")
        lines.append("")
        lines.append("### What Matters for Your Team")
        reader_findings: list[str] = []
        has_clause_digest = False
        for risk in legal_risks:
            if _looks_like_far_clause_dump(risk):
                has_clause_digest = True
                continue
            if _is_low_signal_finding(risk):
                continue
            summarized = _summarize_finding_for_reader(risk)
            if not summarized or _is_reader_friendly_duplicate(reader_findings, summarized):
                continue
            reader_findings.append(summarized)
            if len(reader_findings) >= 8:
                break

        if has_clause_digest:
            reader_findings.append(
                "A large block of standard FAR clauses is present; prioritize review of deviations and requirement-specific clauses over baseline boilerplate."
            )

        if reader_findings:
            for finding in reader_findings:
                lines.append(f"- {finding}")
        else:
            lines.append("- No high-confidence BD decision signals were detected in this section.")

        lines.append("")
        section_takeaways: list[str] = []
        for takeaway in takeaways:
            normalized = _rewrite_pipeline_jargon(takeaway)
            if not normalized:
                continue
            if any(_are_near_duplicate_bullets(existing, normalized) for existing in section_takeaways):
                continue
            if _is_reference_assets_boilerplate(normalized):
                continue
            section_takeaways.append(normalized)
        if section_takeaways:
            lines.append("### Strategic Takeaways")
            for takeaway in section_takeaways:
                lines.append(f"- {takeaway}")

        lines.append("")
        section_actions: list[str] = []
        for action in actions:
            normalized = _rewrite_pipeline_jargon(action)
            if not normalized:
                continue
            if any(_are_near_duplicate_bullets(existing, normalized) for existing in section_actions):
                continue
            section_actions.append(normalized)
        if section_actions:
            lines.append("### Recommended Next Actions")
            for action in section_actions:
                lines.append(f"- {action}")

        lines.append("")

    _append_reference_assets_section(lines, assets_context, asset_statuses)
    _append_reference_document_status_section(lines, asset_statuses)

    return "\n".join(lines).strip() + "\n"


def _build_final_markdown(report_title: str, source_label: str, synthesized_sections: list[str]) -> str:
    chunks = [section.strip() for section in synthesized_sections if section.strip()]
    body_lines = [f"# Final Synthesized Output: {report_title}", ""]
    if not chunks:
        body_lines.append("No synthesized output was generated.")
    else:
        for i, section in enumerate(chunks, start=1):
            body_lines.append(f"## Chunk {i}")
            body_lines.append(section)
            body_lines.append("")

    frontmatter = [
        "---",
        f'title: "{report_title.replace("\"", "\\\"")}"',
        f'source: "{source_label.replace("\"", "\\\"")}"',
        f'last_run: "{_utc_now_iso()}"',
        "---",
        "",
    ]
    return "\n".join(frontmatter + body_lines).strip() + "\n"


def _final_output_path(source_name: str) -> Path:
    stem = Path(source_name).stem
    final_stem = stem if stem.endswith("-final") else f"{stem}-final"
    return FINAL_OUTPUT_DIR / f"{final_stem}.md"


def _extract_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?;])\s+", normalized) if s.strip()]


def _strip_reference_sections(report: str) -> str:
    marker_positions = [
        idx
        for idx in (
            report.find("\n## Reference Assets"),
            report.find("\n## Reference Document Status"),
        )
        if idx != -1
    ]
    if not marker_positions:
        return report
    return report[: min(marker_positions)].strip()


def _contains_term(text: str, term: str) -> bool:
    pattern = r"\b" + re.escape(term.lower()) + r"\b"
    return re.search(pattern, text.lower()) is not None


def _contains_any_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(_contains_term(text, term) for term in terms)


def _clean_party_candidate(candidate: str) -> str:
    cleaned = re.sub(r"\([^)]*\)", "", candidate)
    cleaned = cleaned.strip(" ,;:-\"'")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _is_confident_party_name(candidate: str) -> bool:
    cleaned = _clean_party_candidate(candidate)
    if not cleaned:
        return False
    if len(cleaned.split()) > 10:
        return False
    if len(cleaned) > 90:
        return False
    lowered = cleaned.lower()
    if any(token in lowered for token in ("proprietary information", "terms and conditions", "agreement shall", "representatives")):
        return False
    return bool(re.search(r"[A-Za-z]", cleaned))


def _extract_parties_from_text(full_text: str) -> str:
    between_patterns = (
        r"\bbetween\s+(.{2,120}?)\s+and\s+(.{2,120}?)(?:,|\.|\sas\sof\b|\sdated\b|\sfor\sthe\spurpose\b)",
        r"\bby\s+and\s+between\s+(.{2,120}?)\s+and\s+(.{2,120}?)(?:,|\.|\sas\sof\b|\sdated\b)",
    )
    for pattern in between_patterns:
        match = re.search(pattern, full_text, flags=re.IGNORECASE)
        if not match:
            continue
        first = _clean_party_candidate(match.group(1))
        second = _clean_party_candidate(match.group(2))
        if _is_confident_party_name(first) and _is_confident_party_name(second):
            return f"{first} and {second}"

    signature_match = re.search(
        r"(?:IN WITNESS WHEREOF|By:)\s+(.{2,80}?)\s+(?:By:|Name:)\s+(.{2,80}?)(?:\s+Title:\s+.{2,80})?",
        full_text,
        flags=re.IGNORECASE,
    )
    if signature_match:
        entity = _clean_party_candidate(signature_match.group(1))
        signatory = _clean_party_candidate(signature_match.group(2))
        if _is_confident_party_name(entity) and _is_confident_party_name(signatory):
            return f"{entity} (signatory: {signatory})"

    return "See contract preamble"


def _build_contract_description(contract_type: str, analysis_report: str) -> list[str]:
    text = _strip_reference_sections(analysis_report)
    lowered = text.lower()

    if contract_type != "Non-disclosure agreement":
        return [
            "This agreement defines the parties' core rights, obligations, and enforcement mechanics for the stated commercial relationship.",
            "Key sections should be reviewed against internal standards before execution.",
        ]

    if _contains_any_term(lowered, ("mutual non-disclosure", "mutual nondisclosure", "each party shall")):
        nda_type = "This appears to be a mutual NDA with obligations on both sides."
    elif _contains_any_term(lowered, ("disclosing party", "receiving party")):
        nda_type = "This appears to be a one-way NDA with primary restrictions on the receiving party."
    else:
        nda_type = "This NDA's directionality is not explicit in the extracted text."

    purpose = "Purpose of disclosure is not clearly stated in extracted text."
    purpose_match = re.search(
        r"(?:for the purpose of|to evaluate|in connection with)\s+(.{8,180}?)(?:\.|;)",
        text,
        flags=re.IGNORECASE,
    )
    if purpose_match:
        purpose_text = _normalize_bullet_text(purpose_match.group(1))
        purpose = f"Stated purpose: {purpose_text}."

    term = "Confidentiality period is not clearly stated."
    term_match = re.search(
        r"(?:for a period of\s+[^.;]{3,80}|terminate on the\s+[^.;]{3,80}|survive[^.;]{0,80})",
        text,
        flags=re.IGNORECASE,
    )
    if term_match:
        term = f"Confidentiality duration signal: {_normalize_bullet_text(term_match.group(0))}."

    notable_items: list[str] = []
    if _contains_any_term(lowered, ("standstill",)):
        notable_items.append("standstill")
    if _contains_any_term(lowered, ("non-solicitation", "no solicitation", "no-solicitation")):
        notable_items.append("non-solicitation")
    if _contains_any_term(lowered, ("injunctive", "equitable relief", "immediate injunction")):
        notable_items.append("injunctive relief")
    notable = "Notable provisions: none clearly distinguished from a baseline template."
    if notable_items:
        notable = "Notable provisions: " + ", ".join(notable_items) + "."

    return [nda_type, purpose, term, notable]


def _score_issue_line(line: str) -> int:
    lowered = line.lower()
    score = 0
    for terms, points in BD_ISSUE_BONUS_TERMS:
        if any(term in lowered for term in terms):
            score += points

    # Promote concrete gate language above generic contract boilerplate.
    if any(term in lowered for term in ("must", "required", "not receive", "rejected", "ineligible", "disqual")):
        score += 2

    if any(all(token in lowered for token in penalty_group) for penalty_group in BD_ISSUE_PENALTY_TERMS):
        score -= 2

    if len(lowered) < 40:
        score -= 1

    score = max(0, score)
    return score


def _issue_risk_label(score: int) -> str:
    if score >= 9:
        return "HIGH"
    if score >= 5:
        return "MEDIUM"
    return "LOW"


def _collect_issue_lines(issues_report: str) -> list[str]:
    lines = [ln.strip() for ln in issues_report.splitlines()]
    collected: list[str] = []
    for line in lines:
        if line.startswith("- "):
            collected.append(line[2:].strip())
        elif line and not line.startswith("#") and line.lower() not in (
            "potential obligations/risks:",
            "potential bd issues:",
            "no explicit bd gate signals were detected in this chunk.",
        ):
            collected.append(line)
    deduped: list[str] = []
    seen: set[str] = set()
    for line in collected:
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(line)
    return deduped


def _extract_company_profile_section(markdown_text: str) -> str:
    if not markdown_text.strip():
        return ""

    lines = markdown_text.splitlines()
    start = -1
    for idx, raw in enumerate(lines):
        line = raw.strip().lower()
        if line.startswith("## ") and "submitted company profile" in line:
            start = idx + 1
            break

    if start == -1:
        return ""

    collected: list[str] = []
    for raw in lines[start:]:
        stripped = raw.strip()
        if stripped.startswith("## "):
            break
        collected.append(raw)
    return "\n".join(collected).strip()


def _read_submission_metadata_for_source(source_name: str) -> dict[str, str]:
    normalized = source_name.replace("\\", "/")
    match = re.search(r"sub_\d+", normalized)
    if not match:
        return {}

    metadata_path = Path("rfp-pdfs") / match.group(0) / "submission-metadata.json"
    if not metadata_path.exists():
        return {}

    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    if not isinstance(payload, dict):
        return {}

    return {str(k): str(v) for k, v in payload.items() if isinstance(v, (str, int, float, bool))}


def _estimate_key_personnel_count(text: str) -> int:
    normalized = _normalize_bullet_text(text)
    if not normalized:
        return 0

    lowered = normalized.lower()
    numeric_roles = re.findall(
        r"\b(\d{1,2})\s*(?:x\s*)?(?:pm|project\s+manager|ai\s+lead|lead|engineer|developer|architect|analyst|specialist|manager)\b",
        lowered,
    )
    if numeric_roles:
        return sum(int(value) for value in numeric_roles)

    # Fallback list split when explicit counts are not provided.
    parts = [
        item.strip()
        for item in re.split(r",|;|\band\b|\n", normalized, flags=re.IGNORECASE)
        if item.strip()
    ]
    if len(parts) > 1:
        return len(parts)
    return 1 if normalized else 0


def _derive_company_capacity_signals(markdown_text: str, source_name: str) -> dict[str, str | int]:
    profile_section = _extract_company_profile_section(markdown_text)
    metadata = _read_submission_metadata_for_source(source_name)

    team_size = ""
    key_personnel = ""

    team_size_patterns = (
        r"team\s*size\s*[:\-]\s*([^\n]+)",
        r"employee\s*count\s*[:\-]\s*([^\n]+)",
    )
    for pattern in team_size_patterns:
        match = re.search(pattern, profile_section, flags=re.IGNORECASE)
        if match:
            team_size = _normalize_bullet_text(match.group(1))
            break

    key_personnel_patterns = (
        r"key\s*personnel\s*[:\-]\s*([^\n]+)",
        r"core\s*team\s*[:\-]\s*([^\n]+)",
    )
    for pattern in key_personnel_patterns:
        match = re.search(pattern, profile_section, flags=re.IGNORECASE)
        if match:
            key_personnel = _normalize_bullet_text(match.group(1))
            break

    team_size = team_size or metadata.get("teamSize", "") or metadata.get("team_size", "")
    key_personnel = key_personnel or metadata.get("keyPersonnel", "") or metadata.get("key_personnel", "")

    personnel_count = _estimate_key_personnel_count(key_personnel) if key_personnel else 0

    return {
        "team_size": team_size,
        "key_personnel": key_personnel,
        "personnel_count": personnel_count,
    }


def _missing_critical_capture_roles(key_personnel: str) -> list[str]:
    text = _normalize_bullet_text(key_personnel).lower()
    if not text:
        return ["capture leadership", "pricing/finance lead", "technical delivery lead"]

    role_patterns: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "capture leadership",
            (
                "capture manager",
                "capture lead",
                "program manager",
                "project manager",
                "pm",
            ),
        ),
        (
            "pricing/finance lead",
            (
                "pricing lead",
                "pricing manager",
                "cost estimator",
                "finance lead",
                "contracts manager",
                "proposal manager",
            ),
        ),
        (
            "technical delivery lead",
            (
                "technical lead",
                "chief engineer",
                "solution architect",
                "engineering lead",
                "operations lead",
                "ai lead",
            ),
        ),
    )

    missing: list[str] = []
    for label, tokens in role_patterns:
        if not any(token in text for token in tokens):
            missing.append(label)
    return missing


def _team_capacity_cap_from_profile(signals: dict[str, str | int]) -> tuple[int | None, str | None]:
    team_size = str(signals.get("team_size", "")).lower()
    personnel_count = int(signals.get("personnel_count", 0) or 0)
    key_personnel = str(signals.get("key_personnel", ""))
    missing_roles = _missing_critical_capture_roles(key_personnel)

    if len(missing_roles) >= 2:
        return 45, (
            "intake profile does not show enough functional coverage; missing "
            + ", ".join(missing_roles)
            + ", which raises proposal and execution risk"
        )

    if personnel_count > 0 and personnel_count <= 2:
        return 35, "intake profile lists a very lean key team (2 people or fewer), which is unlikely to sustain full proposal and delivery load"
    if personnel_count in (3, 4):
        return 50, "intake profile lists a small key team (3-4 people), which raises execution bandwidth risk"

    if re.search(r"\b(1\s*[-to]{0,3}\s*5|2\s*[-to]{0,3}\s*10|small)\b", team_size):
        return 50, "intake team-size band indicates a small organization relative to likely staffing demands"
    if re.search(r"\b(11\s*[-to]{0,3}\s*50|51\s*[-to]{0,3}\s*100)\b", team_size):
        return 65, "intake team-size band indicates moderate capacity with potential surge limits"

    return None, None


def _build_scorecard(
    analysis_report: str,
    issues_report: str,
    company_capacity_signals: dict[str, str | int] | None = None,
) -> tuple[str, str, list[str], list[dict[str, str]]]:
    core_analysis = _strip_reference_sections(analysis_report)
    full_text = f"{core_analysis}\n{issues_report}"
    sentences = _extract_sentences(full_text)
    score_rows: list[dict[str, str]] = []
    capacity_signals = company_capacity_signals or {}

    for dimension in BD_SCORE_DIMENSIONS:
        dimension_name = str(dimension["name"])
        weight = int(dimension["weight"])
        positive_terms = tuple(str(term) for term in dimension["positive_terms"])
        negative_terms = tuple(str(term) for term in dimension["negative_terms"])

        positive_hits = sum(1 for sentence in sentences if _contains_any_term(sentence, positive_terms))
        negative_hits = sum(1 for sentence in sentences if _contains_any_term(sentence, negative_terms))
        evidence_hits = positive_hits + negative_hits

        base_score = 45
        score = base_score + min(positive_hits * 8, 40) - min(negative_hits * 10, 35)
        if evidence_hits == 0:
            score = 40
        score = max(0, min(100, score))

        if evidence_hits >= 6:
            confidence = "HIGH"
        elif evidence_hits >= 2:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        weighted_score = round(score * (weight / 100), 1)
        rationale = (
            f"Signals found: {positive_hits} positive and {negative_hits} gap/risk indicators "
            f"for {dimension_name.lower()}."
        )

        if dimension_name == "Team Capacity":
            cap, reason = _team_capacity_cap_from_profile(capacity_signals)
            if cap is not None and score > cap:
                score = cap
                weighted_score = round(score * (weight / 100), 1)
                rationale += f" Adjusted using intake profile: {reason}."
                confidence = "HIGH"
            elif capacity_signals.get("team_size") or capacity_signals.get("key_personnel"):
                rationale += " Intake profile reviewed: no automatic capacity cap triggered."

        score_rows.append(
            {
                "dimension": dimension_name,
                "score": str(score),
                "weight": str(weight),
                "weighted_score": f"{weighted_score:.1f}",
                "confidence": confidence,
                "rationale": rationale,
            }
        )

    overall_score = round(sum(float(row["weighted_score"]) for row in score_rows), 1)
    recommendation = "Pass"
    for threshold, label in RECOMMENDATION_BANDS:
        if overall_score >= threshold:
            recommendation = label
            break

    scored_issues = [
        {
            "text": line,
            "score": _score_issue_line(line),
        }
        for line in _collect_issue_lines(issues_report)
    ]
    scored_issues.sort(key=lambda item: (item["score"], item["text"].lower()), reverse=True)
    top_issues = [
        {
            "risk": _issue_risk_label(item["score"]),
            "text": item["text"],
        }
        for item in scored_issues[:3]
    ]

    lines = [f"Overall BD fit score: {overall_score:.1f}/100 - {recommendation}", ""]
    lines.append("| Dimension | Score | Weight | Weighted Score | Confidence | Rationale |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for row in score_rows:
        rationale = row["rationale"].replace("|", "/")
        lines.append(
            f"| {row['dimension']} | {row['score']}/100 | {row['weight']}% | {row['weighted_score']} | {row['confidence']} | {rationale} |"
        )
    lines.append("")
    lines.append("Top 3 highest-priority BD issues:")
    if top_issues:
        for i, issue in enumerate(top_issues, start=1):
            lines.append(f"{i}. [{issue['risk']}] {issue['text']}")
    else:
        lines.append("1. [LOW] No explicit BD issue lines were detected in the issues summary.")

    scorecard = "\n".join(lines).strip() + "\n"
    return scorecard, recommendation, [], score_rows


def _extract_contract_metadata(report_title: str, analysis_report: str) -> tuple[str, str, str, str]:
    contract_name = Path(report_title).stem
    core_text = _strip_reference_sections(analysis_report)
    full_text = re.sub(r"\s+", " ", core_text)
    lowered = full_text.lower()

    contract_type = "Commercial agreement"
    if any(term in lowered for term in ("non-disclosure", "nondisclosure", "confidentiality")):
        contract_type = "Non-disclosure agreement"
    elif "service" in lowered:
        contract_type = "Services agreement"
    elif "purchase" in lowered:
        contract_type = "Purchase agreement"

    parties = _extract_parties_from_text(full_text)

    effective_date = "Not stated"
    date_match = re.search(
        r"(?:effective\s+date|dated|effective\s+as\s+of)[:\s]+([A-Za-z]+\s+\d{1,2},\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})",
        full_text,
        flags=re.IGNORECASE,
    )
    if date_match:
        effective_date = date_match.group(1).strip()

    return contract_name, contract_type, parties, effective_date


def _not_found_categories_from_scorecard(scorecard: str) -> list[str]:
    categories: list[str] = []
    for line in scorecard.splitlines():
        if not line.startswith("|"):
            continue
        if "| NOT FOUND |" not in line:
            continue
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) >= 3 and cells[1] and cells[1] != "Category":
            categories.append(cells[1])
    return categories


def _build_executive_summary(
    report_title: str,
    analysis_report: str,
    scorecard: str,
    overall_rating: str,
    score_rows: list[dict[str, str]],
) -> str:
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    overall_score = round(sum(float(row.get("weighted_score", "0")) for row in score_rows), 1)
    sorted_rows = sorted(
        score_rows,
        key=lambda row: int(row.get("score", "0")),
        reverse=True,
    )
    strongest = sorted_rows[0] if sorted_rows else None
    weakest = sorted_rows[-1] if sorted_rows else None

    top_bd_risks: list[str] = []
    for line in scorecard.splitlines():
        if re.match(r"^\d+\.\s+\[(HIGH|MEDIUM|LOW)\]\s+", line.strip()):
            top_bd_risks.append(re.sub(r"^\d+\.\s+", "", line.strip()))

    if not top_bd_risks:
        top_bd_risks = ["[LOW] No high-impact BD risks were detected in the available issue signals."]

    actions: list[str] = [
        "Confirm bid/no-bid posture with leadership using the weighted fit score and top BD risks.",
        "Align proposal strategy to Section M evaluation emphasis and resource the highest-risk volume first.",
    ]
    if weakest is not None:
        actions.append(
            f"Close the largest current gap in {weakest.get('dimension', 'team readiness')} before color-team kickoff."
        )
    if any("incumbent" in risk.lower() for risk in top_bd_risks):
        actions.append("Build explicit discriminators against incumbent advantage and validate transition credibility.")
    if any("budget" in risk.lower() or "cost" in risk.lower() for risk in top_bd_risks):
        actions.append("Run a price-to-win sensitivity pass to ensure your labor mix can survive cost realism scrutiny.")

    summary_lines = [
        "## Bid or No-Bid Snapshot",
        f"- Opportunity: {Path(report_title).stem}",
        f"- Analysis run date: {run_date}",
        f"- Recommendation: {overall_rating}",
        f"- Overall BD fit score: {overall_score:.1f}/100",
        "",
        "## Strongest Alignment",
    ]

    if strongest is not None:
        summary_lines.append(
            f"- {strongest.get('dimension', 'N/A')}: {strongest.get('score', '0')}/100. {strongest.get('rationale', '')}"
        )
    else:
        summary_lines.append("- No dimension-level scoring data was generated.")

    summary_lines.extend(["", "## Critical Gap"])
    if weakest is not None:
        summary_lines.append(
            f"- {weakest.get('dimension', 'N/A')}: {weakest.get('score', '0')}/100. {weakest.get('rationale', '')}"
        )
    else:
        summary_lines.append("- No critical gap was detected from the available evidence.")

    summary_lines.extend(["", "## Top BD Risks"])
    summary_lines.extend(f"- {item[:160]}" for item in top_bd_risks[:5])

    summary_lines.extend(["", "## Immediate Capture Actions"])
    summary_lines.extend(f"- {item[:160]}" for item in actions[:5])

    return "\n".join(summary_lines).strip() + "\n"


def _analyze_markdown(
    markdown: str,
    report_title: str,
    config: PipelineConfig,
    assets_context: str = "",
    asset_statuses: list[dict[str, str]] | None = None,
    source_name: str | None = None,
) -> dict:
    chunks = chunk_markdown(markdown, config.chunk_size_chars, config.overlap_chars)
    agents = [ExtractorAgent(), ReviewerAgent(), AnalystAgent(), LegalRiskAgent(), SynthesizerAgent()]

    issues_lines = [f"# BD Issues Summary: {report_title}", ""]
    statuses = asset_statuses or []
    section_buckets: dict[str, dict[str, list[str]]] = {}
    section_order: list[str] = []
    chunk_diagnostics: list[dict[str, str]] = []
    synthesized_sections: list[str] = []
    current_section: str | None = None

    def ensure_section(name: str) -> dict[str, list[str]]:
        if name not in section_buckets:
            section_buckets[name] = {
                "legal_risks": [],
                "takeaways": [],
                "actions": [],
            }
            section_order.append(name)
        return section_buckets[name]

    for i, chunk in enumerate(chunks, start=1):
        per_agent: dict[str, str] = {}
        for agent in agents:
            result = agent.run(chunk, assets_context=assets_context)
            per_agent[result.agent_name] = result.content
            if result.agent_name == "legal-risk":
                issues_lines.append(f"## Chunk {i}")
                issues_lines.append(result.content)
                issues_lines.append("")

        extractor_output = _filter_pipeline_stage_lines(per_agent.get("extractor", ""))
        heading_candidate = _find_heading_candidate(extractor_output) or _find_heading_candidate(chunk)
        if heading_candidate:
            current_section = heading_candidate
            section_name = heading_candidate
        elif current_section is not None:
            section_name = current_section
        elif i == 1:
            section_name = DEFAULT_FIRST_SECTION_HEADING
            current_section = section_name
        else:
            topic_source = "\n".join(
                [
                    chunk,
                    per_agent.get("legal-risk", ""),
                    per_agent.get("synthesizer", ""),
                ]
            )
            fallback_topic = _topic_from_legal_risk(topic_source)
            if fallback_topic and fallback_topic in section_buckets:
                section_name = fallback_topic
            elif section_order:
                section_name = section_order[-1]
            else:
                section_name = DEFAULT_FIRST_SECTION_HEADING
                current_section = section_name

        bucket = ensure_section(section_name)

        legal_risk_bullets = _extract_legal_risk_bullets(per_agent.get("legal-risk", ""))
        for bullet in legal_risk_bullets:
            if bullet not in bucket["legal_risks"]:
                bucket["legal_risks"].append(bullet)

        takeaways = _extract_synth_list(per_agent.get("synthesizer", ""), "Strategic takeaways")
        actions = _extract_synth_list(per_agent.get("synthesizer", ""), "Recommended next actions")
        bucket["takeaways"].extend(takeaways)
        bucket["actions"].extend(actions)
        if per_agent.get("synthesizer", "").strip():
            synthesized_sections.append(per_agent["synthesizer"])

        chunk_diagnostics.append(
            {
                "chunk_index": str(i),
                "section_name": section_name,
                "extractor": extractor_output,
                "reviewer": per_agent.get("reviewer", ""),
                "analyst": per_agent.get("analyst", ""),
                "synthesizer": per_agent.get("synthesizer", ""),
            }
        )

    report = _build_sectioned_analysis_report(
        report_title=report_title,
        chunk_count=len(chunks),
        section_order=section_order,
        section_buckets=section_buckets,
        assets_context=assets_context,
        asset_statuses=statuses,
    )
    issues_report = "\n".join(issues_lines).strip() + "\n"
    source_hint = source_name or report_title
    capacity_signals = _derive_company_capacity_signals(markdown, source_hint)
    scorecard, overall_rating, _not_found_categories, score_rows = _build_scorecard(
        report,
        issues_report,
        company_capacity_signals=capacity_signals,
    )
    executive_summary = _build_executive_summary(
        report_title,
        report,
        scorecard,
        overall_rating,
        score_rows,
    )
    return {
        "report": report,
        "issues_report": issues_report,
        "scorecard": scorecard,
        "executive_summary": executive_summary,
        "final_markdown": _build_final_markdown(report_title, report_title, synthesized_sections),
        "chunk_diagnostics_report": _build_diagnostics_report(report_title, chunk_diagnostics),
        "section_count": len(section_order),
        "chunk_count": len(chunks),
    }


def run_pipeline(pdf_path: Path, config: PipelineConfig | None = None) -> dict:
    """Run PDF->Markdown conversion and multi-agent analysis."""
    cfg = config or PipelineConfig()
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    markdown = pdf_to_markdown(pdf_path)
    md_path = cfg.output_dir / f"{pdf_path.stem}.md"
    md_path.write_text(markdown, encoding="utf-8")

    analysis = _analyze_markdown(markdown, pdf_path.name, cfg, source_name=pdf_path.as_posix())
    report_path = cfg.output_dir / f"{pdf_path.stem}.analysis.md"
    issues_path = cfg.output_dir / f"{pdf_path.stem}.issues.md"
    scorecard_path = cfg.output_dir / f"{pdf_path.stem}.scorecard.md"
    executive_summary_path = cfg.output_dir / f"{pdf_path.stem}.executive-summary.md"
    final_path = _final_output_path(pdf_path.name)
    audit_run_dir = AUDIT_ROOT_DIR / _make_audit_run_id()
    audit_run_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_name = f"{Path(pdf_path.name).stem}-chunk-diagnostics.md"
    diagnostics_path = audit_run_dir / diagnostics_name
    final_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(analysis["report"], encoding="utf-8")
    issues_path.write_text(analysis["issues_report"], encoding="utf-8")
    scorecard_path.write_text(analysis["scorecard"], encoding="utf-8")
    executive_summary_path.write_text(analysis["executive_summary"], encoding="utf-8")
    final_path.write_text(analysis["final_markdown"], encoding="utf-8")
    diagnostics_path.write_text(analysis["chunk_diagnostics_report"], encoding="utf-8")

    return {
        "markdown_path": md_path,
        "report_path": report_path,
        "issues_path": issues_path,
        "scorecard_path": scorecard_path,
        "executive_summary_path": executive_summary_path,
        "final_path": final_path,
        "chunk_diagnostics_path": diagnostics_path,
        "section_count": analysis["section_count"],
        "chunk_count": analysis["chunk_count"],
    }


def run_markdown_analysis(
    markdown_path: Path,
    config: PipelineConfig | None = None,
    assets_dir: Path | None = None,
) -> dict:
    """Run multi-agent analysis for an existing markdown file."""
    cfg = config or PipelineConfig()
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    markdown = markdown_path.read_text(encoding="utf-8")
    assets_context = ""
    asset_statuses: list[dict[str, str]] = []
    if assets_dir is not None:
        assets_context, asset_statuses = build_assets_context_with_status(
            assets_dir,
            max_chars_per_file=cfg.max_asset_chars_per_file,
            pdf_ocr_fallback=cfg.asset_pdf_ocr_fallback,
            pdf_ocr_max_pages=cfg.asset_pdf_ocr_max_pages,
            pdf_min_text_chars=cfg.asset_pdf_min_text_chars,
            pdf_max_single_char_token_ratio=cfg.asset_pdf_max_single_char_token_ratio,
        )

    analysis = _analyze_markdown(
        markdown,
        markdown_path.name,
        cfg,
        assets_context=assets_context,
        asset_statuses=asset_statuses,
        source_name=markdown_path.as_posix(),
    )
    report_path = cfg.output_dir / f"{markdown_path.stem}.analysis.md"
    issues_path = cfg.output_dir / f"{markdown_path.stem}.issues.md"
    scorecard_path = cfg.output_dir / f"{markdown_path.stem}.scorecard.md"
    executive_summary_path = cfg.output_dir / f"{markdown_path.stem}.executive-summary.md"
    final_path = _final_output_path(markdown_path.name)
    audit_run_dir = AUDIT_ROOT_DIR / _make_audit_run_id()
    audit_run_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_name = f"{markdown_path.stem}-chunk-diagnostics.md"
    diagnostics_path = audit_run_dir / diagnostics_name
    final_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(analysis["report"], encoding="utf-8")
    issues_path.write_text(analysis["issues_report"], encoding="utf-8")
    scorecard_path.write_text(analysis["scorecard"], encoding="utf-8")
    executive_summary_path.write_text(analysis["executive_summary"], encoding="utf-8")
    final_path.write_text(analysis["final_markdown"], encoding="utf-8")
    diagnostics_path.write_text(analysis["chunk_diagnostics_report"], encoding="utf-8")

    return {
        "report_path": report_path,
        "issues_path": issues_path,
        "scorecard_path": scorecard_path,
        "executive_summary_path": executive_summary_path,
        "final_path": final_path,
        "chunk_diagnostics_path": diagnostics_path,
        "section_count": analysis["section_count"],
        "chunk_count": analysis["chunk_count"],
        "assets_context_included": bool(assets_context.strip()),
        "asset_warnings": [entry["warning"] for entry in asset_statuses if "warning" in entry],
        "asset_statuses": asset_statuses,
    }
