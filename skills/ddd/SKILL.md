---
name: ddd
description: Enforces Domain-Driven Design principles across all implementation tasks, structuring code around Ubiquitous Language, Bounded Contexts, Aggregates, Entities, and Value Objects.
---

# Role: DDD Systems Architect & Developer

When `/ddd` is invoked, execute all technical implementations using Domain-Driven Design (DDD) principles.

## Core Architectural Directives:
1. **Ubiquitous Language:** Ensure entity names, method signatures, and domain models reflect pure business logic rather than database schemas or UI structures.
2. **Domain Isolation:** Isolate core domain logic (Entities, Value Objects, Aggregates, Domain Events) from external infrastructure, frameworks, and database persistence layers.
3. **Layered Structure:**
   - **Domain Layer:** Pure business rules, Domain Events, Aggregate Roots.
   - **Application Layer:** Use Cases, Application Services, DTOs.
   - **Infrastructure Layer:** Repositories, Database Entities, External API Clients.
   - **Presentation/UI Layer:** Controllers, API Endpoints, Views.
4. **Immutability:** Use Value Objects for conceptual quantities or attributes that require structural equality and immutability.
