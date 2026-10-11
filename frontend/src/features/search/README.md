# Global Search & Command Palette Module (`@/features/search`)

## Ownership
The Search module owns:
- Global Cmd+K / Ctrl+K keyboard palette orchestration
- Fast indexing and jump navigation across catalog assets, glossaries, domains, and quick actions
- Direct delegation to catalog deep-links and creation modals

## State Boundary
- **Client State**: `useSearchUiStore` manages dialog visibility (`isOpen`), search string (`query`), and keyboard toggle actions.

## Public Barrel Contract
Import only from `@/features/search`.
