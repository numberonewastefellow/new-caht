/**
 * VertualAI Chat Widget - Entry Point
 * Exports the main web component
 */

import { VirtualAIChatWidget } from "./widget";

// Define the custom element
if (
  typeof customElements !== "undefined" &&
  !customElements.get("virtualai-chat-widget")
) {
  customElements.define("virtualai-chat-widget", VirtualAIChatWidget);
}

// Export for use in other modules
export { VirtualAIChatWidget };
export * from "./types/api-types";
export * from "./types/widget-types";
