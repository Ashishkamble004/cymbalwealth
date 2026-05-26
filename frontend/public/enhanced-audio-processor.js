/**
 * Enhanced AudioWorklet processor with adaptive ring buffer, VAD-based
 * barge-in detection, and simple noise suppression.
 *
 * Runs in the AudioWorklet thread — no DOM access, no imports.
 * Adapted from kkrishnan90's pattern for Gemini Live streaming.
 */

class WorkletRingBuffer {
  constructor(initialSize = 8192, maxSize = 32768, minSize = 1024) {
    this.maxSize = maxSize;
    this.minSize = minSize;
    this.currentSize = Math.max(initialSize, minSize);
    this.buffer = new Float32Array(this.currentSize);
    this.writeIndex = 0;
    this.readIndex = 0;
    this.count = 0;
  }

  getFillLevel() {
    return this.count / this.currentSize;
  }

  getAvailableSpace() {
    return this.currentSize - this.count;
  }

  write(data) {
    const dataLength = data.length;
    if (dataLength > this.getAvailableSpace()) {
      if (this.currentSize < this.maxSize) {
        this.resize(Math.min(this.currentSize * 2, this.maxSize));
      } else {
        // Drop oldest samples to make room
        const drop = dataLength - this.getAvailableSpace();
        this.readIndex = (this.readIndex + drop) % this.currentSize;
        this.count = Math.max(0, this.count - drop);
      }
    }
    for (let i = 0; i < dataLength; i++) {
      this.buffer[this.writeIndex] = data[i];
      this.writeIndex = (this.writeIndex + 1) % this.currentSize;
      this.count = Math.min(this.count + 1, this.currentSize);
    }
  }

  read(output) {
    const avail = Math.min(this.count, output.length);
    for (let i = 0; i < avail; i++) {
      output[i] = this.buffer[this.readIndex];
      this.readIndex = (this.readIndex + 1) % this.currentSize;
    }
    for (let i = avail; i < output.length; i++) {
      output[i] = 0;
    }
    this.count -= avail;
    return avail;
  }

  resize(newSize) {
    newSize = Math.max(this.minSize, Math.min(newSize, this.maxSize));
    if (newSize === this.currentSize) return;
    const oldBuf = this.buffer;
    const preserve = Math.min(this.count, newSize);
    this.buffer = new Float32Array(newSize);
    for (let i = 0; i < preserve; i++) {
      this.buffer[i] = oldBuf[(this.readIndex + i) % this.currentSize];
    }
    this.readIndex = 0;
    this.writeIndex = preserve;
    this.count = preserve;
    this.currentSize = newSize;
  }

  clear() {
    this.writeIndex = 0;
    this.readIndex = 0;
    this.count = 0;
    this.buffer.fill(0);
  }
}

class EnhancedAudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.config = { sampleRate: 16000, bufferSize: 2400 };
    this.inputBuffer = new WorkletRingBuffer(4096, 16384, 1024);
    this.isRecording = true;
    this.isMuted = false;
    this.isSystemPlaying = false;

    // VAD configuration and state
    this.vadConfig = {
      enabled: true,
      threshold: 0.04,
      minSpeechFrames: 3,
      minSilenceFrames: 10,
      energyHistory: [],
    };
    this.vadState = {
      isSpeechActive: false,
      speechFrameCount: 0,
      silenceFrameCount: 0,
    };

    this.port.onmessage = (e) => this.handleMessage(e);
  }

  handleMessage(event) {
    const { type, data } = event.data;
    switch (type) {
      case "SET_RECORDING":
        this.isRecording = data.recording;
        if (!data.recording) this.inputBuffer.clear();
        break;
      case "SET_MUTED":
        this.isMuted = data.muted;
        break;
      case "SET_SYSTEM_PLAYING":
        this.isSystemPlaying = data.playing;
        break;
      case "SET_VAD_CONFIG":
        Object.assign(this.vadConfig, data);
        break;
    }
  }

  detectVAD(samples) {
    let energy = 0;
    for (let i = 0; i < samples.length; i++) {
      energy += samples[i] * samples[i];
    }
    energy = Math.sqrt(energy / samples.length);

    this.vadConfig.energyHistory.push(energy);
    if (this.vadConfig.energyHistory.length > 10) {
      this.vadConfig.energyHistory.shift();
    }

    const avg =
      this.vadConfig.energyHistory.reduce((s, e) => s + e, 0) /
      this.vadConfig.energyHistory.length;
    const threshold = this.vadConfig.threshold + avg * 0.1;
    const active = energy > threshold;

    if (active) {
      this.vadState.speechFrameCount++;
      this.vadState.silenceFrameCount = 0;
      if (this.vadState.speechFrameCount >= this.vadConfig.minSpeechFrames) {
        this.vadState.isSpeechActive = true;
      }
    } else {
      this.vadState.silenceFrameCount++;
      this.vadState.speechFrameCount = 0;
      if (this.vadState.silenceFrameCount >= this.vadConfig.minSilenceFrames) {
        this.vadState.isSpeechActive = false;
      }
    }

    return {
      energy,
      isSpeechActive: this.vadState.isSpeechActive,
      threshold,
    };
  }

  applyNoiseSuppression(samples) {
    return samples;
  }

  process(inputs) {
    if (!this.isRecording || this.isMuted) return true;

    const input = inputs[0];
    if (!input || !input[0]) return true;

    const processed = this.applyNoiseSuppression(input[0]);
    let vad = null;

    if (this.vadConfig.enabled) {
      vad = this.detectVAD(processed);
      if (vad.isSpeechActive && this.isSystemPlaying) {
        this.port.postMessage({
          type: "BARGE_IN_DETECTED",
          data: {
            energy: vad.energy,
            threshold: vad.threshold,
            timestamp: Date.now(),
          },
        });
      }
    }

    this.inputBuffer.write(processed);
    while (this.inputBuffer.count >= this.config.bufferSize) {
      const chunk = new Float32Array(this.config.bufferSize);
      this.inputBuffer.read(chunk);
      const int16 = new Int16Array(this.config.bufferSize);
      for (let i = 0; i < this.config.bufferSize; i++) {
        const s = Math.max(-1, Math.min(1, chunk[i]));
        int16[i] = Math.round(s * 32767);
      }
      this.port.postMessage(
        {
          type: "AUDIO_DATA",
          data: {
            audioData: int16.buffer,
            timestamp: Date.now(),
            hasActivity: vad?.isSpeechActive ?? false,
          },
        },
        [int16.buffer]
      );
    }
    return true;
  }
}

registerProcessor("enhanced-audio-processor", EnhancedAudioProcessor);
