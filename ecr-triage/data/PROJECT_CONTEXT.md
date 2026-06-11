# eCR-Triage — Project Context

> This file is the source of truth for the agent. Read it before any task.
> Scope and architecture are still evolving — when in doubt, ask before building.

## What this is

eCR-Triage is a **SMART on FHIR client app** that uses an **LLM to rank incoming
electronic case report (eICR) Bundles by urgency** at the Department of Health (DOH)
end of the eCR pipeline. It does **within-tier prioritization** of investigators'
queues, guided by an epidemiologist-co-designed rubric.

Every ranking must be **auditable**: a tier, an urgency score, and **written reasoning
per case**. The app writes results back to FHIR as **Flag** and **Task** resources.

**Humans retain final decision authority.** The tool prioritizes; it never decides.

Built for the **FHIR DevDays 2026 Student Track**. Framed as a future-state,
FHIR-native demo aligned with CDC's Data Modernization Initiative and APHL's
FHIR eCR IG 2.1.2.

## Pipeline placement (this is core to the concept)

```
EHR → eCR Now → AIMS → RCKMS → DOH
                              ▲
                    eCR-Triage sits HERE
              (post-RCKMS, pre-investigator)
```

The app does NOT do reportability determination (that's RCKMS upstream). It takes
already-reportable cases and orders the investigator's queue.

## Architecture & FHIR scope

- **Client:** SMART on FHIR client app
- **Test server:** HAPI FHIR, run locally via Docker
- **LLM:** Claude or GPT-4 via API, structured prompt + rubric. **No fine-tuning.
  No agent framework** in the app itself.
- **FHIR read:** Patient, Condition, Encounter, Observation
- **FHIR write:** Flag, Task

## Scoring / rubric

- Ranking logic is grounded in **CSTE notifiable-condition urgency tiers**:
  **4-hour, 24-hour, 7-day**. CSTE tiering doc is the primary citable source.
- Within a tier, the LLM produces a finer urgency score for queue ordering.
- Output per case MUST include: assigned tier, urgency score, written reasoning.

## Evaluation (the part the rubric is graded on — do not skip)

- **Expert concordance** — LLM ranking vs. epidemiologist ranking (Spearman for
  order, Cohen's kappa if bucketed). Headline metric.
- **False-low-urgency rate** — high-urgency case ranked low. Weighted heavily.
  This is the failure mode we most want to avoid.
- **Tier accuracy** — confusion matrix across the three CSTE tiers.
- **Rubric adherence** — does the written reasoning actually map to the score?
- Requires a **gold-standard set** of ~20–30 expert-ranked cases to measure against.

## Checks / guardrails (every failure path ends at a human)

- **Schema validation** — LLM output must parse to {tier, score, reasoning}; reject + retry on malformed.
- **Tier–score consistency** — flag contradictions (e.g. "4-hour" tier with low score).
- **Grounding check** — reasoning must reference resources actually in the Bundle; reject confabulation.
- **Determinism** — low temperature; same case shouldn't swing wildly.
- **Write-back validation** — Flag/Task must be valid FHIR before POST.

## Fallbacks

- Malformed output → retry once stricter → else route to "manual review" (never drop the case).
- Low confidence / ambiguous → surface unranked to investigator with a note (never false-low).
- API failure / timeout → queue for retry (never silently lose).
- Fails grounding check → flag for human, do not write back.

## Out of scope (do NOT build)

- Reportability determination (RCKMS does this)
- Data quality / QC / duplicate detection as a primary feature
- Fine-tuning, agent frameworks inside the app
- Anything that removes human final authority

## Definition of done (end-to-end)

Bundle in → parsed (Patient/Condition/Encounter/Observation) → LLM ranks with
tier + score + reasoning → guardrails pass → Flag + Task written to HAPI →
result visible in a ranked queue. Measurable against the gold-standard set.
