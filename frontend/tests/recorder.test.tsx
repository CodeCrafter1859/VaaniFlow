import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AuthProvider } from "../src/context/AuthProvider";
import { useRecorder } from "../src/hooks/useRecorder";

afterEach(() => vi.unstubAllGlobals());

it("reports microphone denial and releases the recording state", async () => {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: vi
        .fn()
        .mockRejectedValue(new DOMException("Denied", "NotAllowedError")),
    },
  });
  const { result } = renderHook(() => useRecorder(), { wrapper: AuthProvider });
  await act(async () => {
    await result.current.start("Test");
  });
  expect(result.current.status).toBe("error");
  expect(result.current.error).toContain("permission denied");
});

it("flushes audio before stop, waits for saved final, and cleans up tracks", async () => {
  const stopTrack = vi.fn();
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: vi
        .fn()
        .mockResolvedValue({ getTracks: () => [{ stop: stopTrack }] }),
    },
  });
  const connect = vi.fn();
  class Context {
    sampleRate = 16000;
    destination = {};
    audioWorklet = { addModule: vi.fn().mockResolvedValue(undefined) };
    createMediaStreamSource() {
      return { connect };
    }
    createAnalyser() {
      return { fftSize: 256 };
    }
    createGain() {
      return { connect, gain: { value: 1 } };
    }
    resume = vi.fn().mockResolvedValue(undefined);
    close = vi.fn().mockResolvedValue(undefined);
  }
  class Node {
    static current: Node;
    port: {
      onmessage: ((event: { data: unknown }) => void) | null;
      postMessage: ReturnType<typeof vi.fn>;
    } = { onmessage: null, postMessage: vi.fn() };
    constructor() {
      Node.current = this;
    }
    connect = connect;
    disconnect = vi.fn();
  }
  class Socket {
    static OPEN = 1;
    static current: Socket;
    readyState = 1;
    bufferedAmount = 0;
    onopen: (() => void) | null = null;
    onmessage: ((event: { data: string }) => Promise<void>) | null = null;
    onerror = null;
    onclose = null;
    send = vi.fn();
    close = vi.fn();
    constructor() {
      Socket.current = this;
    }
  }
  vi.stubGlobal("AudioContext", Context);
  vi.stubGlobal("AudioWorkletNode", Node);
  vi.stubGlobal("WebSocket", Socket);
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      '{"data":{"ticket":"test-ticket","websocket_url":"ws://localhost:8001/ws/transcribe"}}',
    ),
  );
  const { result, unmount } = renderHook(() => useRecorder(), {
    wrapper: AuthProvider,
  });
  await act(async () => {
    await result.current.start("Test");
  });
  act(() => Socket.current.onopen?.());
  await act(async () => {
    await Socket.current.onmessage?.({
      data: '{"type":"ready","max_duration":300}',
    });
  });
  expect(result.current.status).toBe("recording");
  act(() => result.current.pause());
  expect(result.current.status).toBe("paused");
  act(() => Node.current.port.onmessage?.({ data: "pause" }));
  act(() => result.current.pause());
  expect(result.current.status).toBe("recording");
  expect(
    Socket.current.send.mock.calls.some(
      (call) => call[0] === '{"type":"resume"}',
    ),
  ).toBe(false);
  act(() => Node.current.port.onmessage?.({ data: "resume" }));
  expect(Socket.current.send.mock.calls.at(-1)?.[0]).toBe('{"type":"resume"}');
  act(() => result.current.stop());
  expect(result.current.status).toBe("stopping");
  expect(
    Socket.current.send.mock.calls.some(
      (call) => call[0] === '{"type":"stop"}',
    ),
  ).toBe(false);
  act(() => {
    Node.current.port.onmessage?.({ data: new ArrayBuffer(200) });
    Node.current.port.onmessage?.({ data: "stop" });
  });
  expect(Socket.current.send.mock.calls.at(-1)?.[0]).toBe('{"type":"stop"}');
  expect(stopTrack).toHaveBeenCalled();
  expect(result.current.record).toBeNull();
  await act(async () => {
    await Socket.current.onmessage?.({
      data: '{"type":"final","text":"नमस्ते","language":"hi","record":{"id":"saved"}}',
    });
  });
  await waitFor(() => expect(result.current.status).toBe("saved"));
  expect(result.current.text).toBe("नमस्ते");
  unmount();
  expect(Socket.current.close).toHaveBeenCalled();
});
