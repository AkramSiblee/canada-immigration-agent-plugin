# Consultation Notes
Date of consultation: {terms.meeting_date}  |  File: {?case.id}

Client: {client.name}
How held: {terms.method}  |  Present: {terms.attendees}
Source of these notes: {terms.source}

## Client's goals
- {terms.goals}

## Facts the client gave
- {terms.facts}

## Advice given
- {terms.advice}

@if terms.options
## Options discussed
- {terms.options}

@endif
@if terms.risks
## Risk flags
- {terms.risks}

@endif
@if terms.documents_requested
## Documents requested
- {terms.documents_requested}

@endif
@if terms.next_steps
## Next steps
- {terms.next_steps}

@endif
@if terms.fees_discussed
## Fees discussed
{terms.fees_discussed}

@endif
@covers NOTES-DRAFT
Draft prepared with AI from {terms.source}. Reviewed and corrected by the consultant before filing. The consultant's own professional judgment governs.
