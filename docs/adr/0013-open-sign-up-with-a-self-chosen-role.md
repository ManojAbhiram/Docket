# ADR-0013: Open sign up with a self-chosen role

- Status: Accepted
- Date: 2026-10-07
- Task: NOTASK-7
- Deciders: Manoj Abhiram (chose open sign up against the recommendation of invite-only)

## Context

Docket has two seeded accounts, one staff and one verifier, and no way to add people (ADR-0006, ADR-0012). The demo needs more than two users. The product is one office with no tenants. Today the data is demo data, not real student records.

## Options considered

### Option A: open sign up with a role choice
Anyone creates an account and picks staff or verifier. Smallest to build and easiest to demo. Anyone can become a verifier and approve applications, so it is only safe with demo data.

### Option B: sign up, then admin approval
New accounts wait until an admin approves them. Safer, but there is no admin role or screen, so it adds a role, a queue and a screen.

### Option C: admin invite link
An admin issues single-use links that carry the role. Closest to a real office, and it was the recommendation (invite-only). It needs the same admin role and screen as Option B, plus link storage and expiry.

## Decision

We will allow open sign up with a self-chosen role. The engineer chose this on 2026-10-07 against the recommendation of invite-only, because the data is demo data and no admin role exists to approve or invite.

## Consequences

- Easier: anyone can try the product at once, with no admin work.
- Harder: anyone can register as a verifier and approve applications (threat T-38, accepted). Mitigations that bear on escalation are few: every decision is logged with its actor, and the per-source sign up limit only slows bulk registration. Nothing stops a person choosing the verifier role. The Argon2 hash slots are a CPU and memory control for hashing, not a privilege control.
- A taken username answers 409, so usernames can be enumerated. Accepted for the same reason.
- Revisit before any real student data. Options then are an access code for the verifier role, or Option B or C once an admin role exists.
