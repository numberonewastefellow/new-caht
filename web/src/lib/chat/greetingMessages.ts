export const GREETING_MESSAGES = [
  "How can I help?",
  "Let's get started.",
  "What's on your mind?",
  "Ready when you are.",
  "Let's figure it out.",
  "What would you like to explore?",
];

export function getRandomGreeting(): string {
  return GREETING_MESSAGES[
    Math.floor(Math.random() * GREETING_MESSAGES.length)
  ] as string;
}
