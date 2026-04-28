from dataclasses import dataclass
import re


@dataclass
class AgentResult:
    agent_name: str
    content: str


class BaseAgent:
    name = "base"

    def run(self, markdown_chunk: str, assets_context: str = "") -> AgentResult:
        raise NotImplementedError


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.lower()))


def _summary_preview(text: str, max_chars: int = 500) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return "No summary available"
    if len(compact) <= max_chars:
        return compact

    window = compact[:max_chars]
    cut_points = [window.rfind(sep) for sep in (". ", "? ", "! ", "; ")]
    cut = max(cut_points)
    if cut >= 80:
        return window[: cut + 1].strip()

    word_cut = window.rfind(" ")
    if word_cut >= 80:
        return window[:word_cut].strip() + "..."
    return window.strip() + "..."


def _find_clause_signals(text: str) -> dict[str, bool]:
    lowered = text.lower()
    return {
        "set_aside_signal": any(term in lowered for term in ("set-aside", "small business", "8(a)", "hubzone", "sdvosb", "wosb")),
        "naics_signal": "naics" in lowered,
        "vehicle_signal": any(term in lowered for term in ("contract vehicle", "idiq", "bpa", "schedule", "gwac")),
        "evaluation_signal": any(term in lowered for term in ("evaluation", "factor", "section m", "tradeoff", "lpta", "best value")),
        "past_performance_signal": any(term in lowered for term in ("past performance", "cpars", "references", "recency", "relevancy")),
        "staffing_signal": any(term in lowered for term in ("key personnel", "resume", "staffing", "labor category", "fte", "hours")),
        "transition_signal": any(term in lowered for term in ("transition", "mobilization", "phase-in", "days after award", "start-up")),
        "pricing_signal": any(term in lowered for term in ("price", "cost", "ige", "ceiling", "nte", "cost realism", "wage determination")),
        "incumbent_signal": "incumbent" in lowered,
    }


def _detect_section_heading(text: str) -> str | None:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines:
        md_match = re.match(r"^#{1,6}\s+(.+)$", line)
        if md_match:
            return md_match.group(1).strip()

        numbered_match = re.match(r"^(\d+(?:\.\d+)*)\s*[.)-]?\s+([A-Z][^\n]{2,140})$", line)
        if numbered_match:
            return f"{numbered_match.group(1)} {numbered_match.group(2).strip()}"

        section_match = re.match(r"^(Section\s+[A-Za-z0-9.\-]+\s*[:.-]?\s*[^\n]{2,160})$", line, flags=re.IGNORECASE)
        if section_match:
            return section_match.group(1).strip()

        article_match = re.match(r"^(Article\s+[A-Za-z0-9.\-]+\s*[:.-]?\s*[^\n]{2,160})$", line, flags=re.IGNORECASE)
        if article_match:
            return article_match.group(1).strip()

    return None


def _strategic_takeaways(signals: dict[str, bool], assets_context: str) -> list[str]:
    takeaways: list[str] = []

    if signals["set_aside_signal"] and signals["naics_signal"]:
        takeaways.append("Set-aside and NAICS signals are present, so eligibility should be confirmed before committing bid resources.")
    elif signals["set_aside_signal"]:
        takeaways.append("Set-aside language appears in scope, which can create eligibility gates that drive bid or no-bid outcomes.")

    if signals["evaluation_signal"]:
        takeaways.append("Evaluation-factor language appears in the chunk, enabling early proposal emphasis decisions aligned to likely scoring priorities.")

    if signals["past_performance_signal"]:
        takeaways.append("Past performance cues suggest recency and relevancy evidence may be a discriminator in evaluator confidence.")

    if signals["staffing_signal"] or signals["transition_signal"]:
        takeaways.append("Staffing and transition requirements indicate execution feasibility risk that should be quantified before final pursuit approval.")

    if signals["pricing_signal"]:
        takeaways.append("Pricing and cost-realism signals indicate a need to pressure-test labor mix and wrap assumptions against likely evaluator scrutiny.")

    if signals["incumbent_signal"]:
        takeaways.append("Incumbent references may indicate structural advantage, so your response strategy should emphasize material differentiation and transition confidence.")

    if assets_context.strip():
        takeaways.append("Reference assets are available, supporting faster alignment to your internal capture standards and reusable proof points.")

    if not takeaways:
        takeaways.append("This chunk is decision-neutral in isolation; rely on cross-chunk synthesis before finalizing bid posture.")

    return takeaways[:4]


def _strategic_next_steps(signals: dict[str, bool], has_assets: bool) -> list[str]:
    actions = [
        "Classify this chunk as pursue, conditional pursue, or pass based on bid-impact evidence.",
    ]

    if signals["set_aside_signal"] or signals["naics_signal"]:
        actions.append("Validate eligibility gates and identify any disqualifiers tied to NAICS, size standard, or set-aside status.")

    if signals["evaluation_signal"]:
        actions.append("Map proposal emphasis to stated evaluation factors and identify the highest-risk volume for red-team priority.")

    if signals["pricing_signal"]:
        actions.append("Run a preliminary price-to-win check using labor assumptions, wage requirements, and any stated budget ceiling.")

    if signals["staffing_signal"] or signals["transition_signal"]:
        actions.append("Confirm staffing and mobilization assumptions are achievable within the stated period of performance and transition window.")

    if has_assets:
        actions.append("Map findings to reference assets and reuse validated win-theme evidence in your capture brief.")

    return actions[:4]


class ExtractorAgent(BaseAgent):
    name = "extractor"

    def run(self, markdown_chunk: str, assets_context: str = "") -> AgentResult:
        lines = [ln.strip() for ln in markdown_chunk.splitlines() if ln.strip()]
        key_lines = lines[:5]
        content = "\n".join(key_lines) if key_lines else "No content"
        heading = _detect_section_heading(markdown_chunk)

        if heading:
            content += f"\n\nDetected section heading: {heading}"

        if assets_context.strip() and key_lines:
            overlap = sorted(_tokenize(" ".join(key_lines)) & _tokenize(assets_context))
            if overlap:
                content += "\n\nReference overlap terms: " + ", ".join(overlap[:12])
            else:
                content += "\n\nReference overlap terms: none detected"

        return AgentResult(self.name, content)


class ReviewerAgent(BaseAgent):
    name = "reviewer"

    def run(self, markdown_chunk: str, assets_context: str = "") -> AgentResult:
        checks = []
        if "TODO" in markdown_chunk:
            checks.append("Found TODO markers needing resolution.")
        if len(markdown_chunk) < 200:
            checks.append("Chunk is short; context may be incomplete.")
        if assets_context.strip():
            overlap_count = len(_tokenize(markdown_chunk) & _tokenize(assets_context))
            checks.append(f"Reference alignment terms detected: {overlap_count}.")
        if not checks:
            checks.append("No obvious structural issues detected.")
        return AgentResult(self.name, " ".join(checks))


class AnalystAgent(BaseAgent):
    name = "analyst"

    def run(self, markdown_chunk: str, assets_context: str = "") -> AgentResult:
        words = [w for w in markdown_chunk.replace("\n", " ").split(" ") if w]
        unique = len(set(w.lower() for w in words))
        if assets_context.strip():
            shared = len(_tokenize(markdown_chunk) & _tokenize(assets_context))
            ref_terms = len(_tokenize(assets_context))
            return AgentResult(
                self.name,
                f"Word count: {len(words)}; unique terms: {unique}; shared-with-assets: {shared}/{ref_terms}.",
            )
        return AgentResult(
            self.name,
            f"Word count: {len(words)}; unique terms: {unique}.",
        )


class LegalRiskAgent(BaseAgent):
    name = "legal-risk"

    _keyword_pattern = re.compile(
        r"\b(naics|set-aside|small\s+business|8\(a\)|hubzone|wosb|sdvosb|"
        r"evaluation|section\s+m|factor|tradeoff|lpta|best\s+value|past\s+performance|cpars|"
        r"key\s+personnel|labor\s+category|fte|transition|mobilization|incumbent|"
        r"price|cost\s+realism|ceiling|nte|contract\s+vehicle|idiq|bpa|schedule)\b",
        re.IGNORECASE,
    )

    def run(self, markdown_chunk: str, assets_context: str = "") -> AgentResult:
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?;])\s+|\n+", markdown_chunk)
            if s.strip()
        ]
        matches: list[str] = []
        seen: set[str] = set()

        for sentence in sentences:
            if not self._keyword_pattern.search(sentence):
                continue
            compact = re.sub(r"\s+", " ", sentence)
            key = compact.lower()
            if key in seen:
                continue
            seen.add(key)
            matches.append(f"- {compact}")
            if len(matches) >= 8:
                break

        if not matches:
            return AgentResult(self.name, "No explicit BD gate signals were detected in this chunk.")

        return AgentResult(
            self.name,
            "Potential BD issues:\n" + "\n".join(matches),
        )


class SynthesizerAgent(BaseAgent):
    name = "synthesizer"

    def run(self, markdown_chunk: str, assets_context: str = "") -> AgentResult:
        preview = _summary_preview(markdown_chunk)
        signals = _find_clause_signals(markdown_chunk)
        has_assets = bool(assets_context.strip())
        takeaways = _strategic_takeaways(signals, assets_context)
        next_steps = _strategic_next_steps(signals, has_assets)
        heading = _detect_section_heading(markdown_chunk)

        output_lines = ["Summary preview: " + preview]
        if heading:
            output_lines.extend(["", "Section heading candidate: " + heading])
        output_lines.extend(["", "Strategic takeaways:"])
        output_lines.extend(f"- {item}" for item in takeaways)
        output_lines.append("")
        output_lines.append("Recommended next actions:")
        output_lines.extend(f"- {item}" for item in next_steps)

        if not has_assets:
            output_lines.append("")
            output_lines.append("Reference anchors: none detected")
            return AgentResult(self.name, "\n".join(output_lines))

        ref_terms = sorted(_tokenize(markdown_chunk) & _tokenize(assets_context))
        output_lines.append("")
        if ref_terms:
            output_lines.append("Reference anchors: " + ", ".join(ref_terms[:10]))
        else:
            output_lines.append("Reference anchors: none detected")
        return AgentResult(self.name, "\n".join(output_lines))
