export const config = {
  name: import.meta.env.VITE_APP_NAME || "Speech to Text",
  api: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1",
  ws: import.meta.env.VITE_WS_URL || "ws://localhost:8001/ws/transcribe",
};
