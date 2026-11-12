# End of Service Agreement
Date: {date}  |  File: {case.id}

{client.name}
{client.address}

Dear {client.name},

Our service agreement has ended. {terms.outcome}

## Your documents and property
@covers 36(1)(a)
We have returned the following to you:
- {terms.documents_returned}

## Accounting of your money
@covers 36(1)(b)
- {accounting}

## Final invoice
@covers 36(1)(c)
{terms.final_invoice}

## Refund
@covers 36(1)(d)
{terms.refund}

Our retainer with you has now ended, and we no longer represent you.
@if terms.next_steps
{terms.next_steps}
@endif

We will keep your file for at least six years, as the College requires. If you have any concerns about our services, you can contact us, or the College of Immigration and Citizenship Consultants at college-ic.ca.

Sincerely,

{firm.name}
Regulated Canadian Immigration Consultant, licence no. {firm.rcic}
