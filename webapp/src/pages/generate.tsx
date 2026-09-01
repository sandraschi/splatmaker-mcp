import { useState } from "react";

export function Generate() {
  const [msg, setMsg] = useState<string | null>(null);
  return (
    <div data-testid="generate-page" className="space-y-4 max-w-xl">
      <h1 className="text-xl font-bold">Generate</h1>
      <div className="rounded border border-zinc-800 bg-zinc-900 p-4 space-y-3">
        <p className="text-sm text-zinc-300">Use the MCP tool <code>splat_generate</code> from Claude/Cursor, or call the HTTP bridge directly.</p>
        <pre className="rounded bg-zinc-950 p-3 text-xs text-zinc-300 overflow-auto">{`# from_images — mixed dirs now auto-staged\nawait splat_generate(operation="from_images", image_paths=["D:/cap/a/1.jpg","D:/cap/b/2.jpg"])\n# from_video\nawait splat_generate(operation="from_video", video_path="D:/cap/walk.mp4")\n# then poll\nawait splat_generate(operation="status", job_id="...")`}</pre>
        <div className="text-xs text-zinc-500">Hint: dump your phone's DCIM into one folder or let the server stage for you. No manual consolidation needed now.</div>
      </div>
      {msg && <div className="text-sm text-amber-300">{msg}</div>}
    </div>
  );
}
