"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  createChatSession,
  sendMessage,
} from "@/app/app/services/lib";

interface TestMessage {
  role: "user" | "assistant" | "error" | "system";
  content: string;
}

export interface AgentTestTarget {
  agentId: number;
  agentName: string;
  stepName: string;
}

interface AgentTestModalProps {
  target: AgentTestTarget;
  onClose: () => void;
}

export function AgentTestModal({ target, onClose }: AgentTestModalProps) {
  const [messages, setMessages] = useState<TestMessage[]>([
    {
      role: "system",
      content: `Testing "${target.agentName}" — send a message to begin.`,
    },
  ]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const chatSessionRef = useRef<string | null>(null);
  const parentMsgRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Cleanup abort on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || streaming) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setStreaming(true);

    try {
      // Create chat session on first message
      if (!chatSessionRef.current) {
        const sessionId = await createChatSession(
          target.agentId,
          "Workflow Builder Test",
          null
        );
        chatSessionRef.current = sessionId;
      }

      const controller = new AbortController();
      abortRef.current = controller;

      // Add empty assistant message that we'll stream into
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      const stream = sendMessage({
        message: text,
        chatSessionId: chatSessionRef.current,
        parentMessageId: parentMsgRef.current,
        filters: null,
        signal: controller.signal,
      });

      for await (const packet of stream) {
        if (controller.signal.aborted) break;

        // Handle different packet shapes
        if ("obj" in packet) {
          const obj = packet.obj as any;
          if (obj.type === "message_delta" && obj.content) {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content + obj.content,
                };
              }
              return updated;
            });
          }
        }

        // Track parent message for multi-turn
        if ("message_id" in packet) {
          parentMsgRef.current = (packet as any).message_id;
        }
      }
    } catch (err: any) {
      if (err?.name === "AbortError") return;
      setMessages((prev) => [
        ...prev,
        {
          role: "error",
          content: err?.message || "An error occurred",
        },
      ]);
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }, [input, streaming, target.agentId]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setStreaming(false);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="wfb-test-overlay" onClick={onClose}>
      <div className="wfb-test-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="wfb-test-header">
          <div className="wfb-test-title">
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            Test: {target.agentName}
            {target.stepName &&
              target.stepName !== target.agentName &&
              ` (${target.stepName})`}
          </div>
          <button
            className="wfb-config-close"
            onClick={onClose}
            title="Close"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Messages */}
        <div className="wfb-test-body">
          <div className="wfb-test-messages">
            {messages.map((msg, i) => (
              <div key={i} className={`wfb-test-msg wfb-test-msg--${msg.role}`}>
                {msg.content}
                {msg.role === "assistant" &&
                  streaming &&
                  i === messages.length - 1 && (
                    <span className="wfb-test-streaming-dot" />
                  )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="wfb-test-input-row">
            <textarea
              ref={inputRef}
              className="wfb-test-input"
              placeholder="Type a message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={streaming}
            />
            {streaming ? (
              <button
                className="wfb-test-send-btn"
                onClick={handleStop}
                title="Stop"
                style={{ background: "var(--theme-red-05, #dc2626)" }}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <rect x="6" y="6" width="12" height="12" rx="2" />
                </svg>
              </button>
            ) : (
              <button
                className="wfb-test-send-btn"
                onClick={handleSend}
                disabled={!input.trim()}
                title="Send"
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
