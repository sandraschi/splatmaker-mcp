import { useCallback, useEffect, useState } from "react";

const ZOOM_LEVELS = [0.8, 1.0, 1.25, 1.5, 2.0, 3.0];

function loadSaved(): number {
	try {
		const saved = localStorage.getItem("tauri-zoom");
		if (saved) {
			const idx = ZOOM_LEVELS.indexOf(Number.parseFloat(saved));
			return idx >= 0 ? idx : 1;
		}
	} catch {
		/* storage unavailable - default zoom */
	}
	return 1;
}

export function useZoom() {
	const [, setZoomIndex] = useState(loadSaved);

	const applyZoom = useCallback(async (level: number) => {
		localStorage.setItem("tauri-zoom", String(level));
		try {
			const { getCurrentWebview } = await import("@tauri-apps/api/webview");
			await getCurrentWebview().setZoom(level);
			return;
		} catch {
			/* not in Tauri - fall through to CSS zoom so dev behaves the same */
		}
		if (typeof document !== "undefined") {
			document.documentElement.style.zoom = String(level);
		}
	}, []);

	useEffect(() => {
		const handler = (e: WheelEvent) => {
			if (!e.ctrlKey) return;
			e.preventDefault();
			setZoomIndex((prev) => {
				const next =
					e.deltaY < 0
						? Math.min(prev + 1, ZOOM_LEVELS.length - 1)
						: Math.max(prev - 1, 0);
				if (next !== prev) applyZoom(ZOOM_LEVELS[next]);
				return next;
			});
		};
		window.addEventListener("wheel", handler, { passive: false });
		const saved = localStorage.getItem("tauri-zoom");
		if (saved) applyZoom(Number.parseFloat(saved));
		return () => window.removeEventListener("wheel", handler);
	}, [applyZoom]);
}
