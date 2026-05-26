/**
 * Enhanced audio processor with AudioWorklet support and ScriptProcessor fallback.
 * Provides VAD-based barge-in detection, noise suppression via the worklet,
 * and a uniform event-emitter interface for the hook layer.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AudioProcessorOptions {
  sampleRate?: number;
  bufferSize?: number;
  vadEnabled?: boolean;
  vadThreshold?: number;
}

export interface BargeInEvent {
  energy: number;
  threshold: number;
  timestamp: number;
}

type AudioProcessorEvent = "audioData" | "bargeInDetected" | "error" | "fatalError";
type EventHandler = (...args: unknown[]) => void;

export interface AudioProcessor {
  start(stream: MediaStream): void;
  stop(): void;
  pause(): void;
  unpause(): void;
  destroy(): void;
  updateConfig(config: { isMuted?: boolean; vadEnabled?: boolean }): void;
  setSystemPlaying(playing: boolean): void;
  on(event: AudioProcessorEvent, handler: EventHandler): void;
  off(event: AudioProcessorEvent, handler: EventHandler): void;
}

// ---------------------------------------------------------------------------
// EventEmitter mixin
// ---------------------------------------------------------------------------

class EventEmitterMixin {
  private _listeners: Map<string, Set<EventHandler>> = new Map();

  on(event: string, handler: EventHandler): void {
    if (!this._listeners.has(event)) {
      this._listeners.set(event, new Set());
    }
    this._listeners.get(event)!.add(handler);
  }

  off(event: string, handler: EventHandler): void {
    this._listeners.get(event)?.delete(handler);
  }

  protected emitEvent(event: string, ...args: unknown[]): void {
    this._listeners.get(event)?.forEach((fn) => {
      try {
        fn(...args);
      } catch (e) {
        console.error(`[AudioProcessor] Error in ${event} handler:`, e);
      }
    });
  }
}

// ---------------------------------------------------------------------------
// AudioWorklet wrapper
// ---------------------------------------------------------------------------

class AudioWorkletWrapper extends EventEmitterMixin implements AudioProcessor {
  private audioContext: AudioContext;
  private workletNode: AudioWorkletNode | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private isPaused = false;

  constructor(audioContext: AudioContext) {
    super();
    this.audioContext = audioContext;
  }

  async init(): Promise<void> {
    // Load the worklet module from the public directory
    await this.audioContext.audioWorklet.addModule("/enhanced-audio-processor.js");
  }

  start(stream: MediaStream): void {
    try {
      this.sourceNode = this.audioContext.createMediaStreamSource(stream);
      this.workletNode = new AudioWorkletNode(
        this.audioContext,
        "enhanced-audio-processor"
      );

      this.workletNode.port.onmessage = (event) => {
        const { type, data } = event.data;
        switch (type) {
          case "AUDIO_DATA":
            // data.audioData is an ArrayBuffer of Int16
            this.emitEvent("audioData", data.audioData as ArrayBuffer);
            break;
          case "BARGE_IN_DETECTED":
            this.emitEvent("bargeInDetected", data as BargeInEvent);
            break;
        }
      };

      this.sourceNode.connect(this.workletNode);
      // Connect to destination so the worklet process() keeps firing
      this.workletNode.connect(this.audioContext.destination);
    } catch (err) {
      this.emitEvent("error", err);
    }
  }

  stop(): void {
    this.workletNode?.port.postMessage({
      type: "SET_RECORDING",
      data: { recording: false },
    });
  }

  pause(): void {
    this.isPaused = true;
    this.workletNode?.port.postMessage({
      type: "SET_MUTED",
      data: { muted: true },
    });
  }

  unpause(): void {
    this.isPaused = false;
    this.workletNode?.port.postMessage({
      type: "SET_MUTED",
      data: { muted: false },
    });
  }

  destroy(): void {
    this.stop();
    if (this.workletNode) {
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }
  }

  updateConfig(config: { isMuted?: boolean; vadEnabled?: boolean }): void {
    if (config.isMuted !== undefined) {
      this.workletNode?.port.postMessage({
        type: "SET_MUTED",
        data: { muted: config.isMuted },
      });
    }
    if (config.vadEnabled !== undefined) {
      this.workletNode?.port.postMessage({
        type: "SET_VAD_CONFIG",
        data: { enabled: config.vadEnabled },
      });
    }
  }

  setSystemPlaying(playing: boolean): void {
    this.workletNode?.port.postMessage({
      type: "SET_SYSTEM_PLAYING",
      data: { playing },
    });
  }
}

// ---------------------------------------------------------------------------
// ScriptProcessor fallback (for browsers without AudioWorklet)
// ---------------------------------------------------------------------------

class ScriptProcessorFallback extends EventEmitterMixin implements AudioProcessor {
  private audioContext: AudioContext;
  private scriptNode: ScriptProcessorNode | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private isMuted = false;
  private isPaused = false;
  private isSystemPlaying = false;
  private vadEnabled: boolean;
  private vadThreshold: number;
  private bufferSize: number;

  // VAD state
  private energyHistory: number[] = [];
  private speechFrameCount = 0;
  private silenceFrameCount = 0;
  private isSpeechActive = false;

  constructor(
    audioContext: AudioContext,
    options: AudioProcessorOptions = {}
  ) {
    super();
    this.audioContext = audioContext;
    this.vadEnabled = options.vadEnabled ?? true;
    this.vadThreshold = options.vadThreshold ?? 0.04;
    this.bufferSize = options.bufferSize ?? 4096;
  }

  start(stream: MediaStream): void {
    try {
      this.sourceNode = this.audioContext.createMediaStreamSource(stream);
      this.scriptNode = this.audioContext.createScriptProcessor(
        this.bufferSize,
        1,
        1
      );

      this.scriptNode.onaudioprocess = (event) => {
        if (this.isMuted || this.isPaused) return;

        const input = event.inputBuffer.getChannelData(0);
        const processed = input;

        // VAD
        if (this.vadEnabled) {
          let energy = 0;
          for (let i = 0; i < processed.length; i++) {
            energy += processed[i] * processed[i];
          }
          energy = Math.sqrt(energy / processed.length);
          this.energyHistory.push(energy);
          if (this.energyHistory.length > 10) this.energyHistory.shift();
          const avg =
            this.energyHistory.reduce((s, e) => s + e, 0) /
            this.energyHistory.length;
          const threshold = this.vadThreshold + avg * 0.1;
          const active = energy > threshold;

          if (active) {
            this.speechFrameCount++;
            this.silenceFrameCount = 0;
            if (this.speechFrameCount >= 3) this.isSpeechActive = true;
          } else {
            this.silenceFrameCount++;
            this.speechFrameCount = 0;
            if (this.silenceFrameCount >= 10) this.isSpeechActive = false;
          }

          if (this.isSpeechActive && this.isSystemPlaying) {
            this.emitEvent("bargeInDetected", {
              energy,
              threshold,
              timestamp: Date.now(),
            } as BargeInEvent);
          }
        }

        // Convert to Int16 and emit
        const int16 = new Int16Array(processed.length);
        for (let i = 0; i < processed.length; i++) {
          const s = Math.max(-1, Math.min(1, processed[i]));
          int16[i] = Math.round(s * 32767);
        }
        this.emitEvent("audioData", int16.buffer);
      };

      this.sourceNode.connect(this.scriptNode);
      this.scriptNode.connect(this.audioContext.destination);
    } catch (err) {
      this.emitEvent("error", err);
    }
  }

  stop(): void {
    if (this.scriptNode) {
      this.scriptNode.onaudioprocess = null;
    }
  }

  pause(): void {
    this.isPaused = true;
  }

  unpause(): void {
    this.isPaused = false;
  }

  destroy(): void {
    this.stop();
    if (this.scriptNode) {
      this.scriptNode.disconnect();
      this.scriptNode = null;
    }
    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }
  }

  updateConfig(config: { isMuted?: boolean; vadEnabled?: boolean }): void {
    if (config.isMuted !== undefined) this.isMuted = config.isMuted;
    if (config.vadEnabled !== undefined) this.vadEnabled = config.vadEnabled;
  }

  setSystemPlaying(playing: boolean): void {
    this.isSystemPlaying = playing;
  }
}

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

/**
 * Create an audio processor, preferring AudioWorklet with ScriptProcessor fallback.
 * Returns a uniform interface regardless of which implementation is used.
 */
export async function createAudioProcessor(
  audioContext: AudioContext,
  options: AudioProcessorOptions = {}
): Promise<AudioProcessor> {
  // Try AudioWorklet first
  if (typeof AudioWorkletNode !== "undefined" && audioContext.audioWorklet) {
    try {
      const wrapper = new AudioWorkletWrapper(audioContext);
      await wrapper.init();
      console.log("[AudioProcessor] Using AudioWorklet (enhanced-audio-processor)");
      return wrapper;
    } catch (err) {
      console.warn(
        "[AudioProcessor] AudioWorklet failed, falling back to ScriptProcessor:",
        err
      );
    }
  }

  // Fallback to ScriptProcessor
  console.log("[AudioProcessor] Using ScriptProcessor fallback");
  return new ScriptProcessorFallback(audioContext, options);
}
