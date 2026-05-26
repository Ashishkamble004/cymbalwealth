/** Connection states for the WebSocket. */
export enum ConnectionState {
  DISCONNECTED = "disconnected",
  CONNECTING = "connecting",
  CONNECTED = "connected",
  ERROR = "error",
}

/** A chat transcript message. */
export interface ChatMessage {
  id: string;
  role: "user" | "agent";
  text: string;
  timestamp: Date;
  source?: "text" | "transcription";
}

/** KYC verification step status. */
export interface VerificationStep {
  id: string;
  label: string;
  status: "pending" | "in-progress" | "verified" | "failed";
}

/** WebSocket message from server. */
export interface ServerMessage {
  type: "audio" | "transcript" | "input_transcription" | "output_transcription" | "pong" | "interrupted" | "turn_complete";
  data?: string;
  mime_type?: string;
  role?: string;
  text?: string;
  finished?: boolean;
  response_id?: number;
}

/** WebSocket message to server. */
export interface ClientMessage {
  type: "audio" | "video" | "text" | "context" | "end_session" | "ping";
  data?: string;
  reference_number?: string;
}
