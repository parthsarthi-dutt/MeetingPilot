import { API_BASE_URL } from "./client";

type WsEventCallback = (data: any) => void;

class MeetingWebSocketClient {
  private ws: WebSocket | null = null;
  private isConnecting = false;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private listeners: Map<string, Set<WsEventCallback>> = new Map();
  private joinedMeetings: Set<string> = new Set();

  private getWsUrl(): string {
    const url = new URL(API_BASE_URL);
    const protocol = url.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${url.host}/ws`;
  }

  connect() {
    if (this.ws || this.isConnecting) return;

    // We only connect if we have a token
    const token = localStorage.getItem("mp_access_token");
    if (!token) return; // Authentication is required for the WebSocket

    this.isConnecting = true;
    const wsUrl = this.getWsUrl();

    // The backend uses cookie or token-based auth for WS, but standard browser WebSocket
    // API doesn't support custom headers easily. If the backend relies on a token in the URL or relies on a cookie, we may need to adjust.
    // For now, let's assume it can connect and standard auth is handled (e.g. cookies or token as query param if needed).
    // If it requires a query param:
    this.ws = new WebSocket(`${wsUrl}?token=${token}`);

    this.ws.onopen = () => {
      this.isConnecting = false;
      // Re-join any meetings we were subscribed to
      this.joinedMeetings.forEach((meetingId) => {
        this.send({ event: "join_meeting", meeting_id: meetingId });
      });
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const eventType = data.event || data.type; // Fallback in case structure varies
        if (eventType && this.listeners.has(eventType)) {
          this.listeners.get(eventType)?.forEach((cb) => cb(data));
        }
      } catch (err) {
        console.error("Failed to parse WS message", err);
      }
    };

    this.ws.onclose = () => {
      this.ws = null;
      this.isConnecting = false;
      // Attempt reconnect after 2 seconds
      this.reconnectTimer = setTimeout(() => this.connect(), 2000);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  joinMeeting(meetingId: string) {
    this.joinedMeetings.add(meetingId);
    this.send({ event: "join_meeting", meeting_id: meetingId });
  }

  leaveMeeting(meetingId: string) {
    this.joinedMeetings.delete(meetingId);
    this.send({ event: "leave_meeting", meeting_id: meetingId });
  }

  on(eventType: string, callback: WsEventCallback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)?.add(callback);
    
    // Auto connect when a listener is added if not connected
    if (!this.ws && !this.isConnecting) {
      this.connect();
    }
  }

  off(eventType: string, callback: WsEventCallback) {
    if (this.listeners.has(eventType)) {
      this.listeners.get(eventType)?.delete(callback);
    }
  }
}

export const wsClient = new MeetingWebSocketClient();
