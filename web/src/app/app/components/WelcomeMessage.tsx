"use client";

import Logo from "@/refresh-components/Logo";
import {
  getRandomGreeting,
  GREETING_MESSAGES,
} from "@/lib/chat/greetingMessages";
import AgentAvatar from "@/refresh-components/avatars/AgentAvatar";
import Text from "@/refresh-components/texts/Text";
import { MinimalAgentSnapshot } from "@/app/admin/assistants/interfaces";
import { useState, useEffect } from "react";
import { useSettingsContext } from "@/providers/SettingsProvider";
import FrostedDiv from "@/refresh-components/FrostedDiv";
import { motion } from "motion/react";

export interface WelcomeMessageProps {
  agent?: MinimalAgentSnapshot;
  isDefaultAgent: boolean;
}

export default function WelcomeMessage({
  agent,
  isDefaultAgent,
}: WelcomeMessageProps) {
  const settings = useSettingsContext();
  const enterpriseSettings = settings?.enterpriseSettings;

  // Use a stable default for SSR, then randomize on client after hydration
  const [greeting, setGreeting] = useState(GREETING_MESSAGES[0]);

  useEffect(() => {
    if (enterpriseSettings?.custom_greeting_message) {
      setGreeting(enterpriseSettings.custom_greeting_message);
    } else {
      setGreeting(getRandomGreeting());
    }
  }, [enterpriseSettings?.custom_greeting_message]);

  let content: React.ReactNode = null;

  if (isDefaultAgent) {
    content = (
      <motion.div
        data-testid="onyx-logo"
        className="flex flex-col items-center gap-3"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: "easeOut" }}
      >
        <Logo folded size={56} />
        <Text as="p" headingH1 className="virtualai-gradient-text text-center">
          {greeting}
        </Text>
        <Text as="p" mainContentMuted text03 className="text-center">
          Ask anything. I&apos;m here to help.
        </Text>
      </motion.div>
    );
  } else if (agent) {
    content = (
      <motion.div
        data-testid="assistant-name-display"
        className="flex flex-col items-center gap-3"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: "easeOut" }}
      >
        <AgentAvatar agent={agent} size={48} />
        <Text as="p" headingH2 className="text-center">
          {agent.name}
        </Text>
        {agent.description && (
          <Text as="p" mainContentMuted text03 className="text-center max-w-md">
            {agent.description}
          </Text>
        )}
      </motion.div>
    );
  }

  // if we aren't using the default agent, we need to wait for the agent info to load
  // before rendering
  if (!content) return null;

  return (
    <FrostedDiv
      data-testid="chat-intro"
      className="flex flex-col items-center justify-center gap-4 w-full max-w-[var(--app-page-main-content-width)]"
    >
      {content}
    </FrostedDiv>
  );
}
