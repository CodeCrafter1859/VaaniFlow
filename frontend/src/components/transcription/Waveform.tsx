import { useEffect, useRef } from "react";
export function Waveform({
  analyser,
  recording,
}: {
  analyser?: AnalyserNode;
  recording: boolean;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    let id = 0;
    const data = new Uint8Array(128);
    function draw() {
      const ctx = canvas.current?.getContext("2d");
      if (!ctx) return;
      ctx.clearRect(0, 0, 800, 100);
      if (analyser && recording) analyser.getByteFrequencyData(data);
      else data.fill(0);
      for (let i = 0; i < 64; i++) {
        const height = Math.max(4, (data[i] / 255) * 85);
        ctx.fillStyle = recording ? "#7860e8" : "#cbc4e5";
        ctx.beginPath();
        ctx.roundRect(i * 12.5 + 3, 50 - height / 2, 5, height, 3);
        ctx.fill();
      }
      id = requestAnimationFrame(draw);
    }
    draw();
    return () => cancelAnimationFrame(id);
  }, [analyser, recording]);
  return (
    <canvas
      ref={canvas}
      width={800}
      height={100}
      className="waveform"
      aria-label={
        recording ? "Live microphone audio levels" : "Microphone inactive"
      }
    />
  );
}
