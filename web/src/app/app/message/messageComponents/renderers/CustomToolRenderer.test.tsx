/**
 * Tests for MCP tool-execution error display.
 *
 * MCP reports tool failures in-band: the call returns normally and the result
 * carries `isError: true` with the error message as ordinary content. The
 * backend forwards that as `is_error` on the tool payload. Without it the UI
 * rendered a rejected call exactly like a successful one -- a `docx_create_document`
 * that the server had rejected still showed "completed".
 */
import React from "react";
import { render } from "@testing-library/react";

import CustomToolRenderer from "./CustomToolRenderer";
import { RenderType, RendererOutput, RendererResult } from "../interfaces";
import { PacketType } from "../../../services/streamingModels";

function renderTool(data: Record<string, unknown>): RendererResult {
  let captured: RendererOutput = [];

  const packets = [
    {
      ind: 0,
      obj: {
        type: PacketType.CUSTOM_TOOL_START,
        tool_name: "docx_create_document",
      },
    },
    {
      ind: 0,
      obj: {
        type: PacketType.CUSTOM_TOOL_DELTA,
        tool_name: "docx_create_document",
        response_type: "json",
        data,
      },
    },
    { ind: 0, obj: { type: PacketType.SECTION_END } },
  ] as never;

  render(
    <CustomToolRenderer
      packets={packets}
      state={{}}
      onComplete={() => {}}
      renderType={RenderType.FULL}
      animate={false}
      stopPacketSeen={false}
    >
      {(result) => {
        captured = result;
        return <></>;
      }}
    </CustomToolRenderer>
  );

  // Narrow away `undefined` for the callers: every render path in this
  // component returns exactly one result, so a different count is a bug in
  // the component rather than something the assertions should tolerate.
  expect(captured).toHaveLength(1);
  return captured[0] as RendererResult;
}

describe("CustomToolRenderer MCP error state", () => {
  it("reports a successful call as completed", () => {
    const result = renderTool({ tool_result: "Document created" });

    expect(result.status).toBe("docx_create_document completed");
  });

  it("reports a failed call as failed, not completed", () => {
    const result = renderTool({
      tool_result: "Invalid arguments: author must be a string",
      is_error: true,
    });

    expect(result.status).toBe("docx_create_document failed");
  });

  it("uses a distinct icon for a failed call", () => {
    const ok = renderTool({ tool_result: "fine" });
    const failed = renderTool({ tool_result: "bad", is_error: true });

    expect(failed.icon).not.toBe(ok.icon);
  });

  it("treats a missing is_error as success", () => {
    const result = renderTool({ tool_result: "no flag present" });

    expect(result.status).toBe("docx_create_document completed");
  });

  it("treats is_error:false as success", () => {
    const result = renderTool({ tool_result: "ok", is_error: false });

    expect(result.status).toBe("docx_create_document completed");
  });
});
