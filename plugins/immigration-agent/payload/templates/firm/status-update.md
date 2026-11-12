# Update on Your File
Date: {date}  |  File: {case.id}

{client.name}
{?client.address}

Dear {client.name},

This is an update on your file.

## What has happened
@covers 22(3)(a)
- {terms.events}

@if terms.next_steps
## What happens next
- {terms.next_steps}

@endif
@if terms.client_actions
## What we need from you
- {terms.client_actions}

@endif
## Checking your application online
@covers 22(1)(f)
{terms.online_access}

## Copies
@covers 22(3)(b)
If you would like a copy of anything we submitted or received for you, just ask and we will send it.

Processing times are set by IRCC and can change. We will tell you as soon as we hear anything new.

Sincerely,

{firm.name}
Regulated Canadian Immigration Consultant, licence no. {firm.rcic}
