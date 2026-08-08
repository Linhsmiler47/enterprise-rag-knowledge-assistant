# Incident Response Policy

## Declaring an incident

Any engineer may declare an incident when a production system is degraded or unavailable for
users. Declaring an incident is always the safe default -- it is far cheaper to stand down a
false alarm than to delay response to a real outage. An incident is declared by posting in the
incident channel and paging the relevant on-call rotation.

## Severity levels

Severity 1 means a full outage of a customer-facing system with no workaround. Severity 2 means
significant degradation or a partial outage with a workaround available. Severity 3 means a minor
issue affecting a small subset of users or an internal-only system. Severity level determines the
response time expectation and whether a status page update is required.

## During an incident

The first responder's job is to mitigate impact, not to find the root cause. Mitigation (rollback,
scaling, feature-flag disable) takes priority over investigation. A dedicated incident commander
is assigned for any Severity 1 or Severity 2 incident to coordinate response and communication,
separate from whoever is actively debugging.

## After an incident

Every Severity 1 and Severity 2 incident requires a blameless postmortem within five business
days, documenting the timeline, root cause, impact, and concrete follow-up action items with
owners. The postmortem is not considered complete until every action item has an owner and a
due date.
