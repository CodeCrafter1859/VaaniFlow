class PCMCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.samples = [];
    this.paused = false;
    this.port.onmessage = (event) => {
      if (event.data === "stop" || event.data === "pause") {
        this.flush();
        this.paused = true;
        this.port.postMessage(event.data);
      } else {
        this.paused = false;
        this.port.postMessage("resume");
      }
    };
  }
  flush() {
    if (this.samples.length) {
      const pcm = new Int16Array(this.samples);
      this.port.postMessage(pcm.buffer, [pcm.buffer]);
      this.samples = [];
    }
  }
  process(inputs) {
    const input = inputs[0]?.[0];
    if (input && !this.paused) {
      for (const value of input)
        this.samples.push(Math.round(Math.max(-1, Math.min(1, value)) * 32767));
      if (this.samples.length >= 4096) this.flush();
    }
    return true;
  }
}
registerProcessor("pcm-capture", PCMCapture);
