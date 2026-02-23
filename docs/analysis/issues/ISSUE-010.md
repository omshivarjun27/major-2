---
id: ISSUE-010
title: Duplicate Type Definitions Across shared/schemas and core/vqa/api_schema
severity: medium
source_artifact: architecture_risks.md
architecture_layer: cross-cutting
---

## Description
`Priority`, `Direction`, `BoundingBox`, `Detection`, and `ObstacleRecord` are defined in both `shared/schemas/__init__.py` (as dataclasses) and `core/vqa/api_schema.py` (as Pydantic models). The two hierarchies use slightly different names (`Priority` vs `PriorityLevel`, `Direction` vs `DirectionType`) and different field formats (`BoundingBox(x1,y1,x2,y2)` vs `BoundingBoxSchema(x,y,width,height)`).

## Root Cause
API schemas were created separately from domain models to support Pydantic v2 validation and OpenAPI generation. No unification strategy was established.

## Impact
- Serialization mismatches when converting between internal and API representations
- Confusion about which type to import for a given use case
- Extra conversion code and mapping functions required
- Risk of divergence as features are added to one hierarchy but not the other

## Reproducibility
always

## Remediation Plan
1. Designate `shared/schemas` dataclasses as the canonical internal types.
2. Use `core/vqa/api_schema.py` Pydantic models only for API boundary serialization.
3. Add explicit `from_domain()` / `to_domain()` converters on Pydantic models.
4. Document the canonical type source in `shared/schemas/__init__.py`.
5. Remove any direct construction of API schema types in domain logic.

## Implementation Suggestion
```python
# core/vqa/api_schema.py
class ObstacleSchema(BaseModel):
    ...
    @classmethod
    def from_domain(cls, record: ObstacleRecord) -> "ObstacleSchema":
        return cls(
            id=record.id,
            class_name=record.class_name,
            distance_m=record.distance_m,
            ...
        )
```

## GPU Impact
N/A

## Cloud Impact
N/A

## Acceptance Criteria
- [ ] Single canonical source of truth for each domain type documented
- [ ] API schema types have explicit `from_domain()` converters
- [ ] No domain logic directly constructs API schema types
- [ ] All existing tests pass after unification
