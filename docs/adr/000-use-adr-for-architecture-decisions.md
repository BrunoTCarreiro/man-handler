# ADR 000: Use Architecture Decision Records

**Status:** Accepted  
**Date:** 2025-01-07  
**Deciders:** Bruno  

---

## Context and Problem Statement

As the home manual assistant project grows, architectural decisions need to be documented for future reference and to help onboard new contributors.

---

## Decision

We will use Architecture Decision Records (ADRs) as described by Michael Nygard to document significant architectural decisions.

ADRs will be:
* Stored in `docs/adr/`
* Numbered sequentially (000, 001, 002, ...)
* Written in Markdown
* Immutable once accepted (new ADRs supersede old ones, rather than editing)

---

## Consequences

### Positive
* Decisions are documented with context
* Future team members understand *why* choices were made
* Easy to revisit decisions when requirements change
* Creates a historical record of the project's evolution

### Negative
* Requires discipline to document decisions
* Takes time to write ADRs
* Old ADRs may become outdated but remain in history

---

## References

* [Michael Nygard's ADR article](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)



