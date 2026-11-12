# Service Agreement
Date: {date}  |  File: {case.id}

## 1. Who this agreement is between
@covers 24(3)(a) 24(3)(b)
**Consultant:** {firm.name}, Regulated Canadian Immigration Consultant, licence no. {firm.rcic}
@if firm.business
**Business:** {firm.business}
@endif
Address: {firm.address}  |  Telephone: {firm.phone}  |  Email: {firm.email}

**Client:** {client.name}
Home address: {client.address}
@if client.phone
Telephone: {client.phone}
@endif
@if client.email
Email: {client.email}
@endif
@if client.business
Business address and contact details: {client.business}
@endif

## 2. Advice given so far
@covers 24(3)(c)
{terms.preliminary_advice}

## 3. Your instructions
@covers 24(3)(f)
{terms.instructions}

## 4. Services
@covers 24(3)(g) 24(3)(h)
The Consultant will provide these services:
- {terms.services}
Estimated time frames: {terms.time_frames}
Services not listed above are not part of this agreement. Any change to this agreement must be agreed in writing by both of us.

## 5. Quality, supervision and help
@covers 24(3)(d) 24(3)(e) 24(3)(u)
The Consultant endeavours to provide quality services and will adequately supervise anyone who assists in providing them.
People likely to assist the Consultant: {terms.assistants}
The Consultant will get help when needed, including retaining an interpreter or translator.

## 6. Fees, disbursements and taxes
@covers 24(3)(i) 24(3)(j) 24(3)(k) 24(3)(l) 24(3)(n)
Professional fees: {terms.fee_estimate}
Expected disbursements, charged at actual cost:
- {terms.disbursements}
Taxes: {terms.taxes}
Payment terms: {terms.payment_terms}
Interest on unpaid amounts: {terms.interest}
Other costs you may have to pay: {terms.additional_costs}
If fees or disbursements will be more than these estimates, or a new disbursement arises, the Consultant will tell you and get your written agreement first.

## 7. Advance payments and refunds
@covers 24(3)(m)
Advance payment required: {terms.advance_payment}
Advance payments are held in trust in a client account. They are withdrawn only to pay an invoice for services already provided, or a disbursement you have approved.
Refund policy: {terms.refund_policy}

## 8. Conflicts of interest
@covers 24(3)(o)
{terms.conflicts}

## 9. Your original documents
@covers 24(3)(p)
Original documents you give the Consultant will be returned to you once the purpose for taking them has been achieved.

## 10. Confidentiality
@covers 24(3)(q)
The Consultant has a duty under the Code of Professional Conduct to keep your information confidential, during this agreement and after it ends.
{firm.confidentiality}

@if firm.technology_notice
## 11. Use of technology
@covers 24(3)(z)
{firm.technology_notice}

@endif
## 12. Language and updates
@covers 24(3)(s) 24(3)(t)
The services will be provided in {terms.service_language}.
The Consultant will give you timely information on the status of your case, including when documents are submitted or received for you.

## 13. Complaints
@covers 24(3)(r) 24(3)(v)
{firm.complaints_procedure}
The College of Immigration and Citizenship Consultants regulates immigration and citizenship consultants in Canada. It licenses consultants, sets the Code of Professional Conduct, and investigates complaints about licensees. You can make a complaint to the College at any time, whether or not you have used the Consultant's own procedure. Information is at college-ic.ca.

## 14. The College and the Code
@covers 24(3)(w) 24(3)(x)
The College may require the Consultant to produce documents, including documents in your file, under the College of Immigration and Citizenship Consultants Act and its regulations and by-laws.
You have been given a copy of the Code of Professional Conduct for College of Immigration and Citizenship Consultants Licensees.

## 15. If the Consultant cannot continue
@covers 24(3)(y)
{firm.incapacity_plan}

## 16. When this agreement ends
Within 30 days after this agreement is completed or ended early, the Consultant will return your documents and property, give you an accounting of all money received from you, send a final invoice, and refund any money held in trust that is more than the amount invoiced.

@if terms.other_terms
## 17. Other terms
@covers 24(3)(z)
{terms.other_terms}

@endif
## Signatures
Each of us keeps a signed copy of this agreement.
@signatures
