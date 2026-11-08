# DRF serializers for all API responses

**Status:** Accepted — migrated from DEC-002 (`docs/decisions.md`, Dec 2025), archived under `docs/archive/decisions.md`.

**Context:** Views originally returned hand-built dicts. This made it hard
to validate response shape and easy to introduce inconsistencies.

**Decision:** BOMWarningSerializer, FlatBOMItemSerializer, and
FlatBOMResponseSerializer wrap every API response.

**Alternatives considered:** Keep raw dicts, use Pydantic, use dataclasses.

**Why this way:** DRF serializers are the Django-native pattern, give
automatic validation/coercion, and generate browsable API docs. Found 2
bugs during the serializer migration, proving the value immediately.
