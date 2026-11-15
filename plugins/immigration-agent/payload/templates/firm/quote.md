# Fee Quote
Date: {date}

{client.name}

Re: {terms.program_label}

Thank you for meeting with us. This is our quote for the services discussed.

## Services
- {terms.services}

## Our professional fees
- {terms.fee_lines}

## Government fees (paid to IRCC)
- {terms.gov_lines}

## Total
- {terms.totals}

## Payment schedule
- {terms.schedule}

## Please note
@covers QUOTE-NOTES
- Government fees are set by IRCC and can change before you apply. We confirm them on the day of filing (amounts here from IRCC's fee list as checked on {terms.fees_checked}).
- This quote is valid for {terms.valid_days} days. It is not a service agreement: we start work only after we both sign a written service agreement.
- Our fees do not depend on the result. No one can guarantee the outcome of an immigration application.
@if terms.notes
- {terms.notes}
@endif

Sincerely,

{firm.name}
Regulated Canadian Immigration Consultant, licence no. {firm.rcic}
