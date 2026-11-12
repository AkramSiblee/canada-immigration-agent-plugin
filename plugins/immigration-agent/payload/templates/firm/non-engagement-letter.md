# We Are Not Representing You
Date: {date}

{client.name}
{client.address}

Dear {client.name},

Thank you for contacting us about {terms.matter}. We are writing to confirm that we will **not** be representing you in this matter.
@if terms.reason
{terms.reason}
@endif

We have not filed anything for you and we are not acting for you. Strict time limits may apply to your situation{?terms.deadline_note}. Please get advice from another licensed representative promptly so you don't miss a deadline.

@if terms.documents_returned
We have returned these documents to you:
- {terms.documents_returned}
@endif

Sincerely,

{firm.name}
Regulated Canadian Immigration Consultant, licence no. {firm.rcic}
