# CSTE / CDC Notifiable Condition Tiers

**Source:** Protocol for Public Health Agencies to Notify CDC about the Occurrence of
Nationally Notifiable Conditions, 2025 — Categorized by Notification Timeliness.
Approved by CSTE June 2024, implemented January 1, 2025, updated November 19, 2024.
CDC National Notifiable Diseases (ndc.services.cdc.gov).

> This file is the canonical source for eCR-Triage's tier logic. The triage prompt
> and the validator both derive from it. Keep this file in sync with any prompt changes.

---

## What the tiers mean

These tiers describe **how quickly a public health agency must notify CDC** — they are
a legal/reporting floor, NOT a direct measure of how urgent an investigator's work is.

| Tier | CDC definition | eCR-Triage label |
|------|----------------|------------------|
| Extremely urgent | Call CDC EOC within **4 hours** of a case meeting notification criteria; electronic notification next business day | `4-hour` |
| Urgent | Call CDC EOC within **24 hours**; electronic notification next scheduled transmission | `24-hour` |
| Routine | Submit electronic case notification within the next reporting cycle | `7-day` |

## How eCR-Triage uses them

1. **Tier is the primary sort.** A case's CSTE tier sets its top-level priority.
2. **Most real eICRs are routine (7-day).** The 4-hour and 24-hour lists are short and
   high-consequence; the routine bucket is the large majority of incoming cases.
3. **Within a tier, `urgency_score` (1–10) breaks ties.** This is where eCR-Triage adds
   value — differentiating the large routine queue. The scoring factors are being
   derived from published literature on case-investigation prioritization (separate doc).
4. The score NEVER overrides the tier. A 4-hour/score-3 case still outranks a
   7-day/score-10 case.

---

## TIER: 4-hour (Immediately notifiable, extremely urgent)

Almost entirely bioterrorism / catastrophic-exposure scenarios.

```yaml
tier_4_hour:
  - condition: Anthrax
    qualifier: source of infection not recognized; recognized bioterrorism exposure / potential mass exposure; serious illness of naturally-occurring anthrax
  - condition: Botulism
    qualifier: foodborne (except endemic to Alaska); intentional/suspected intentional release; infant botulism clusters/outbreaks; unknown etiology
  - condition: Plague
    qualifier: suspected intentional release
  - condition: SARS-associated coronavirus
    qualifier: all cases prior to classification
  - condition: Smallpox
    qualifier: confirmed and probable cases
  - condition: Tularemia
    qualifier: suspected intentional release
  - condition: Viral hemorrhagic fevers
    qualifier: suspected intentional release (Ebola, Marburg, Lassa, Crimean-Congo, etc.)
```

## TIER: 24-hour (Immediately notifiable, urgent)

High-consequence communicable diseases.

```yaml
tier_24_hour:
  - condition: Anthrax
    qualifier: naturally-occurring or occupational, responding to treatment
  - condition: Brucellosis
    qualifier: multiple cases, temporally/spatially clustered
  - condition: Cronobacter invasive infection
    qualifier: infants
  - condition: Diphtheria
  - condition: Novel influenza A virus infection
  - condition: Measles
  - condition: Melioidosis
  - condition: Mpox
  - condition: Paralytic poliomyelitis
  - condition: Poliovirus infection, nonparalytic
  - condition: Rabies, animal
    qualifier: specific import/variant/reservoir criteria
  - condition: Rabies, human
  - condition: Rubella
  - condition: Viral hemorrhagic fevers
    qualifier: all suspected/confirmed cases other than suspected intentional
```

## TIER: 7-day (Routinely notifiable)

The large majority of notifiable conditions. **Any confirmed/probable notifiable
condition NOT in the two lists above defaults here.** Representative examples (not exhaustive):

```yaml
tier_7_day_examples:
  - Anaplasmosis
  - Arboviral diseases (West Nile, EEE, La Crosse, Powassan, etc.)
  - Babesiosis
  - Campylobacteriosis
  - Chlamydia trachomatis infection
  - Coccidioidomycosis
  - Cryptosporidiosis
  - Dengue virus infections
  - Escherichia coli, Shiga toxin-producing (STEC)
  - Giardiasis
  - Gonorrhea
  - Haemophilus influenzae, invasive
  - Hepatitis A, acute
  - Hepatitis B (acute, chronic, perinatal)
  - Hepatitis C (acute, chronic, perinatal)
  - HIV infection
  - Invasive pneumococcal disease
  - Legionellosis
  - Listeriosis
  - Lyme disease
  - Malaria
  - Meningococcal disease
  - Mumps
  - Pertussis
  - Q Fever
  - Salmonellosis
  - Shigellosis
  - Streptococcal toxic-shock syndrome
  - Syphilis (all stages incl. congenital)
  - Tuberculosis
  - Varicella
  - Vibriosis / cholera
  - Yellow Fever
  - Zika virus disease
```

---

## Decision rule for the engine

```
IF condition matches a tier_4_hour entry (and its qualifier)   -> tier = "4-hour"
ELIF condition matches a tier_24_hour entry                    -> tier = "24-hour"
ELIF condition is a confirmed/probable notifiable condition    -> tier = "7-day"
ELSE (not a notifiable condition)                              -> not a triage target;
                                                                  surface for human review
THEN assign urgency_score (1-10) within the tier using the
     literature-derived prioritization factors (see separate rubric doc).
```

## Notes / caveats

- Local/state requirements may differ from this federal list and may set different
  timeframes. This file uses the national CSTE/CDC list as the citable baseline; the
  CDA-vs-FHIR and jurisdiction-variation assumptions are acknowledged openly in the project.
- Qualifiers matter: anthrax and several others appear in MORE THAN ONE tier depending
  on circumstances (e.g. bioterrorism vs. naturally-occurring). The engine should
  consider the qualifier, not just the condition name.
- "All cases prior to classification" means the case is notifiable even before it's
  confirmed vs. probable — relevant for suspected high-consequence conditions.
