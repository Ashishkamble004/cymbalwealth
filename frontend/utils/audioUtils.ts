/** Audio utility functions for PCM encoding/decoding with WebSocket. */

/**
 * Encode a Float32Array of PCM samples to a base64 string of 16-bit PCM.
 */
export function encodeAudioToBase64(float32Array: Float32Array): string {
  const int16Array = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  const bytes = new Uint8Array(int16Array.buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

/**
 * Decode a base64 string of 16-bit PCM to a Float32Array.
 */
export function decodeBase64ToAudio(base64: string): Float32Array {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  const int16Array = new Int16Array(bytes.buffer);
  const float32Array = new Float32Array(int16Array.length);
  for (let i = 0; i < int16Array.length; i++) {
    float32Array[i] = int16Array[i] / (int16Array[i] < 0 ? 0x8000 : 0x7fff);
  }
  return float32Array;
}

/**
 * Create an AudioBuffer from a Float32Array at the given sample rate.
 */
export function createAudioBuffer(
  audioContext: AudioContext,
  float32Array: Float32Array,
  sampleRate: number
): AudioBuffer {
  const audioBuffer = audioContext.createBuffer(1, float32Array.length, sampleRate);
  audioBuffer.getChannelData(0).set(float32Array);
  return audioBuffer;
}

/**
 * Resample audio from one sample rate to another using linear interpolation.
 */
export function resampleAudio(
  input: Float32Array,
  inputRate: number,
  outputRate: number
): Float32Array {
  if (inputRate === outputRate) return input;
  const ratio = inputRate / outputRate;
  const outputLength = Math.round(input.length / ratio);
  const output = new Float32Array(outputLength);
  for (let i = 0; i < outputLength; i++) {
    const srcIndex = i * ratio;
    const srcFloor = Math.floor(srcIndex);
    const srcCeil = Math.min(srcFloor + 1, input.length - 1);
    const frac = srcIndex - srcFloor;
    output[i] = input[srcFloor] * (1 - frac) + input[srcCeil] * frac;
  }
  return output;
}

/**
 * AudioWorklet processor code for capturing microphone PCM audio.
 * Returns the code as a string to be loaded via Blob URL.
 */
export function getPCMProcessorCode(): string {
  return `
class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = [];
    this._bufferSize = 2400; // 150ms at 16kHz
  }

  process(inputs) {
    const input = inputs[0];
    if (input && input[0]) {
      const channelData = input[0];
      for (let i = 0; i < channelData.length; i++) {
        this._buffer.push(channelData[i]);
      }
      while (this._buffer.length >= this._bufferSize) {
        const chunk = this._buffer.splice(0, this._bufferSize);
        this.port.postMessage({ pcmData: new Float32Array(chunk) });
      }
    }
    return true;
  }
}

registerProcessor('pcm-processor', PCMProcessor);
`;
}
