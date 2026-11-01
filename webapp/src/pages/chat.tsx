import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../lib/api";
import { api } from "../lib/api";

const HISTORY_KEY = "splatmaker-chat-history";
const SYSTEM_PROMPT =
	"You are the Splatmaker assistant. Splatmaker turns phone photos or walk-around video into navigable 3D Gaussian-splat worlds using the free Nerfstudio/Splatfacto engine (ns-process-data -> ns-train splatfacto -> ns-export gaussian-splat, ~15k iterations, ~10 min on an RTX 4090). FOSS splats have no collision mesh: every VR use must route the .ply through blender-mcp blendersplatting first. Answer briefly and concretely.";

interface Msg extends ChatMessage {
	id: string;
}

const nid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export function Chat() {
	const [models, setModels] = useState<string[]>([]);
	const [model, setModel] = useState<string>("");
	const [messages, setMessages] = useState<Msg[]>(() => {
		try {
			const raw = JSON.parse(
				localStorage.getItem(HISTORY_KEY) ?? "[]",
			) as ChatMessage[];
			return raw
				.filter((m) => m && typeof m.content === "string")
				.map((m) => ({ ...m, id: nid() }));
		} catch {
			return [];
		}
	});
	const [input, setInput] = useState("");
	const [busy, setBusy] = useState(false);
	const [err, setErr] = useState<string | null>(null);
	const bottomRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		api
			.llmModels()
			.then((r) => {
				setModels(r.models);
				if (r.models.length > 0) setModel((m) => m || r.models[0]);
				if (r.error) setErr(r.error);
			})
			.catch((e) => setErr(String(e)));
	}, []);
	useEffect(() => {
		localStorage.setItem(HISTORY_KEY, JSON.stringify(messages));
		bottomRef.current?.scrollIntoView({ behavior: "smooth" });
	}, [messages]);

	const send = async () => {
		const text = input.trim();
		if (!text || busy || !model) return;
		const next: Msg[] = [
			...messages,
			{ id: nid(), role: "user" as const, content: text },
		];
		setMessages(next);
		setInput("");
		setBusy(true);
		setErr(null);
		try {
			const r = await api.llmChat(model, next, SYSTEM_PROMPT);
			setMessages([
				...next,
				{ id: nid(), role: "assistant" as const, content: r.message },
			]);
		} catch (e) {
			setErr(String(e));
		} finally {
			setBusy(false);
		}
	};

	return (
		<div data-testid="chat-page" className="space-y-4">
			<div className="flex items-center gap-3">
				<h1 className="text-xl font-bold">Chat</h1>
				<select
					data-testid="chat-model"
					value={model}
					onChange={(e) => setModel(e.target.value)}
					className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm"
				>
					{models.length === 0 && <option value="">no local models</option>}
					{models.map((m) => (
						<option key={m} value={m}>
							{m}
						</option>
					))}
				</select>
				<button
					type="button"
					onClick={() => setMessages([])}
					className="rounded border border-zinc-700 px-3 py-1 text-sm"
				>
					Clear
				</button>
			</div>
			{err && <div className="text-sm text-red-400">{err}</div>}
			<div data-testid="chat-messages" className="space-y-2">
				{messages.length === 0 && (
					<div className="text-sm text-zinc-300">
						Ask about captures, jobs, Nerfstudio, or the collider-mesh step.
						Answered by the selected local Ollama model — nothing leaves this
						machine.
					</div>
				)}
				{messages.map((m) => (
					<div
						key={m.id}
						className={`rounded border p-3 text-sm whitespace-pre-wrap ${
							m.role === "user"
								? "border-zinc-700 bg-zinc-900"
								: "border-zinc-800 bg-zinc-950 text-zinc-300"
						}`}
					>
						<span className="font-mono text-sm text-amber-200">{m.role}: </span>
						{m.content}
					</div>
				))}
				<div ref={bottomRef} />
			</div>
			<div className="flex gap-2">
				<input
					data-testid="chat-input"
					value={input}
					onChange={(e) => setInput(e.target.value)}
					onKeyDown={(e) => {
						if (e.key === "Enter" && !e.shiftKey) {
							e.preventDefault();
							send();
						}
					}}
					placeholder="Ask about splats, jobs, Nerfstudio…"
					className="flex-1 rounded border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm"
				/>
				<button
					type="button"
					data-testid="chat-send"
					onClick={send}
					disabled={busy || !model}
					className="rounded bg-amber-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
				>
					{busy ? "…" : "Send"}
				</button>
			</div>
		</div>
	);
}
