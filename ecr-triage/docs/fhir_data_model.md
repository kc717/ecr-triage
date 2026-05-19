# FHIR Data Model — eCR-Triage

## Resources We Read (from eICR Bundles)

### Patient
- **Purpose**: Demographics for triage context (age, location)
- **Key elements**: birthDate, gender, address (city, state)
- **Profile**: US Core Patient

### Condition
- **Purpose**: The reportable condition triggering the case report
- **Key elements**: code (SNOMED CT), onsetDateTime, clinicalStatus
- **Profile**: US Core Condition
- **Example**: Measles (186747009), Tuberculosis (56717001)

### Encounter
- **Purpose**: Care setting and timing context
- **Key elements**: class (AMB/EMER/IMP), period, serviceType
- **Profile**: US Core Encounter

### Observation
- **Purpose**: Lab results and vital signs supporting triage
- **Key elements**: code (LOINC), valueQuantity, effectiveDateTime
- **Profile**: US Core Observation (Lab/Vitals)

### Immunization
- **Purpose**: Vaccination history relevant to reportable condition
- **Key elements**: vaccineCode, occurrenceDateTime, status
- **Profile**: US Core Immunization

## Resources We Write (triage output)

### Flag
- **Purpose**: Represent triage priority as a visible alert
- **Key elements**:
  - status: active
  - category: triage
  - code: priority level (urgent/high/routine/low)
  - subject: reference to Patient
  - period.start: timestamp of triage decision
  - text: LLM-generated rationale

### Task
- **Purpose**: Create an investigation work item
- **Key elements**:
  - status: requested
  - intent: order
  - priority: maps from triage output
  - focus: reference to Patient
  - description: case summary
  - note: recommended actions from LLM

## Terminology

| System | Usage |
|--------|-------|
| SNOMED CT | Condition codes |
| LOINC | Observation codes (labs, vitals) |
| CVX | Immunization vaccine codes |
| HL7 ActCode | Encounter class |
