"use client";

import { createContext, useContext } from "react";

export interface CodeExecutionContextType {
  chatSessionId: string;
  /** The user message node ID that is the parent of this assistant message */
  parentNodeId: number | null;
  /** The backend message ID of the parent user message */
  parentMessageId: number | undefined;
  /** Callback to insert execution result as a sibling message in the tree */
  onCodeExecutionResult: (result: {
    messageId: number;
    parentMessageId: number;
    content: string;
    files: Array<{ id: string; type: string; name?: string }>;
  }) => void;
}

export const CodeExecutionContext =
  createContext<CodeExecutionContextType | null>(null);

export function useCodeExecution() {
  return useContext(CodeExecutionContext);
}
