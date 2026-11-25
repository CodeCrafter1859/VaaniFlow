import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "../src/App";
const record = {
  id: "1",
  title: "Hindi meeting",
  text: "नमस्ते hello",
  language: "hi",
  duration: 12,
  status: "completed",
  created_at: "2026-01-01T10:00:00Z",
  updated_at: "2026-01-01T10:00:00Z",
};
function mockServer() {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, options) => {
      const url = String(input);
      let data: unknown = {};
      if (url.endsWith("/auth/me")) data = { name: "Alice" };
      else if (url.endsWith("/dashboard/stats"))
        data = {
          total: 1,
          completed: 1,
          failed: 0,
          duration: 12,
          languages: [{ language: "hi", count: 1 }],
        };
      else if (options?.method === "DELETE") data = { deleted: true };
      else if (options?.method === "PATCH")
        data = { ...record, ...JSON.parse(options.body as string) };
      else data = { items: [record], total: 1, page: 1, page_size: 10 };
      return new Response(JSON.stringify({ data }));
    });
}
async function login() {
  fireEvent.change(screen.getByLabelText("Access token"), {
    target: { value: "test-token" },
  });
  fireEvent.click(screen.getByText("Open workspace"));
  await screen.findByText(/Welcome back, Alice/);
}
describe("workspace flows", () => {
  it("authenticates, displays real API statistics and edits history", async () => {
    window.history.replaceState({}, "", "/");
    const fetch = mockServer();
    render(<App />);
    await login();
    expect(await screen.findByText("Hindi meeting")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Transcription history"));
    fireEvent.click(await screen.findByLabelText("Edit Hindi meeting"));
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Updated meeting" },
    });
    fireEvent.click(screen.getByText("Save changes"));
    await waitFor(() =>
      expect(
        fetch.mock.calls.some(
          (call) =>
            call[1]?.method === "PATCH" &&
            String(call[1]?.body).includes("Updated meeting"),
        ),
      ).toBe(true),
    );
  });
  it("requires delete confirmation and supports cancellation", async () => {
    window.history.replaceState({}, "", "/");
    const fetch = mockServer();
    render(<App />);
    await login();
    fireEvent.click(screen.getByText("Transcription history"));
    fireEvent.click(await screen.findByLabelText("Delete Hindi meeting"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Cancel"));
    expect(fetch.mock.calls.some((call) => call[1]?.method === "DELETE")).toBe(
      false,
    );
    fireEvent.click(screen.getByLabelText("Delete Hindi meeting"));
    fireEvent.click(screen.getByText("Delete transcription"));
    await waitFor(() =>
      expect(
        fetch.mock.calls.some((call) => call[1]?.method === "DELETE"),
      ).toBe(true),
    );
  });
  it("shows authentication failures", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"error":{"message":"Invalid token"}}', { status: 401 }),
    );
    render(<App />);
    fireEvent.change(screen.getByLabelText("Access token"), {
      target: { value: "bad" },
    });
    fireEvent.click(screen.getByText("Open workspace"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid token");
  });
});
