import { describe, expect, it, vi } from "vitest";
import { request } from "../src/services/api";
describe("Fetch wrapper", () => {
  it("sends authorization and returns data", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify({ data: { total: 3 } })));
    expect(await request("/dashboard/stats", "secret")).toEqual({ total: 3 });
    expect(
      new Headers(fetch.mock.calls[0][1]?.headers).get("Authorization"),
    ).toBe("Bearer secret");
  });
  it("preserves server errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: { message: "Not allowed" } }), {
        status: 401,
      }),
    );
    await expect(request("/transcriptions", "")).rejects.toThrow("Not allowed");
  });
  it("handles non-JSON failures", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("Bad gateway", { status: 502 }),
    );
    await expect(request("/transcriptions", "")).rejects.toThrow("502");
  });
  it("does not set a multipart content type", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response('{"data":{}}'));
    await request("/audio", "", { method: "POST", body: new FormData() });
    expect(
      new Headers(fetch.mock.calls[0][1]?.headers).has("Content-Type"),
    ).toBe(false);
  });
});
