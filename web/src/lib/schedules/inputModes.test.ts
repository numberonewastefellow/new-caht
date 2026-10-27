import {
  DEFAULT_LIST_MESSAGE,
  DEFAULT_WINDOW_MESSAGE,
  defaultMessageFor,
  hasItemPlaceholder,
  inputSummary,
  isCustomMessage,
  parseItems,
  validateInputs,
} from "@/lib/schedules/inputModes";

describe("defaultMessageFor", () => {
  it("never invents a request for fixed mode", () => {
    expect(defaultMessageFor("fixed")).toBe("");
    expect(defaultMessageFor("fixed", null)).toBe("");
    expect(defaultMessageFor("fixed", "  Summarise today  ")).toBe(
      "Summarise today"
    );
  });
  it("uses the window / list defaults", () => {
    expect(defaultMessageFor("window")).toBe(DEFAULT_WINDOW_MESSAGE);
    expect(defaultMessageFor("list")).toBe(DEFAULT_LIST_MESSAGE);
    expect(defaultMessageFor("ask")).toBe("");
  });
});

describe("isCustomMessage", () => {
  it("detects edits of the defaults", () => {
    expect(isCustomMessage("window", DEFAULT_WINDOW_MESSAGE)).toBe(false);
    expect(isCustomMessage("window", "Digest since {{window_start}}")).toBe(
      true
    );
    expect(isCustomMessage("list", "{{item}}")).toBe(false);
    expect(isCustomMessage("list", "Guidance on {{item}}")).toBe(true);
  });
});

describe("parseItems", () => {
  it("splits lines and drops blanks", () => {
    expect(parseItems(" asthma \r\n\n diabetes\n")).toEqual([
      "asthma",
      "diabetes",
    ]);
    expect(parseItems("")).toEqual([]);
  });
});

describe("validateInputs", () => {
  it("requires a request in fixed mode", () => {
    expect(validateInputs("fixed", "  ", "")).toMatch(/request/);
    expect(
      validateInputs("fixed", "what is the use of paracetamol?", "")
    ).toBeNull();
  });
  it("accepts window and ask without a message", () => {
    expect(validateInputs("window", "", "")).toBeNull();
    expect(validateInputs("ask", "", "")).toBeNull();
  });
  it("checks list items and the {{item}} placeholder", () => {
    expect(validateInputs("list", "{{item}}", "\n ")).toMatch(
      /at least one item/
    );
    expect(validateInputs("list", "no placeholder", "a")).toMatch(
      /\{\{item\}\}/
    );
    expect(validateInputs("list", "Guidance on {{ item }}", "a\nb")).toBeNull();
    expect(validateInputs("list", "", "a")).toBeNull(); // falls back to {{item}}
  });
  it("detects the placeholder with spaces", () => {
    expect(hasItemPlaceholder("x {{ item }} y")).toBe(true);
    expect(hasItemPlaceholder("x {{items}}")).toBe(false);
  });
});

describe("inputSummary", () => {
  const base = {
    input_message: "Q?",
    input_prompt: null,
    input_items: null,
    workflow_name: "W",
  };
  it("summarises each mode", () => {
    expect(inputSummary({ ...base, input_mode: "fixed" })).toBe("Q?");
    expect(inputSummary({ ...base, input_mode: "ask" })).toMatch(/Asks you/);
    expect(
      inputSummary({ ...base, input_mode: "ask", input_prompt: "Paste notes" })
    ).toBe("Paste notes");
    expect(
      inputSummary({
        ...base,
        input_mode: "list",
        input_message: "{{item}}",
        input_items: ["a", "b"],
      })
    ).toBe("2 items · {{item}}");
  });
});
