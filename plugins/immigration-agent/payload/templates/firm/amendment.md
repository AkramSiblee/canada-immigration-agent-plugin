# Amendment to Service Agreement
Date: {date}  |  File: {case.id}
Client: {client.name}

## What is changing
@covers 24(5)
This amends the service agreement dated {terms.original_date} between {firm.name} and {client.name}. Everything else in that agreement stays the same.
- {terms.changes}

## Why
{terms.reason}

@if terms.new_fee_estimate
## Fees and disbursements
@covers 31(3)
The fees or disbursements will be more than the original estimate, or a new disbursement has arisen. New estimate: {terms.new_fee_estimate}
By signing, you agree to this before the additional work or cost is incurred.

@endif
## Signatures
Both of us must agree to this amendment in writing. Each of us keeps a signed copy.
@signatures
