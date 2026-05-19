# Architecture — eCR-Triage

## Overview

eCR-Triage is a three-stage pipeline:

1. **Ingest**: Pull eICR FHIR Bundles from a FHIR R4 server
2. **Triage**: Parse resources, send structured summaries to an LLM, receive priority + rationale
3. **Writeback**: Post Flag and Task resources back to the server

## Data Flow

```
[FHIR Server] --GET Bundle--> [Bundle Parser] --structured text--> [LLM Triage Engine]
                                                                          |
                                                                    priority + rationale
                                                                          |
                                                                   [Writeback Module]
                                                                          |
                                                              --POST Flag/Task--> [FHIR Server]
```

## Key Design Decisions

### Human-in-the-loop
The LLM provides a *recommendation*, not an automated action. The Flag resource
makes the priority visible in any FHIR client; the Task resource creates an
actionable work item. An investigator reviews both before acting.

### Grounded reasoning
The triage prompt includes only data extracted from FHIR resources. The LLM is
instructed to reference specific resources (e.g., "Condition: Measles, SNOMED
186747009") in its rationale, making the reasoning auditable.

### Write-back as interoperability proof
Most student FHIR apps are read-only. By writing Flag and Task resources, we
demonstrate bidirectional interoperability — the triage output is itself a
FHIR resource that other systems can consume.

## FHIR Profiles & IGs

- **US Core**: Patient, Condition, Encounter, Observation
- **eCR IG (eICR)**: Bundle composition structure
- **Base R4**: Flag, Task (no US Core profile required)
