import {
  RefObject,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  PacketType,
  PythonToolPacket,
  PythonToolStart,
  PythonToolDelta,
  PythonToolFile,
  SectionEnd,
} from "@/app/app/services/streamingModels";
import {
  MessageRenderer,
  RenderType,
} from "@/app/app/message/messageComponents/interfaces";
import { CodeBlock } from "@/app/app/message/CodeBlock";
import hljs from "highlight.js/lib/core";
import python from "highlight.js/lib/languages/python";
import { SvgTerminal } from "@opal/icons";
import FadingEdgeContainer from "@/refresh-components/FadingEdgeContainer";
import { InMessageImage } from "@/app/app/components/files/images/InMessageImage";
import { buildImgUrl } from "@/app/app/components/files/images/utils";

// Register Python language for highlighting
hljs.registerLanguage("python", python);

// Component to render syntax-highlighted Python code
function HighlightedPythonCode({ code }: { code: string }) {
  const highlightedHtml = useMemo(() => {
    try {
      return hljs.highlight(code, { language: "python" }).value;
    } catch {
      return code;
    }
  }, [code]);

  return (
    <span
      dangerouslySetInnerHTML={{ __html: highlightedHtml }}
      className="hljs"
    />
  );
}

const IMAGE_EXTENSIONS = new Set([
  ".png",
  ".jpg",
  ".jpeg",
  ".gif",
  ".svg",
  ".webp",
]);

function isImageFile(filename: string): boolean {
  const ext = filename.slice(filename.lastIndexOf(".")).toLowerCase();
  return IMAGE_EXTENSIONS.has(ext);
}

// One self-heal attempt's accumulated streams. Deltas are split into attempts at
// `reset` boundaries so a failed attempt's output/traceback never mixes with the
// successful retry.
interface Attempt {
  stdout: string;
  stderr: string;
}

// A delta is "terminal" when it carries execution result metadata (exit_code is a
// real number, or it timed out, or it reports a duration). Streamed chunk deltas
// leave these at their null/false defaults, so this reliably finds the final frame.
function isTerminalDelta(d: PythonToolDelta): boolean {
  return (
    (d.exit_code !== undefined && d.exit_code !== null) ||
    d.timed_out === true ||
    (d.duration_ms !== undefined && d.duration_ms !== null)
  );
}

function constructCurrentPythonState(packets: PythonToolPacket[]) {
  const pythonStart = packets.find(
    (packet) => packet.obj.type === PacketType.PYTHON_TOOL_START
  )?.obj as PythonToolStart | null;
  const pythonDeltas = packets
    .filter((packet) => packet.obj.type === PacketType.PYTHON_TOOL_DELTA)
    .map((packet) => packet.obj as PythonToolDelta);
  const pythonEnd = packets.find(
    (packet) =>
      packet.obj.type === PacketType.SECTION_END ||
      packet.obj.type === PacketType.ERROR
  )?.obj as SectionEnd | null;

  const code = pythonStart?.code || "";

  // Fold deltas into attempts (split at self-heal `reset` boundaries) and find the
  // single terminal delta (which drives status/elapsed, not stderr presence).
  const attempts: Attempt[] = [{ stdout: "", stderr: "" }];
  let terminal: PythonToolDelta | null = null;
  for (const d of pythonDeltas) {
    if (d.reset) {
      // Any text on the reset delta describes the OUTGOING (failing) attempt, so
      // append it there before starting the fresh pane for the retry.
      const cur = attempts[attempts.length - 1]!;
      cur.stdout += d.stdout || "";
      cur.stderr += d.stderr || "";
      attempts.push({ stdout: "", stderr: "" });
    } else {
      const seg = attempts[attempts.length - 1]!;
      seg.stdout += d.stdout || "";
      seg.stderr += d.stderr || "";
    }
    if (isTerminalDelta(d)) {
      terminal = d;
    }
  }
  const current = attempts[attempts.length - 1]!;
  const archivedAttempts = attempts.slice(0, -1);

  const fileIds = pythonDeltas.flatMap((delta) => delta?.file_ids || []);
  const files: PythonToolFile[] = pythonDeltas.flatMap(
    (delta) => delta?.files || []
  );

  const isExecuting = Boolean(pythonStart) && !pythonEnd && !terminal;
  const isComplete = Boolean(pythonStart) && Boolean(pythonEnd);

  // Outcome is driven by the terminal delta's exit_code / timed_out / error_kind —
  // NEVER by stderr presence (tqdm, logging, and warnings all write to stderr on a
  // perfectly successful run).
  const succeeded = terminal ? terminal.exit_code === 0 : false;
  const failed = terminal ? !succeeded : false;
  const timedOut = terminal?.timed_out === true;
  const errorKind = terminal?.error_kind ?? null;
  const durationMs = terminal?.duration_ms ?? null;

  return {
    code,
    current,
    archivedAttempts,
    fileIds,
    files,
    isExecuting,
    isComplete,
    hasTerminal: Boolean(terminal),
    succeeded,
    failed,
    timedOut,
    errorKind,
    durationMs,
  };
}

// Monospace output pane. stderr is tinted as an error only when the run actually
// failed; on a successful run stderr is shown muted (secondary), not red.
function OutputPane({
  stdout,
  stderr,
  failed,
  scrollRef,
}: {
  stdout: string;
  stderr: string;
  failed: boolean;
  scrollRef?: RefObject<HTMLDivElement | null>;
}) {
  if (!stdout && !stderr) return null;
  return (
    <div
      ref={scrollRef}
      className="rounded-md bg-background-neutral-02 p-3 max-h-[420px] overflow-y-auto"
    >
      {stdout && (
        <pre className="text-sm whitespace-pre-wrap font-mono text-text-01">
          {stdout}
        </pre>
      )}
      {stderr && (
        <pre
          className={`text-sm whitespace-pre-wrap font-mono ${
            failed ? "text-status-error-05" : "text-text-03"
          }`}
        >
          {stderr}
        </pre>
      )}
    </div>
  );
}

export const PythonToolRenderer: MessageRenderer<PythonToolPacket, {}> = ({
  packets,
  onComplete,
  renderType,
  children,
}) => {
  const {
    code,
    current,
    archivedAttempts,
    fileIds,
    files,
    isExecuting,
    isComplete,
    succeeded,
    failed,
    timedOut,
    errorKind,
    durationMs,
  } = useMemo(() => constructCurrentPythonState(packets), [packets]);

  // Separate image files from non-image files
  const imageFiles = useMemo(
    () => files.filter((f) => isImageFile(f.filename)),
    [files]
  );
  const nonImageFiles = useMemo(
    () => files.filter((f) => !isImageFile(f.filename)),
    [files]
  );
  const hasOnlyBareFileIds = fileIds.length > 0 && files.length === 0;

  useEffect(() => {
    if (isComplete) {
      onComplete();
    }
  }, [isComplete, onComplete]);

  // --- Live elapsed timer (per-card, shown after ~2s while executing) ---
  const startedAtRef = useRef<number | null>(null);
  const [elapsedS, setElapsedS] = useState(0);
  useEffect(() => {
    if (isExecuting && startedAtRef.current === null) {
      startedAtRef.current = Date.now();
    }
    if (!isExecuting) return;
    const id = setInterval(() => {
      if (startedAtRef.current !== null) {
        setElapsedS(Math.floor((Date.now() - startedAtRef.current) / 1000));
      }
    }, 1000);
    return () => clearInterval(id);
  }, [isExecuting]);

  // --- Sticky autoscroll of the live output pane while streaming ---
  const liveScrollRef = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const el = liveScrollRef.current;
    if (!el || !isExecuting) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    if (nearBottom) {
      el.scrollTop = el.scrollHeight;
    }
  }, [current.stdout, current.stderr, isExecuting]);

  const status = useMemo(() => {
    if (isExecuting) {
      return elapsedS >= 2 ? `Running code… ${elapsedS}s` : "Running code…";
    }
    if (timedOut) return "Timed out";
    if (errorKind === "oom") return "Ran out of memory";
    if (errorKind === "kernel_died") return "Kernel crashed";
    if (failed) return "Failed";
    if (succeeded) {
      return durationMs != null
        ? `Analyzed · ${(durationMs / 1000).toFixed(1)}s`
        : "Analyzed";
    }
    if (isComplete) return "Python execution completed";
    return "Python execution";
  }, [
    isExecuting,
    elapsedS,
    timedOut,
    errorKind,
    failed,
    succeeded,
    durationMs,
    isComplete,
  ]);

  const content = (
    <div className="flex flex-col mb-1 space-y-2">
      {/* Loading indicator when executing */}
      {isExecuting && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <div className="flex gap-0.5">
            <div className="w-1 h-1 bg-current rounded-full animate-pulse"></div>
            <div
              className="w-1 h-1 bg-current rounded-full animate-pulse"
              style={{ animationDelay: "0.1s" }}
            ></div>
            <div
              className="w-1 h-1 bg-current rounded-full animate-pulse"
              style={{ animationDelay: "0.2s" }}
            ></div>
          </div>
          <span>Running code…</span>
        </div>
      )}

      {/* Code block */}
      {code && (
        <div className="prose max-w-full">
          <CodeBlock className="language-python" codeText={code.trim()}>
            <HighlightedPythonCode code={code.trim()} />
          </CodeBlock>
        </div>
      )}

      {/* Superseded self-heal attempts (collapsed) */}
      {archivedAttempts.map((att, i) => (
        <details
          key={i}
          className="rounded-md bg-background-neutral-02 px-3 py-2"
        >
          <summary className="text-xs font-semibold text-text-03 cursor-pointer">
            Attempt {i + 1} (failed) — click to expand
          </summary>
          <div className="mt-2">
            <OutputPane stdout={att.stdout} stderr={att.stderr} failed />
          </div>
        </details>
      ))}

      {/* Live / final output for the current attempt */}
      <OutputPane
        stdout={current.stdout}
        stderr={current.stderr}
        failed={failed}
        scrollRef={liveScrollRef}
      />

      {/* Generated images — rendered inline */}
      {imageFiles.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-1">
          {imageFiles.map((file) => (
            <div key={file.file_id} className="transition-all group">
              <InMessageImage fileId={file.file_id} shape="landscape" />
              <div className="text-xs text-text-04 mt-1 truncate">
                {file.filename}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Non-image files — download links */}
      {nonImageFiles.length > 0 && (
        <div className="flex flex-col gap-1">
          {nonImageFiles.map((file) => (
            <a
              key={file.file_id}
              href={buildImgUrl(file.file_id)}
              download={file.filename}
              className="text-sm text-theme-primary-05 hover:underline truncate"
            >
              {file.filename}
            </a>
          ))}
        </div>
      )}

      {/* Fallback for bare file_ids without enriched metadata */}
      {hasOnlyBareFileIds && (
        <div className="text-sm text-text-03">
          Generated {fileIds.length} file{fileIds.length !== 1 ? "s" : ""}
        </div>
      )}

      {/* No output fallback - only when complete with no output */}
      {isComplete &&
        !current.stdout &&
        !current.stderr &&
        files.length === 0 && (
          <div className="py-2 text-center text-text-04">
            <SvgTerminal className="w-4 h-4 mx-auto mb-1 opacity-50" />
            <p className="text-xs">No output</p>
          </div>
        )}
    </div>
  );

  // FULL mode: render content directly
  if (renderType === RenderType.FULL) {
    return children([
      {
        icon: SvgTerminal,
        status,
        content,
        supportsCollapsible: true,
      },
    ]);
  }

  // Compact mode: wrap content in FadeDiv
  return children([
    {
      icon: SvgTerminal,
      status,
      supportsCollapsible: true,
      content: (
        <FadingEdgeContainer
          direction="bottom"
          className="max-h-24 overflow-hidden"
        >
          {content}
        </FadingEdgeContainer>
      ),
    },
  ]);
};
