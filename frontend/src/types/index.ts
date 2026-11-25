export interface Transcript {
  id: string;
  title: string;
  text: string;
  language: string;
  duration: number;
  status: "completed" | "failed";
  created_at: string;
  updated_at: string;
}
export interface Page {
  items: Transcript[];
  total: number;
  page: number;
  page_size: number;
}
export interface Stats {
  total: number;
  completed: number;
  failed: number;
  duration: number;
  languages: { language: string; count: number }[];
}
export interface Ticket {
  ticket: string;
  expires_in: number;
  websocket_url: string;
  upload_url: string;
}
