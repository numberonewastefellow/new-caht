import { useEffect, useMemo } from "react";
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

// Helper function to construct current Python execution state
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
  const stdout = pythonDeltas
    .map((delta) => delta?.stdout || "")
    .filter((s) => s)
    .join("");
  const stderr = pythonDeltas
    .map((delta) => delta?.stderr || "")
    .filter((s) => s)
    .join("");
  const fileIds = pythonDeltas.flatMap((delta) => delta?.file_ids || []);

  // Collect enriched file metadata (with fallback to bare file_ids)
  const files: PythonToolFile[] = pythonDeltas.flatMap(
    (delta) => delta?.files || []
  );

  const isExecuting = pythonStart && !pythonEnd;
  const isComplete = pythonStart && pythonEnd;
  const hasError = stderr.length > 0;

  return {
    code,
    stdout,
    stderr,
    fileIds,
    files,
    isExecuting,
    isComplete,
    hasError,
  };
}

export const PythonToolRenderer: MessageRenderer<PythonToolPacket, {}> = ({
  packets,
  onComplete,
  renderType,
  children,
}) => {
  const {
    code,
    stdout,
    stderr,
    fileIds,
    files,
    isExecuting,
    isComplete,
    hasError,
  } = constructCurrentPythonState(packets);

  // Separate image files from non-image files
  const imageFiles = useMemo(
    () => files.filter((f) => isImageFile(f.filename)),
    [files]
  );
  const nonImageFiles = useMemo(
    () => files.filter((f) => !isImageFile(f.filename)),
    [files]
  );
  // Fallback: if we have file_ids but no enriched files, show count
  const hasOnlyBareFileIds = fileIds.length > 0 && files.length === 0;

  useEffect(() => {
    if (isComplete) {
      onComplete();
    }
  }, [isComplete, onComplete]);

  const status = useMemo(() => {
    if (isExecuting) {
      return "Executing Python code...";
    }
    if (hasError) {
      return "Python execution failed";
    }
    if (isComplete) {
      return "Python execution completed";
    }
    return "Python execution";
  }, [isComplete, isExecuting, hasError]);

  // Shared content for all states - used by both FULL and compact modes
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
          <span>Running code...</span>
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

      {/* Output */}
      {stdout && (
        <div className="rounded-md bg-background-neutral-02 p-3">
          <div className="text-xs font-semibold mb-1 text-text-03">Output:</div>
          <pre className="text-sm whitespace-pre-wrap font-mono text-text-01">
            {stdout}
          </pre>
        </div>
      )}

      {/* Error */}
      {stderr && (
        <div className="rounded-md bg-status-error-01 p-3 border border-status-error-02">
          <div className="text-xs font-semibold mb-1 text-status-error-05">
            Error:
          </div>
          <pre className="text-sm whitespace-pre-wrap font-mono text-status-error-05">
            {stderr}
          </pre>
        </div>
      )}

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
      {isComplete && !stdout && !stderr && files.length === 0 && (
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
