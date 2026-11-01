// Same-origin by default (vite proxy forwards /api and /mcp to :11091).
// Absolute backend URL ONLY inside the Tauri WebView, where same-origin is
// the app bundle itself. A hardcoded absolute URL in a real browser tab breaks
// on any non-localhost hostname (LAN name, Tailscale MagicDNS, goliath).
declare global {
	interface Window {
		__TAURI__?: unknown;
		__TAURI_INTERNALS__?: unknown;
	}
}
const IN_TAURI =
	typeof window !== "undefined" &&
	("__TAURI__" in window || "__TAURI_INTERNALS__" in window);
export const API_BASE = IN_TAURI ? "http://127.0.0.1:11091" : "";

export interface Health {
	status: string;
	server: string;
	version: string;
	uptime_seconds: number;
	engine_configured: boolean;
}

export interface Job {
	job_id: string;
	kind: "from_video" | "from_images";
	status: "queued" | "running" | "done" | "failed";
	created_at: number;
	message: string;
	asset_paths?: Record<string, string>;
}

export interface Status {
	server: string;
	version: string;
	status: string;
	uptime_seconds: number;
	engine_configured: boolean;
	engine_verified: "pending" | "ok" | "broken" | "missing";
	engine_version: string;
	engine_error: string;
	max_iterations: number;
	tool_count: number;
	tools: string[];
	job_count: number;
	jobs_by_status: Record<string, number>;
}

export interface Capabilities {
	server: string;
	version: string;
	tools: { name: string; operations: string[]; description: string }[];
	rest: string[];
	ports: { backend: number };
}

export interface SkillSurface {
	prompt: { name: string; text: string };
	resource: { uri: string; description: string };
}

export interface ChatMessage {
	role: "user" | "assistant" | "system";
	content: string;
}

async function get<T>(path: string): Promise<T> {
	const res = await fetch(`${API_BASE}${path}`);
	if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
	return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
	const res = await fetch(`${API_BASE}${path}`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(body),
	});
	if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
	return res.json() as Promise<T>;
}

export const api = {
	health: () => get<Health>("/api/health"),
	status: () => get<Status>("/api/status"),
	capabilities: () => get<Capabilities>("/api/capabilities"),
	jobs: () => get<{ jobs: Job[] }>("/api/jobs"),
	jobStatus: (id: string) =>
		post<{ job_id: string; status: string; message?: string }>(
			"/api/jobs/status",
			{ job_id: id },
		),
	skills: () => get<SkillSurface>("/api/skills"),
	logs: (limit = 200) => get<{ logs: string[] }>(`/api/logs?limit=${limit}`),
	llmModels: () => get<{ models: string[]; error?: string }>("/api/llm/models"),
	llmChat: (model: string, messages: ChatMessage[], system?: string) =>
		post<{ model: string; message: string }>("/api/llm/chat", {
			model,
			messages,
			system,
		}),
};
