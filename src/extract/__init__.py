"""Critical-field extraction (SPEC 8.2, 8.4; RF01; Phase 2).

Division of labor (SPEC 7.1):
- The model reads one document at a time and proposes mentions: field key, the text exactly as
  printed, page and location.
- Deterministic code does the rest: it rejects any mention whose text is not on the cited page
  (no value without a source, no invented value), normalizes values by type, and sets each
  field's status across documents from rules/ (pending, missing, not_applicable, contradictory).
- verified is set only by a human and stale only when a newer version supersedes a value
  (status.py); extraction never sets either.
"""
