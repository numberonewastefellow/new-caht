import {
  WorkflowApiError,
  describeSaveError,
  saveWorkflow,
  upgradeNodeConfig,
} from "@/lib/workflows/api";

function respond(status: number, body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    })
  );
}

describe("workflow API errors", () => {
  const fetchMock = jest.fn();
  beforeAll(() => {
    global.fetch = fetchMock as unknown as typeof fetch;
  });

  it("surfaces the server's 400 detail", async () => {
    fetchMock.mockReturnValueOnce(
      respond(400, { detail: "Step 'Route': targets an unknown step" })
    );
    const error = await saveWorkflow(3, { steps: [] }).catch((e) => e);
    expect(error).toBeInstanceOf(WorkflowApiError);
    expect(error.status).toBe(400);
    expect(describeSaveError(error)).toBe(
      "Step 'Route': targets an unknown step"
    );
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/admin/workflow/3",
      expect.objectContaining({ method: "PATCH" })
    );
  });

  it("explains a 409 version conflict", async () => {
    fetchMock.mockReturnValueOnce(respond(409, { detail: "stale" }));
    const error = await saveWorkflow(3, {
      steps: [],
      expected_version: 2,
    }).catch((e) => e);
    expect(error.isVersionConflict).toBe(true);
    expect(describeSaveError(error)).toMatch(/changed by someone else/);
  });

  it("creates when there is no id and returns the saved workflow", async () => {
    fetchMock.mockReturnValueOnce(respond(200, { id: 9, version: 1 }));
    await expect(saveWorkflow(null, { name: "x", steps: [] })).resolves.toEqual(
      {
        id: 9,
        version: 1,
      }
    );
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/admin/workflow",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("posts upgrade requests to the node type", async () => {
    fetchMock.mockReturnValueOnce(
      respond(200, { from_version: 1, to_version: 2, config: { a: 1 } })
    );
    await upgradeNodeConfig("conditional_router", {
      from_version: 1,
      config: {},
      step_order_to_node_key: { 0: "s1" },
    });
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/workflow/node-types/conditional_router/upgrade",
      expect.objectContaining({ method: "POST" })
    );
  });
});
