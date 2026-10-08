// Framework-agnostic API client.
// This connects directly to the FastAPI backend.

import type {
  Meeting,
  MeetingDetail,
  WorkflowLogEntry,
  OnboardingStatus,
  CompanyProfile,
  Settings,
  Credits,
  AdminOverview,
  AdminUserRow,
  Checklist,
} from "./types";

const API_BASE =
  typeof import.meta !== "undefined"
    ? (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000") // changed default port to 8000 as backend uses 8000 usually, but let's stick to env var if it is there
    : "http://localhost:8000";

// Swappable auth token getter. By default, reads from localStorage.
let authTokenGetter: () => Promise<string | null> = async () => {
  if (typeof window !== "undefined") {
    return localStorage.getItem("mp_access_token");
  }
  return null;
};

export function setAuthTokenGetter(fn: () => Promise<string | null>) {
  authTokenGetter = fn;
}

async function realFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await authTokenGetter();
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${await res.text().catch(() => res.statusText)}`);
  }
  if (res.status === 204) return undefined as T;
  // Handle empty bodies for 200 responses that might be empty
  const text = await res.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

// -------- Public API surface --------

export const api = {
  onboarding: {
    status: async (): Promise<OnboardingStatus> => {
      return realFetch("/api/onboarding/status");
    },
  },
  companyProfile: {
    get: async (): Promise<CompanyProfile> => {
      return realFetch("/api/company-profile");
    },
    save: async (body: CompanyProfile): Promise<void> => {
      await realFetch("/api/company-profile", { method: "POST", body: JSON.stringify(body) });
    },
  },
  meetings: {
    list: async (status?: string, page?: number): Promise<{ meetings: Meeting[]; total: number }> => {
      const params = new URLSearchParams();
      if (status) params.append("status", status);
      if (page) params.append("page", page.toString());
      const q = params.toString() ? `?${params.toString()}` : "";
      return realFetch(`/api/meetings${q}`);
    },
    detail: async (id: string): Promise<MeetingDetail> => {
      return realFetch(`/api/meetings/${id}`);
    },
    workflowLogs: async (id: string): Promise<WorkflowLogEntry[]> => {
      return realFetch(`/api/meetings/${id}/workflow-logs`);
    },
    simulate: async (body: {
      title: string; description?: string;
      start_time: string; end_time: string;
      attendees: { name: string; email: string; company?: string }[];
    }): Promise<{ meeting_id: string }> => {
      return realFetch("/api/meetings/simulate", { method: "POST", body: JSON.stringify(body) });
    },
    redo: async (id: string): Promise<void> => {
      await realFetch(`/api/meetings/${id}/redo`, { method: "POST" });
    },
    reschedule: async (id: string, body: { new_start_time: string; new_end_time: string }): Promise<{ new_meeting_id: string }> => {
      return realFetch(`/api/meetings/${id}/reschedule`, { method: "POST", body: JSON.stringify(body) });
    },
    quickMessage: async (id: string, body: { template: "looking_forward" | "custom"; text?: string }): Promise<void> => {
      await realFetch(`/api/meetings/${id}/quick-message`, { method: "POST", body: JSON.stringify(body) });
    },
    agenda: {
      patch: async (id: string, body: { items: { id: string; text: string; order: number }[] }): Promise<void> => {
        await realFetch(`/api/meetings/${id}/agenda`, { method: "PATCH", body: JSON.stringify(body) });
      },
      approveAndSend: async (id: string): Promise<void> => {
        await realFetch(`/api/meetings/${id}/agenda/approve-send`, { method: "POST" });
      }
    },
    checklist: {
      get: async (id: string): Promise<Checklist> => {
        return realFetch(`/api/meetings/${id}/checklist`);
      },
      patch: async (id: string, body: { items: any[] }): Promise<void> => {
        await realFetch(`/api/meetings/${id}/checklist`, { method: "PATCH", body: JSON.stringify(body) });
      },
      send: async (id: string): Promise<void> => {
        await realFetch(`/api/meetings/${id}/checklist/send`, { method: "POST" });
      }
    }
  },
  contacts: {
    doNotResearch: async (personKey: string, value: boolean): Promise<void> => {
      await realFetch(`/api/contacts/${personKey}/do-not-research`, { method: "PATCH", body: JSON.stringify({ value }) });
    }
  },
  settings: {
    get: async (): Promise<Settings> => {
      return realFetch("/api/settings");
    },
    patch: async (partial: Partial<Settings>): Promise<void> => {
      await realFetch("/api/settings", { method: "PATCH", body: JSON.stringify(partial) });
    },
    connections: async (): Promise<{ granted_scopes: string[], permissions_complete: boolean }> => {
      return realFetch("/api/settings/connections");
    },
    reconnectGoogle: async (): Promise<{ redirect_url: string }> => {
      return realFetch("/api/settings/reconnect-google", { method: "POST" });
    }
  },
  credits: {
    get: async (): Promise<Credits> => {
      return realFetch("/api/credits");
    },
  },
  extension: {
    meetingByLink: async (url: string): Promise<{ meeting_id: string, agenda_items: { id: string; text: string }[] } | null> => {
      return realFetch(`/api/extension/meeting-by-link?meet_link=${encodeURIComponent(url)}`);
    }
  },
  admin: {
    overview: async (): Promise<AdminOverview> => {
      return realFetch("/api/admin/analytics/overview");
    },
    users: async (): Promise<AdminUserRow[]> => {
      return realFetch("/api/admin/analytics/users");
    },
  },
};

export const API_BASE_URL = API_BASE;
export const IS_MOCK_API = false;
