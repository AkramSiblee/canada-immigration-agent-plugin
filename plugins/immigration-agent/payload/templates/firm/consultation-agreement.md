# Consultation Agreement
Date: {date}

## 1. Who this agreement is between
@covers 23(2)(a) 23(2)(b)
**Consultant:** {firm.name}, Regulated Canadian Immigration Consultant, licence no. {firm.rcic}
@if firm.business
**Business:** {firm.business}
@endif
Address: {firm.address}  |  Telephone: {firm.phone}  |  Email: {firm.email}

**You:** {client.name}
Address: {client.address}
@if client.phone
Telephone: {client.phone}
@endif
@if client.email
Email: {client.email}
@endif

## 2. Purpose and scope of the consultation
@covers 23(2)(e)
{terms.consultation_purpose}
This consultation is general advice based on the information you give. It is not an agreement to provide further services. Any further services need a separate written service agreement.

## 3. Fee
@covers 23(2)(c)
{terms.consultation_fee}

## 4. The College
@covers 23(2)(d)
The Consultant is licensed and regulated by the College of Immigration and Citizenship Consultants, which licenses immigration and citizenship consultants in Canada, sets the Code of Professional Conduct, and handles complaints about licensees. Information is at college-ic.ca.

## 5. Confidentiality
The Consultant will keep what you share confidential, as the Code of Professional Conduct requires.
{firm.confidentiality}

@if firm.technology_notice
## 6. Use of technology
{firm.technology_notice}

@endif
## Signatures
Each of us keeps a signed copy of this agreement.
@signatures
