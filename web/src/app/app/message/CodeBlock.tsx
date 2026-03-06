import { cn } from "@/lib/utils";
import Text from "@/refresh-components/texts/Text";
import React, { useState, ReactNode, useCallback, useMemo, memo } from "react";
import { SvgCheck, SvgCode, SvgCopy } from "@opal/icons";
import { useCodeExecution } from "@/app/app/message/CodeExecutionContext";

const RUNNABLE_LANGUAGES = new Set(["python", "py", "python3"]);

interface CodeBlockProps {
  className?: string;
  children?: ReactNode;
  codeText: string;
}

const MemoizedCodeLine = memo(({ content }: { content: ReactNode }) => (
  <>{content}</>
));

export const CodeBlock = memo(function CodeBlock({
  className = "",
  children,
  codeText,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [running, setRunning] = useState(false);
  const execContext = useCodeExecution();

  const language = useMemo(() => {
    return className
      .split(" ")
      .filter((cls) => cls.startsWith("language-"))
      .map((cls) => cls.replace("language-", ""))
      .join(" ");
  }, [className]);

  const isRunnable =
    RUNNABLE_LANGUAGES.has(language.toLowerCase()) &&
    execContext !== null &&
    execContext.parentMessageId !== undefined;

  const handleCopy = useCallback(() => {
    if (!codeText) return;
    navigator.clipboard.writeText(codeText).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [codeText]);

  const handleRun = useCallback(async () => {
    if (!codeText || !execContext || !execContext.parentMessageId) return;
    setRunning(true);
    try {
      const resp = await fetch("/api/chat/execute-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_session_id: execContext.chatSessionId,
          parent_message_id: execContext.parentMessageId,
          code: codeText,
        }),
      });
      if (!resp.ok) {
        const errText = await resp.text();
        console.error("Execute code failed:", resp.status, errText);
        return;
      }
      const data = await resp.json();
      execContext.onCodeExecutionResult({
        messageId: data.message_id,
        parentMessageId: data.parent_message_id,
        content: buildExecutionContent(codeText, data),
        files: data.files || [],
      });
    } catch (err) {
      console.error("Execute code error:", err);
    } finally {
      setRunning(false);
    }
  }, [codeText, execContext]);

  const CopyButton = () => (
    <div
      className="cursor-pointer select-none"
      onMouseDown={handleCopy}
    >
      {copied ? (
        <div className="flex items-center space-x-2">
          <SvgCheck height={14} width={14} stroke="currentColor" />
          <Text as="p" secondaryMono>
            Copied!
          </Text>
        </div>
      ) : (
        <div className="flex items-center space-x-2">
          <SvgCopy height={14} width={14} stroke="currentColor" />
          <Text as="p" secondaryMono>
            Copy
          </Text>
        </div>
      )}
    </div>
  );

  const RunButton = () => (
    <div
      className="cursor-pointer select-none"
      onMouseDown={(e) => {
        e.preventDefault();
        if (!running) handleRun();
      }}
    >
      <div className="flex items-center space-x-2">
        {running ? (
          <>
            <div className="h-3.5 w-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
            <Text as="p" secondaryMono>
              Running...
            </Text>
          </>
        ) : (
          <>
            <svg
              height={14}
              width={14}
              viewBox="0 0 24 24"
              fill="currentColor"
              stroke="none"
            >
              <path d="M8 5v14l11-7z" />
            </svg>
            <Text as="p" secondaryMono>
              Run
            </Text>
          </>
        )}
      </div>
    </div>
  );

  if (typeof children === "string" && !language) {
    return (
      <span
        className={cn(
          "font-mono",
          "text-text-05",
          "bg-background-tint-02",
          "border",
          "border-border-01",
          "rounded",
          "text-[0.8125rem]",
          "inline",
          "whitespace-pre-wrap",
          "break-words",
          "py-0.5",
          "px-1",
          className
        )}
      >
        {children}
      </span>
    );
  }

  const CodeContent = () => {
    if (!language) {
      return (
        <pre className="!p-2 m-0 overflow-x-auto w-0 min-w-full hljs">
          <code className={`text-sm hljs ${className}`}>
            {Array.isArray(children)
              ? children.map((child, index) => (
                  <MemoizedCodeLine key={index} content={child} />
                ))
              : children}
          </code>
        </pre>
      );
    }

    return (
      <pre className="!p-2 m-0 overflow-x-auto w-0 min-w-full hljs">
        <code className="text-xs">
          {Array.isArray(children)
            ? children.map((child, index) => (
                <MemoizedCodeLine key={index} content={child} />
              ))
            : children}
        </code>
      </pre>
    );
  };

  return (
    <div className="bg-background-tint-00 px-1 pb-1 rounded-12 max-w-full min-w-0">
      {language && (
        <div className="flex items-center px-2 py-1 text-sm text-text-04 gap-x-2">
          <SvgCode
            height={12}
            width={12}
            stroke="currentColor"
            className="my-auto"
          />
          <Text secondaryMono>{language}</Text>
          <div className="ml-auto flex items-center gap-x-3">
            {isRunnable && <RunButton />}
            {codeText && <CopyButton />}
          </div>
        </div>
      )}

      <CodeContent />
    </div>
  );
});

CodeBlock.displayName = "CodeBlock";
MemoizedCodeLine.displayName = "MemoizedCodeLine";

function buildExecutionContent(
  code: string,
  data: { stdout?: string; stderr?: string; exit_code?: number; files?: any[] }
): string {
  const parts: string[] = [];
  parts.push("**Code Execution Result**\n");
  parts.push(`\`\`\`\n${code}\n\`\`\`\n`);
  if (data.stdout?.trim()) {
    parts.push(`**Output:**\n\`\`\`\n${data.stdout.trim()}\n\`\`\`\n`);
  }
  if (data.stderr?.trim()) {
    parts.push(`**Errors:**\n\`\`\`\n${data.stderr.trim()}\n\`\`\`\n`);
  }
  if (data.exit_code != null && data.exit_code !== 0) {
    parts.push(`Exit code: ${data.exit_code}\n`);
  }
  if (data.files && data.files.length > 0) {
    parts.push(`**Generated ${data.files.length} file(s)**\n`);
  }
  return parts.join("\n");
}
