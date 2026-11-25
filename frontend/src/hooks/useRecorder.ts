import { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { request } from "../services/api";
import type { Ticket, Transcript } from "../types";
import { config } from "../config/env";
type Status =
  | "idle"
  | "connecting"
  | "recording"
  | "paused"
  | "stopping"
  | "saved"
  | "error";
export function useRecorder() {
  const { token } = useAuth();
  const [status, setStatus] = useState<Status>("idle");
  const [text, setText] = useState("");
  const [language, setLanguage] = useState("auto");
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState("");
  const [record, setRecord] = useState<Transcript | null>(null);
  const resources = useRef<{
    socket?: WebSocket;
    stream?: MediaStream;
    context?: AudioContext;
    node?: AudioWorkletNode;
    analyser?: AnalyserNode;
  }>({});
  const sentSamples = useRef(0);
  const active = useRef(true);
  const statusRef = useRef<Status>("idle");
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const transition = (value: Status) => {
    statusRef.current = value;
    if (active.current) setStatus(value);
  };
  function releaseAudio() {
    const r = resources.current;
    r.stream?.getTracks().forEach((track) => track.stop());
    r.node?.disconnect();
    void r.context?.close().catch(() => {});
    r.stream = undefined;
    r.context = undefined;
    r.node = undefined;
    r.analyser = undefined;
  }
  function cleanup() {
    clearTimeout(timer.current);
    releaseAudio();
    const ws = resources.current.socket;
    if (ws) {
      ws.onclose = null;
      ws.onerror = null;
      ws.onmessage = null;
      ws.close();
    }
    resources.current.socket = undefined;
  }
  function fail(message: string) {
    if (active.current) {
      setError(message);
      transition("error");
    }
    cleanup();
  }
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      cleanup();
    };
  }, []);
  function sendStop() {
    releaseAudio();
    resources.current.socket?.send(JSON.stringify({ type: "stop" }));
    clearTimeout(timer.current);
    timer.current = setTimeout(
      () =>
        fail(
          "Finalization timed out. Check history before saving a recovery copy.",
        ),
      300000,
    );
  }
  function stop() {
    if (!["recording", "paused"].includes(statusRef.current)) return;
    transition("stopping");
    resources.current.node?.port.postMessage("stop");
  }
  async function start(title: string) {
    if (
      ["connecting", "recording", "paused", "stopping"].includes(
        statusRef.current,
      )
    )
      return;
    cleanup();
    transition("connecting");
    setError("");
    setText("");
    setRecord(null);
    setLanguage("auto");
    setSeconds(0);
    sentSamples.current = 0;
    try {
      if (!navigator.mediaDevices?.getUserMedia)
        throw new Error("Microphone access requires HTTPS or localhost.");
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      if (!active.current) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      resources.current.stream = stream;
      const context = new AudioContext({ sampleRate: 16000 });
      resources.current.context = context;
      if (context.sampleRate !== 16000)
        throw new Error(
          "This browser does not support 16 kHz capture. Please upload an audio file.",
        );
      await context.audioWorklet.addModule("/pcm-worklet.js");
      const ticket = await request<Ticket>("/auth/ticket", token, {
        method: "POST",
      });
      if (!active.current) {
        cleanup();
        return;
      }
      const ws = new WebSocket(ticket.websocket_url || config.ws);
      resources.current.socket = ws;
      let finalized = false;
      timer.current = setTimeout(() => {
        if (statusRef.current === "connecting")
          fail("Worker connection timed out");
      }, 15000);
      ws.onopen = () =>
        ws.send(JSON.stringify({ type: "auth", ticket: ticket.ticket, title }));
      ws.onerror = () => fail("Could not connect to the transcription worker.");
      ws.onclose = () => {
        if (!finalized && active.current && statusRef.current !== "error")
          fail(
            "Connection closed before confirmation. Check history; your partial text is available to copy or save.",
          );
      };
      ws.onmessage = async (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "ready") {
            clearTimeout(timer.current);
            const source = context.createMediaStreamSource(stream);
            const node = new AudioWorkletNode(context, "pcm-capture");
            const analyser = context.createAnalyser();
            analyser.fftSize = 256;
            resources.current.node = node;
            resources.current.analyser = analyser;
            const silent = context.createGain();
            silent.gain.value = 0;
            source.connect(analyser);
            source.connect(node);
            node.connect(silent);
            silent.connect(context.destination);
            node.port.onmessage = (e) => {
              if (ws.readyState !== WebSocket.OPEN) return;
              if (e.data === "stop") {
                sendStop();
                return;
              }
              if (e.data === "pause") {
                ws.send(JSON.stringify({ type: "pause" }));
                return;
              }
              if (e.data === "resume") {
                ws.send(JSON.stringify({ type: "resume" }));
                return;
              }
              if (
                !["recording", "stopping", "paused"].includes(statusRef.current)
              )
                return;
              if (ws.bufferedAmount > 32000 * 5) {
                fail(
                  "The worker cannot keep up. Try a faster worker or a smaller model.",
                );
                return;
              }
              const remaining =
                message.max_duration * 16000 - sentSamples.current;
              if (remaining <= 0) {
                stop();
                return;
              }
              const frame = (e.data as ArrayBuffer).slice(0, remaining * 2);
              sentSamples.current += frame.byteLength / 2;
              setSeconds(sentSamples.current / 16000);
              ws.send(frame);
              if (sentSamples.current >= message.max_duration * 16000) stop();
            };
            await context.resume();
            transition("recording");
          } else if (message.type === "partial") {
            setText(message.text);
            setLanguage(message.language);
          } else if (message.type === "final") {
            finalized = true;
            clearTimeout(timer.current);
            setText(message.text);
            setLanguage(message.language);
            setRecord(message.record);
            transition("saved");
            releaseAudio();
          } else if (message.type === "error") {
            if (message.text) setText(message.text);
            fail(message.message);
          }
        } catch {
          fail("Invalid response from the transcription worker.");
        }
      };
    } catch (e) {
      fail(
        (e as Error).name === "NotAllowedError"
          ? "Microphone permission denied. Allow microphone access in browser settings."
          : (e as Error).message,
      );
    }
  }
  function pause() {
    const paused = statusRef.current === "paused";
    resources.current.node?.port.postMessage(paused ? "resume" : "pause");
    transition(paused ? "recording" : "paused");
  }
  function clear() {
    cleanup();
    setText("");
    setRecord(null);
    setSeconds(0);
    setError("");
    setLanguage("auto");
    transition("idle");
  }
  function acceptRecord(value: Transcript) {
    setRecord(value);
    setText(value.text);
    setLanguage(value.language);
    setSeconds(value.duration);
    transition("saved");
  }
  return {
    status,
    text,
    language,
    seconds,
    error,
    record,
    resources,
    start,
    pause,
    stop,
    clear,
    acceptRecord,
  };
}
