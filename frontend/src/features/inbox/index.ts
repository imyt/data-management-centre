/**
 * Public contract for Inbox feature module.
 * Other modules and routing layers MUST only import through this barrel.
 */

// Pages
export { InboxPage } from "./pages/inbox-page";

// Components
export { GovernanceInbox } from "./components/GovernanceInbox";

// UI Store
export { useInboxUiStore } from "./stores/inbox.store";
export type { IInboxUiState } from "./stores/inbox.store";

// Types
export * from "./types";

