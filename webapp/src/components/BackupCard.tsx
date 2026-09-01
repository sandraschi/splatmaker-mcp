import { Download, Upload, HardDrive, Database, FileText } from "lucide-react";
import { useState } from "react";
import { API_BASE } from "../lib/api";

export function BackupCard() {
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const handleExport = async () => {
    setBusy(true); setStatus("Preparing vault.zip…");
    try {
      const res = await fetch(`${API_BASE}/api/backup/vault`);
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = `memops-vault-${new Date().toISOString().slice(0,10)}.zip`; a.click(); URL.revokeObjectURL(url);
      setStatus("Vault exported — db/vectors rebuild from markdown.");
    } catch (e) { setStatus(`Export: ${e instanceof Error ? e.message : String(e)} — fallback: copy C:\\Users\\sandr\\.advanced-memory\\vault`); } finally { setBusy(false); }
  };
  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; if (!f) return;
    setBusy(true); setStatus(`Uploading ${f.name}…`);
    try {
      const fd = new FormData(); fd.append("file", f);
      const res = await fetch(`${API_BASE}/api/backup/restore`, { method: "POST", body: fd });
      if (!res.ok) throw new Error(await res.text());
      setStatus("Restored — re-embedding in background.");
    } catch (err) { setStatus(`Restore failed: ${err instanceof Error ? err.message : String(err)}`);} finally { setBusy(false); e.target.value=""; }
  };
  return (
    <div data-testid="backup-card" className="rounded border border-zinc-800 bg-zinc-900 p-4 space-y-3">
      <div className="flex items-center gap-2 border-b border-zinc-800 pb-2"><HardDrive className="w-4 h-4 text-amber-400"/><h3 className="text-sm font-bold">Vault Backup & Restore</h3><span className="ml-auto text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300">derivative-safe</span></div>
      <div className="grid gap-1.5 text-xs"><div className="flex gap-2"><FileText className="w-3.5 h-3.5 text-emerald-400 mt-0.5"/><span><b>vault/*.md</b> source — back this up.</span></div><div className="flex gap-2"><Database className="w-3.5 h-3.5 text-zinc-500 mt-0.5"/><span><b>memory.db + vectors/</b> derivatives — rebuilt via re-embed.</span></div></div>
      <div className="flex gap-2 pt-1"><button data-testid="backup-export" onClick={handleExport} disabled={busy} className="flex-1 flex items-center justify-center gap-1.5 rounded bg-amber-600 hover:bg-amber-500 disabled:opacity-40 px-3 py-2 text-xs font-semibold text-white"><Download className="w-3.5 h-3.5"/> Export vault.zip</button><label data-testid="backup-import" className={`flex-1 flex items-center justify-center gap-1.5 rounded border border-zinc-700 hover:bg-zinc-800 px-3 py-2 text-xs cursor-pointer ${busy?"opacity-40 pointer-events-none":""}`}><Upload className="w-3.5 h-3.5"/> Restore<input type="file" accept=".zip" className="hidden" onChange={handleImport} disabled={busy}/></label></div>
      {status && <div data-testid="backup-status" className="text-xs text-zinc-400 bg-zinc-950 rounded px-3 py-2 border border-zinc-800">{status}</div>}
      <div className="text-[11px] text-zinc-500">Manual: copy <code>C:\Users\sandr\.advanced-memory\vault</code> or run <code>mcp-central-docs/scripts/backup-memops-vault.ps1</code>.</div>
    </div>
  );
}
