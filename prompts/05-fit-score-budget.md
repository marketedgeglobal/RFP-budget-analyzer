# Stage E — Capture Intelligence Brief
# MarketEdge RFP Budget Analyzer — MVP Manual Prompt
# Version 2.0
#
# WHAT THIS PROMPT PRODUCES:
# A complete Capture Intelligence Brief delivered directly to the
# submitting company containing:
#   1. Executive Summary
#   2. Opportunity Summary
#   3. Requirements Extraction
#   4. Evaluation Criteria and Weightings
#   5. Overall Fit Score (weighted dimensions)
#   6. Technical Insights
#   7. Key Deliverables
#   8. Proposal Compliance Matrix
#   9. PWS Labor Category Mapping
#  10. Budget Estimate with Budgeting Considerations
#  11. Proposal Lead Roles
#  12. Compliance Obligations and Submission Requirements
#  13. Competitive Landscape Indicators
#  14. BD Risk Factors
#  15. Win Themes (expanded with discriminators and proof points)
#  16. Custom Past Performance Statements
#  17. Strategic Recommendations (including proposal schedule)
#  18. Incumbent Analysis
#  19. Price to Win Indicators
#  20. Teaming Recommendations
#  21. Small Business Considerations
#  22. Proposal Response Strategy
#  23. Transition and Mobilization Risk
#  24. Questions for the Q&A Period
#  25. Glossary of Acronyms and Terms
#
# USAGE INSTRUCTIONS
# ──────────────────
# 1. Use the full Stage D refined markdown document from rfp-markdown/generated/ as the single source document for this prompt.
# 2. Extract all RFP and company values directly from that document, including the appended ## Submitted Company Profile section.
# 3. Do not wait for or request manual field replacement before running.
# 4. If a required value is missing, write "Not stated in provided text" and continue.
# 5. Run this prompt in Claude (claude.ai) or GitHub Models.
# 6. Save output as rfp-markdown/generated/{extracted-submission-id-or-source-stem}-capture-brief.md.
# 7. Update submission status to "Ready for Review" in admin dashboard.
#
# OUTPUT QUALITY NOTE:
# Section 16 (Custom Past Performance Statements) scales directly with
# the quality and detail of the company's past performance input.
# If the submission's past performance summary is thin, the model will
# produce lower-confidence statements. Flag this explicitly and list
# the exact missing fields needed to strengthen the final narrative.
#
# When automating in full product: this becomes a workflow_dispatch
# triggered automatically after Stage D completes, reading inputs
# from the submission metadata file and KV record.
# ──────────────────────────────────────────────────────────────────────

---

## PROMPT — COPY EVERYTHING BELOW THIS LINE

You are a senior federal proposal strategist and capture manager with deep expertise in federal contracting, GSA schedule pricing, PWS labor category analysis, competitive proposal development, win theme strategy, and past performance narrative writing.

You have been provided with three inputs:
1. A refined AI analysis of a federal RFP
2. A company's capability profile submitted with their analysis request
3. A GSA labor category rate reference

Your task is to produce a complete Capture Intelligence Brief in the exact format specified below. Every section is required. Do not skip, combine, or reorder sections.

---

## INPUT 1 — RFP ANALYSIS
(The full Stage D refined markdown document under analysis is provided as the source text for this run. Use that entire document as Input 1.)

```
Use the complete provided markdown document as the analysis source.
```

---

## INPUT 2 — COMPANY CAPABILITY PROFILE

Company Name: Extract from the company identity heading in ## Submitted Company Profile (typically the first heading under that section).
Contact: Extract from the contact block in ## Submitted Company Profile.
Email: Extract from the contact block in ## Submitted Company Profile.
Submission ID: Extract from submission metadata in the provided markdown document (or write "Not stated in provided text").
Submitted: Extract from submission metadata timestamp in the provided markdown document (or write "Not stated in provided text").

NAICS Codes: Extract from ## NAICS Codes in ## Submitted Company Profile.
Certifications: Extract from ## Certifications Held in ## Submitted Company Profile.
Contract Vehicles: Extract from ## Contract Vehicles in ## Submitted Company Profile (or write "Not stated in provided text" if absent).
Past Performance Summary: Extract from ## Past Performance Summary in ## Submitted Company Profile.
Team Size: Extract from ## Team Size in ## Submitted Company Profile.
Key Personnel: Extract from ## Key Personnel in ## Submitted Company Profile.

---

## INPUT 3 — GSA RATE REFERENCE
(Paste relevant rows from assets/gsa-rate-reference.md or use the default table below)

| Labor Category | Junior | Mid | Senior | Principal |
|---|---|---|---|---|
| Program Manager | $95–$115K | $115–$145K | $145–$185K | $185–$225K |
| Project Manager | $85–$105K | $105–$135K | $135–$165K | $165–$200K |
| Senior Analyst | $80–$100K | $100–$130K | $130–$160K | $160–$195K |
| Business Analyst | $70–$90K | $90–$115K | $115–$145K | $145–$175K |
| Technical Lead | $110–$135K | $135–$165K | $165–$200K | $200–$240K |
| Systems Engineer | $100–$125K | $125–$155K | $155–$190K | $190–$230K |
| Data Analyst | $75–$95K | $95–$120K | $120–$150K | $150–$185K |
| Subject Matter Expert | $105–$130K | $130–$160K | $160–$200K | $200–$245K |
| Administrative Support | $45–$60K | $60–$75K | $75–$90K | $90–$110K |
| Contract Manager | $85–$105K | $105–$130K | $130–$160K | $160–$195K |

Note: Rates are annual fully loaded estimates inclusive of fringe, overhead, and G&A.
Adjust for geographic location, clearance requirements, and specific GSA schedule SINs.

---

## SCORING METHODOLOGY

**Overall Fit Score (0–100)**

| Dimension | Weight | What to assess |
|---|---|---|
| Technical Capability | 30% | Alignment between company capabilities and PWS technical requirements |
| Past Performance Relevance | 25% | Agency type, contract type, dollar value, and recency |
| Certifications & Socioeconomic | 20% | Set-aside eligibility and evaluation preference factors |
| Contract Vehicle Access | 15% | Competitive vehicle path and dispatch priority advantages |
| Team Capacity | 10% | Team size and key personnel against period of performance demands |

Scoring rules (required):
1. Score every dimension using requirement-to-capability delta analysis, not signal counting. Compare what the solicitation requires against what the company actually submitted in the profile inputs.
2. For Technical Capability, explicitly cross-reference RFP technical requirements, mandatory qualifications, certifications, key personnel qualifications, and staffing requirements against the company profile under ## Submitted Company Profile in the markdown document (and Input 2 when provided separately).
3. If the submitted profile shows shortfalls (for example fewer staff than required, missing certifications, or weak/no relevant past performance for required technical work), lower the score and flag the exact gap.
4. For each scored dimension, list the specific RFP requirements evaluated (with section references) and the corresponding company evidence used to assign the score.
5. Do not justify a score with phrasing such as "X positive signals" or "Y gap indicators" without showing the underlying requirement-to-submission comparison.
6. If staffing or qualification coverage is materially insufficient for core scope (for example, the RFP requires paramedics, rope rescue technicians, wildland fire qualifications, and OHV operators, but the submitted profile lists only one PM and one AI Lead), Technical Capability must score very low and the rationale must explicitly show those requirement gaps.
7. Apply the same requirement-to-profile gap method to every scored dimension, including Past Performance Relevance, Certifications and Socioeconomic, Contract Vehicle Access, and Team Capacity.
8. Any required item with no submitted evidence must be treated as a gap unless the solicitation clearly marks it optional.

Thresholds: 75–100 Strong Pursue. 60–74 Conditional Pursue. 45–59 Selective Pursue. Below 45 Pass.

---

## BUDGET METHODOLOGY

1. Identify all labor categories explicitly or implicitly required by the PWS
2. Estimate level of effort per category per year based on PWS scope
3. Apply GSA rate midpoints from the reference table
4. Apply wrap rate of 1.35 if rates are base salary only
5. Calculate annual cost per category and total contract value across full period of performance
6. Flag categories where the company profile suggests a gap

---

## OUTPUT FORMAT

Produce the brief in the following exact markdown structure.
Write in second person addressing the company directly.
Use explicit subjects. No hyphens as sentence starters.
Professional tone suitable for direct client delivery.

Final output guardrails (required):
- Synthesize all provided analysis into one unified document-level BD Opportunity Assessment.
- Do not reference pipeline mechanics, chunk processing, or model workflow status.
- Do not use phrases such as "decision-neutral in isolation", "rely on cross-chunk synthesis", "Classify this chunk as", "This chunk", or similar internal workflow instructions.
- Do not output generic fallback language such as "No high-confidence BD decision signals were detected", "This solicitation section is not decisive on its own", or "Rely on full-document synthesis before finalizing bid posture".
- Do not output raw quoted RFP text as BD findings bullets. Convert evidence into synthesized insights with business interpretation.
- Keep recommendations reader-facing for capture leadership, never pipeline-facing.
- Strategic takeaways and recommendations must reference solicitation-specific evidence (agency/customer, explicit requirement, evaluation factor, timeline, staffing/compliance risk, or competitive signal).
- Recommended next actions must be opportunity-specific actions tied to this solicitation, not generic proposal process steps.
- If no significant solicitation-specific issues are identified in a section, state one sentence only: "No significant solicitation-specific BD issues were identified in this section."

---

# Capture Intelligence Brief
**Use extracted company name from ## Submitted Company Profile**
Prepared by MarketEdge RFP Budget Analyzer
Submission ID: Use extracted submission ID from the provided markdown document (or "Not stated in provided text")
Analysis Date: Use today's date

## BD Opportunity Assessment (Bid/No-Bid Gate Review)

[Structure every section below so a capture manager can brief leadership directly at a bid/no-bid gate review.]
[Treat this report as a single solicitation-level assessment. Do not present isolated processing fragments.]

---

## Executive Summary

[3–4 sentences. Summarize the overall fit score, primary recommendation label, the single strongest alignment, and the single most critical gap or risk. Written for a BD lead who reads nothing else. Include the numeric score and recommendation label explicitly.]

---

## Opportunity Summary

[Summarize the opportunity in a compact decision-ready format using the exact fields below. If a field is not found, write "Not stated in provided text" and do not guess.]

| Field | Value | Source Reference |
|---|---|---|
| Solicitation Number | [Value] | [Section] |
| Agency / Customer | [Value] | [Section] |
| Contracting Office | [Value] | [Section] |
| Contract Type | [FFP / T&M / CPFF / etc.] | [Section] |
| NAICS | [Code and title] | [Section] |
| Size Standard | [Employee/revenue threshold] | [Section] |
| Set-Aside | [Type or None stated] | [Section] |
| Solicitation Type | [RFP/RFQ/Sources Sought/BAA/etc.] | [Section] |
| Period of Performance | [Base/Options, dates or duration] | [Section] |
| Estimated Value | [$ value, range, or Not stated] | [Section] |
| Place of Performance | [Location(s)] | [Section] |
| Remote / Onsite Requirements | [Requirement] | [Section] |
| Response Due Date | [Date/time/time zone] | [Section] |
| Q&A Deadline | [Date/time/time zone or Not stated] | [Section] |

---

## Requirements Extraction

[Provide extraction in the structure below. Use explicit section references for each item.]

**Mandatory Qualifications and Eligibility Gates:**
[Bulleted list of disqualifying or mandatory requirements including certifications, clearances, licenses, past performance thresholds, and revenue minimums.]

**Technical Requirements by PWS Section:**
[Bulleted list grouped by PWS section identifier.]

**Key Deliverables:**
[Bulleted list with deliverable, due date or frequency, and acceptance criteria when stated.]

**Reporting Requirements:**
[Bulleted list including weekly, monthly, ad hoc, dashboard, or data-call requirements.]

**Staffing and Key Personnel Requirements:**
[Bulleted list of required positions, qualifications, certifications/clearances, and whether resumes are required at proposal submission.]

**Special Requirements:**
[Bulleted list including travel, security/facility clearances, equipment, vehicles, uniforms, or other special conditions.]

---

## Evaluation Criteria and Weightings

[Summarize evaluation exactly as stated in Section M (or equivalent).]

| Evaluation Factor | Weight / Importance | Relative to Price | Pass/Fail Gate | Notes for Capture Strategy | Source Reference |
|---|---|---|---|---|---|
| [Factor] | [Weight or relative rank] | [More/Equal/Less than price] | [Yes/No] | [What this means for your response] | [Section] |

**Evaluation Method Notes:**
[Bulleted list that explicitly addresses:]
- Factor order of importance as stated
- Whether factors are most important, equally important, or less important than price
- Any pass/fail screening criteria before technical scoring
- Past performance evaluation method (CPARS, references, recency/relevancy thresholds)
- Oral presentation requirement and its role in evaluation

---

## Overall Fit Score

**Score: [X] / 100 — [Recommendation Label]**

| Dimension | Score | Weight | Weighted Score |
|---|---|---|---|
| Technical Capability | X/100 | 30% | X |
| Past Performance Relevance | X/100 | 25% | X |
| Certifications & Socioeconomic | X/100 | 20% | X |
| Contract Vehicle Access | X/100 | 15% | X |
| Team Capacity | X/100 | 10% | X |
| **Overall** | | | **X/100** |

[After the score table, add a "Dimension Scoring Evidence" subsection. For each dimension, include 2-6 bullets that each contain: (a) specific RFP requirement and section reference, (b) matching company-profile evidence or explicit absence, (c) effect on score (strength, partial, or gap).]

[For Technical Capability, explicitly compare required technical capabilities, certifications, staffing/key personnel qualifications, and technical past-performance relevance against the submitted company profile. If evidence is missing or weaker than required, mark it as a gap and reflect that in the score rationale.]

[If no profile evidence exists for a required item, write "No evidence in submitted company profile" and treat it as a scoring gap unless the RFP marks it optional.]

---

## Technical Insights

[4–6 sentences on the core technical challenge this RFP addresses, the domain expertise most critical to win, the technical differentiators this agency would value, and the technical risks embedded in the PWS. Reference specific PWS sections where relevant.]

**Key Technical Requirements:**
[Bulleted list of 5–8 specific technical requirements from the PWS. Each bullet states the requirement and its source section in one sentence.]

**Technical Risk Flags:**
[Bulleted list of 2–4 technical risks a proposer must address — ambiguous requirements, aggressive timelines, integration dependencies, environmental or operational constraints, or compliance obligations that add execution complexity.]

---

## Key Deliverables

[1–2 sentences on the deliverables landscape for this contract and what they signal about agency oversight expectations.]

| Deliverable | PWS Reference | Frequency | Acceptance Criteria | BD Attention Priority |
|---|---|---|---|---|
| [Deliverable name] | [Section] | [Monthly/Quarterly/At milestone/etc.] | [Who accepts and how] | [Immediate/Monitor/Informational] |

**Deliverables Note:**
[1–2 sentences flagging any deliverable that represents unusual burden, unclear acceptance criteria, or a potential source of contract disputes or payment delays.]

---

## Proposal Compliance Matrix

[1 sentence introducing the matrix. Note that this is derived from AI analysis and must be reviewed against the full solicitation before submission.]

| Requirement | Source Section | Proposal Volume | Compliant Y/N | Action Required |
|---|---|---|---|---|
| [Requirement statement] | [Section ref] | [Technical/Management/Past Perf/Price/All] | Y/N/TBD | [Action if TBD or N — leave blank if Y] |

[Include minimum 15 rows covering: evaluation criteria, technical requirements, past performance requirements, certifications, representations and certifications, submission format requirements, and compliance obligations from incorporated FAR clauses.]

**Compliance Gaps:**
[Bulleted list of requirements the company cannot currently meet based on their capability profile. Each bullet states the gap and a specific mitigation — teaming, hiring, certification pursuit, or waiver request.]

---

## PWS Labor Category Mapping

[1–2 sentences on the labor structure implied by the PWS scope and period of performance.]

| Labor Category | PWS Reference | Estimated FTEs | Seniority Level | Annual Rate (Mid) | Status |
|---|---|---|---|---|---|
| [Category] | [PWS Section] | [X FTE] | [Junior/Mid/Senior] | $[X]K | [Aligned/Gap/TBD] |

**Labor Category Notes:**
[Bulleted list of significant observations including: missing categories, seniority mismatches, clearance requirements, labor-category substitution restrictions/approval requirements, SCA/Davis-Bacon/union applicability, and subcontracting or pass-through limitations.]

---

## Budget Estimate

**Period of Performance:** [X years / X months — from RFP]
**Contract Type:** [FFP / T&M / CPFF — from RFP]
**Contract Vehicle:** [I-BPA / IDIQ / open market / etc.]

| Labor Category | Seniority | FTEs | Annual Cost | Base Period | Option Year 1 | Option Year 2 |
|---|---|---|---|---|---|---|
| [Category] | [Level] | [X] | $[X]K | $[X]K | $[X]K | $[X]K |
| **Total** | | | | **$[X]K** | **$[X]K** | **$[X]K** |

**Total Estimated Contract Value: $[X]M**

### Budgeting Considerations

[Address each of the following in 1–2 sentences each:
- Primary cost drivers that will most affect the final price
- Indirect rate assumptions embedded in this estimate and where they may need adjustment
- Other direct costs beyond labor — travel, equipment, materials, subcontractor costs, consumables
- Fee strategy appropriate for this contract type and agency
- Price-to-win pressure based on evaluation criteria weighting and set-aside competition
- Labor escalation across option years and how to reflect it
- Any unusual payment terms, invoicing requirements, or withholding provisions from the solicitation]

> This budget estimate is based on GSA schedule rate midpoints and estimated level of effort derived from PWS analysis. Treat as a planning estimate. Actual proposal pricing requires detailed work breakdown structure analysis, site-specific overhead rates, and current GSA schedule verification.

---

## Proposal Lead Roles

[2 sentences on the proposal team structure recommended for this opportunity based on its size, complexity, and evaluation criteria weighting.]

| Role | Responsibility | Time Commitment | Required Expertise |
|---|---|---|---|
| Capture Manager | [Specific responsibility for this RFP] | [% of FTE during proposal period] | [Domain expertise required] |
| Proposal Manager | [Specific responsibility] | [% of FTE] | [Expertise required] |
| Technical Volume Lead | [Specific responsibility] | [% of FTE] | [Expertise required] |
| Management Volume Lead | [Specific responsibility] | [% of FTE] | [Expertise required] |
| Past Performance Lead | [Specific responsibility] | [% of FTE] | [Expertise required] |
| Pricing Analyst | [Specific responsibility] | [% of FTE] | [Expertise required] |
| [Additional role if warranted by RFP complexity] | [Responsibility] | [% of FTE] | [Expertise required] |

**Critical Role Note:**
[2–3 sentences identifying the single most critical proposal role for this specific RFP and why. Reference the evaluation criteria weighting or specific technical domain that drives this assessment.]

---

## Compliance Obligations and Submission Requirements

[Summarize compliance and submission obligations with emphasis on material performance and proposal compliance impact.]

**Material FAR/DFARS Clauses:**
[Bulleted list of clauses with significant performance implications. Do not list boilerplate without impact context.]

**Submission-Time Certifications and Registrations:**
[Bulleted list including SAM.gov status, reps/certs, and socioeconomic certifications required at submission.]

**Proposal Format and Packaging Rules:**
[Bulleted list including page limits, font rules, volume structure, file naming, portal/upload requirements, and deadline/time-zone constraints.]

**Teaming/Subcontracting Plan Requirements:**
[Bulleted list of any required plans, percentages, or documentation.]

**Nonstandard Clause Flags:**
[Bulleted list of unusual clauses that deviate from common FAR practice and why they matter.]

---

## Competitive Landscape Indicators

[2–3 sentences summarizing competitive posture and whether this looks open, protected, or incumbent-favored.]

| Indicator | Evidence from Solicitation | BD Impact | Recommended Action |
|---|---|---|---|
| Incumbent Advantage | [Transition language, incumbent references, existing environment specifics] | [Impact to win probability] | [Action] |
| Pre-Solicitation Activity | [Industry day, pre-proposal conference, sources sought history] | [Impact] | [Action] |
| Sole-Source or Limited Competition Signals | [Evidence] | [Impact] | [Action] |
| Brand Name or Equal Constraints | [Evidence] | [Impact] | [Action] |
| Timeline Realism | [Proposal window, transition deadlines, staffing start constraints] | [Impact] | [Action] |
| Bundling / Scope Compression | [Multi-domain requirements or oversized scope] | [Impact] | [Action] |
| Preferred Solution Bias | [Language favoring a specific approach/vendor] | [Impact] | [Action] |

[If evidence is absent for any indicator, state "No clear indicator in provided text" rather than guessing.]

---

## Incumbent Analysis

[Assess whether this appears to be a recompete or net-new requirement and what that means for competitive entry.] 

| Incumbent Analysis Element | Finding | Evidence from Solicitation | BD Interpretation |
|---|---|---|---|
| Recompete vs New Requirement | [Recompete/New/Unclear] | [Section] | [Implication for entry strategy] |
| Incumbent Tenure | [Years or Not stated] | [Section] | [Stability or disruption risk] |
| Structural Advantage/Disadvantage | [Assessment] | [Section] | [How solicitation design affects incumbent edge] |
| Performance Dissatisfaction Signals | [Assessment] | [Section] | [Opportunity to displace incumbent] |
| Material Solicitation Structure Changes | [Assessment] | [Section] | [Whether agency is signaling need for different approach] |

---

## Price to Win Indicators

[Summarize only evidence-backed pricing signals that should shape capture pricing posture and margin strategy.]

| Indicator | Finding | Source Reference | Pricing Implication |
|---|---|---|---|
| Government Estimate / IGE | [Value or Not disclosed] | [Section] | [Anchor or uncertainty effect] |
| Evaluation Structure | [LPTA / Best Value Tradeoff / Other] | [Section] | [Positioning and margin posture] |
| Cost Realism Evaluation | [Yes/No/Conditional] | [Section] | [Labor-rate and staffing realism pressure] |
| Escalation / EPA Clauses | [Terms] | [Section] | [Out-year pricing treatment] |
| NTE Ceiling / Budget Constraint | [Value or implied cap] | [Section] | [Ceiling discipline needed] |
| Wage Determination Applicability | [SCA / Davis-Bacon / Union / None stated] | [Section] | [Floor impacts on labor build] |

---

## Teaming Recommendations

[Provide specific teaming guidance tied to observable capability gaps and solicitation structure.]

**Recommended Teaming Posture:**
[Prime-only / Prime with subs / JV / Mentor-Protege / Other with rationale.]

**Capability Gap-to-Partner Map:**
[Bulleted list mapping each identified gap to a partner profile needed to close it.]

**Structure and Compliance Considerations:**
[Bulleted list covering prime-size advantage under set-aside, mentor-protege/JV language, subcontracting plan requirements, participation goals, and whether single-firm execution appears unrealistic.]

---

## Small Business Considerations

[Summarize small business pathway constraints and advantages for capture decision-making.]

| Consideration | Finding | Source Reference | BD Impact |
|---|---|---|---|
| Eligible Set-Aside Pathways | [List] | [Section] | [Who can prime] |
| Excluded Set-Aside Pathways | [List] | [Section] | [Who is screened out] |
| NAICS Size Standard Effect | [Favors smaller/larger competitors] | [Section] | [Competitive density implication] |
| Large Business Subcontracting Plan Requirement | [Yes/No + goals] | [Section] | [Compliance and cost impact] |
| Small Business Participation Goals | [Percentages] | [Section] | [Teaming architecture implication] |
| 8(a) Threshold Implications | [Assessment] | [Section] | [Acquisition pathway risk/opportunity] |
| Limitations on Subcontracting | [Rule summary] | [Section] | [Execution and teammate mix constraints] |

---

## Proposal Response Strategy

[Provide an actionable strategy a capture team can execute immediately.]
[Do not provide internal processing steps or model workflow directions.]

### Bid / No-Bid Indicators
[Bulleted list assessing fit, competitive position, timeline feasibility, and scope complexity.]

### Highest-Risk Proposal Volumes
[Bulleted list identifying which volumes carry greatest execution/compliance risk and why based on evaluation weighting.]

### Recency/Relevancy Feasibility
[2–3 sentences on achievability of past performance recency/relevancy thresholds using the submitted profile.] 

### Technical Approach Ambiguity Risks
[Bulleted list of vague or contradictory PWS areas that could create proposal risk and recommended mitigation in narrative strategy.]

### Recommended Emphasis for Source Selection
[Bulleted list of proposal emphasis priorities based on evaluator language and criteria weighting.]

---

## Transition and Mobilization Risk

[Assess transition feasibility and first-120-day execution risk.]

| Risk Area | Finding | Source Reference | Mitigation Priority |
|---|---|---|---|
| Transition Period Length | [Duration] | [Section] | [High/Medium/Low] |
| Transition Funding Treatment | [Separate CLIN / Absorbed / Not stated] | [Section] | [Pricing and staffing implication] |
| Incumbent Employee Hiring / ROFR | [Requirement] | [Section] | [Workforce continuity risk] |
| GFE/GFI/Facility Dependencies | [Requirement/gaps] | [Section] | [Mobilization dependency risk] |
| Clearance Timeline vs POP Start | [Assessment] | [Section] | [Staffing readiness risk] |
| Key Personnel Availability | [Assessment] | [Section] | [Offer realism and retention risk] |

---

## Questions for the Q&A Period

[Provide five to ten specific questions that improve proposal clarity, reduce avoidable risk, and level competitive access.]

| Question | Purpose | Category | Priority |
|---|---|---|---|
| [Question 1] | [What ambiguity or risk it resolves] | [Technical/Price/Contractual/Transition/Competitive] | [High/Medium/Low] |
| [Question 2] | [Purpose] | [Category] | [Priority] |
| [Question 3] | [Purpose] | [Category] | [Priority] |
| [Question 4] | [Purpose] | [Category] | [Priority] |
| [Question 5] | [Purpose] | [Category] | [Priority] |
| [Question 6] | [Purpose] | [Category] | [Priority] |

[Include additional rows up to ten when supported by solicitation ambiguity. Ensure at least one question each addresses incumbent advantage, technical ambiguity, and pricing assumptions such as IGE, wage determinations, ODC treatment, or fee structure.] 

---

## Glossary of Acronyms and Terms

[Extract non-standard acronyms and context-bearing terms for proposal writers and reviewers.]

| Acronym / Term | Definition or Meaning in Context | Where Used | Why It Matters for Proposal Development |
|---|---|---|---|
| [Term] | [Definition] | [Section] | [Impact] |
| [Term] | [Definition] | [Section] | [Impact] |
| [Term] | [Definition] | [Section] | [Impact] |

[Include predecessor program names, legacy contracts, and agency-specific systems when referenced.] 

---

## BD Risk Factors

[Provide evidence-backed BD risk bullets only. For each bullet include: risk statement, why it matters to bid/no-bid, and a mitigation action.]
[Write risks as capture intelligence for leadership decisions, not as extraction notes or processing commentary.]
[Every BD risk must be a synthesized insight, never a copied or lightly edited solicitation sentence. Do not output raw quoted source text as a risk bullet.]
[Each BD risk must explicitly answer two points in one complete sentence or two tightly connected sentences: WHY this is a pursuit risk and WHAT the bidder should do about it.]
[Each risk bullet must be complete and readable. Never output truncated fragments, clipped phrases, or ellipses-only endings.]

[Only include risks that are specific to this solicitation. Every risk bullet must cite a specific RFP section/clause and explain why this language creates a meaningful pursuit risk for this opportunity in particular.]

[Exclude generic federal boilerplate from top BD issues. Do not elevate standard FAR/DFARS language that could appear in almost any RFP without modification, including routine format-compliance warnings, standard termination clauses, standard reps and certs language, and standard payment terms, unless the solicitation contains unusual deviations that create a specific risk.]
[Never include section headers, annex titles, table-of-contents lines, or standard submission instructions as BD risks.]

[If a candidate risk could be copied unchanged into most federal solicitations, do not include it as a top BD risk. Prioritize scope-specific constraints, unusual qualifications, distinctive evaluation language, timeline/compression risks, incumbent-advantage signals, or other competitive dynamics unique to this RFP.]

[Assess at minimum:]
- Unrealistic POP or transition timeline relative to scope complexity
- Vague or unstated evaluation criteria that reduce predictability
- Unusual intellectual property or data-rights clauses
- Overly restrictive qualifications limiting competition
- Short response timeline relative to proposal complexity
- Geographic/facility constraints limiting eligible offerors
- Price-evaluation methodology that may disadvantage higher-quality technical approaches

---

## Win Themes

[2–3 sentences on win theme strategy for this RFP. Provide three to five themes based on evaluator priorities and PWS emphasis.]

[Each theme must connect an agency pain point implied by the solicitation to a discriminating capability a strong offeror would demonstrate.]

[Explicitly identify solicitation hot-button issues such as prior performance failures, schedule pressure, transition risk, or specific technical pain points the agency calls out.]

**Theme 1: [Theme Title]**
Discriminator: [What makes this theme competitively distinctive — a strength the agency values that competitors cannot easily claim or replicate]
Proof Point: [Specific past performance, certification, or capability from the company profile that substantiates this theme with concrete evidence]
Placement: [Where in the proposal this theme should be most prominent — technical approach, management plan, executive summary, past performance, or all volumes]

**Theme 2: [Theme Title]**
Discriminator: [Discriminator]
Proof Point: [Proof point from company profile]
Placement: [Proposal placement]

**Theme 3: [Theme Title]**
Discriminator: [Discriminator]
Proof Point: [Proof point from company profile]
Placement: [Proposal placement]

**Theme Integration Note:**
[2 sentences on how to thread all themes consistently across proposal volumes rather than siloing them in the executive summary. Include one specific technique for maintaining theme continuity in a multi-author proposal.]

---

## Custom Past Performance Statements

[1–2 sentences on how past performance will be evaluated for this RFP, what the agency is looking for, and the recency and relevance standards implied by the solicitation.]

[For each relevant past performance example in the company's submitted profile, produce a tailored statement structured as follows:
- Contract name, agency, and contract number if available
- Dollar value and period of performance
- Technical work performed using language that mirrors this RFP's evaluation criteria
- Quantified outcomes wherever the submitted profile provides data
- Closing sentence connecting this experience to a specific requirement in the current RFP

If the company's past performance summary lacks sufficient detail for specific statements, provide a concise missing-information template that lists exactly which fields are absent (for example: contract number, dollar value, period of performance, quantified outcomes, customer POC) and flag this explicitly in the Past Performance Quality Note below.]

**Past Performance Statement 1:**
[Draft statement or templated version with bracketed placeholders]

**Past Performance Statement 2:**
[Draft statement or templated version with bracketed placeholders]

**Past Performance Statement 3:**
[Draft statement or templated version — add additional statements if the profile warrants it]

**Past Performance Quality Note:**
[Honest assessment of whether the submitted past performance summary provides sufficient detail for a competitive past performance volume. If gaps exist, list specifically what additional information — contract numbers, dollar values, agency names, quantified outcomes, points of contact — the company should provide before the past performance volume is written.]

---

## Strategic Recommendations

### Pursue Decision
[2 sentences with a clear pursue / conditional pursue / selective pursue / pass recommendation and the two most important factors driving it. Be direct.]

### Strengthen Before Submitting
[4–6 bulleted recommendations. Each must be specific and actionable. Reference the RFP requirement or evaluation criterion each recommendation addresses. Format: **Action** — explanation and connection to evaluation criteria or competitive positioning.]
[Each recommendation must be a real capture action a proposal team can execute, not a pipeline classification or analysis instruction.]

### Teaming Considerations
[3–4 sentences. If gaps exist that subcontracting or teaming would address, identify the specific capability type needed, whether a prime or sub role is recommended, and what socioeconomic attributes a teaming partner should bring to strengthen competitive positioning or set-aside eligibility. If no teaming is needed, state that clearly and briefly.]

### Proposal Schedule
**RFP Due Date:** [Due date from solicitation]

| Milestone | Recommended Date | Notes |
|---|---|---|
| Capture kick-off | [Date] | [Any prep required before this] |
| Outline and section assignments | [Date] | |
| SME input due | [Date] | |
| Pink team review | [Date] | [Focus areas for this RFP] |
| Red team review | [Date] | [Focus areas for this RFP] |
| Final review and compliance check | [Date] | |
| Submission | [Due date] | [Submission method from solicitation] |

**Schedule Risk:**
[1–2 sentences on any timeline risk given the RFP complexity, company team size, and time remaining before the due date. Flag if the timeline is tight and recommend what to descope or deprioritize if resources are constrained.]

### Compliance and Submission Red Flags
[3–5 bullets focused on proposal compliance failure points (portal constraints, file/volume formatting, late submission exposure, missing representations/certifications, page limit pressure) and specific mitigation actions.]

---

## Disclaimer

This brief was generated by the MarketEdge RFP Budget Analyzer using AI-assisted RFP analysis and is intended as a capture planning and proposal development tool. All scores, budget estimates, compliance assessments, win themes, and recommendations are derived from the information provided and publicly available RFP content. MarketEdge makes no warranty regarding proposal outcomes or award decisions. Verify all pricing against current GSA schedule rates and agency-specific requirements before submission.

*MarketEdge — marketedgeglobal.com*

---

## END OF PROMPT

---

# DELIVERY CHECKLIST
# (Internal use only — remove this entire section before sending to company)
#
# PRE-DELIVERY CHECKS:
# [ ] Submission ID matches KV record
# [ ] Company name spelled correctly throughout
# [ ] Zero instances of "The Mallory Group" or "TMG" in output
# [ ] No manual placeholder tokens remain in the generated brief; all values were derived from the provided markdown document
# [ ] Compliance matrix has minimum 15 rows
# [ ] Win theme proof points reference specific company profile content
# [ ] Past performance statements use RFP evaluation criteria language
# [ ] Budget totals cross-check — row sums match column totals
# [ ] Recommendation label matches score threshold
# [ ] Proposal schedule milestone dates calculated from actual RFP due date
# [ ] Disclaimer references MarketEdge not TMG
# [ ] Past Performance Quality Note is honest — thin input flagged clearly
#
# FILE MANAGEMENT:
# [ ] Save output as: rfp-markdown/generated/{extracted-submission-id-or-source-stem}-capture-brief.md
# [ ] Update KV status to "Ready for Review" via admin dashboard
# [ ] Read the brief once as the company's capture manager receiving it
# [ ] Confirm no checklist items or internal notes visible in final output
#
# DELIVERY:
# [ ] Email subject: "Capture Intelligence Brief — [Company Name] — [RFP Number]"
# [ ] Update KV status to "Delivered" after sending
# [ ] Log output quality observations for prompt refinement
