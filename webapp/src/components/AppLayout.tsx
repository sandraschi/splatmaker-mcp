import { Link, useLocation } from "react-router-dom";
import { Box, LayoutDashboard, Radio, Settings, Image, Video, ListTree } from "lucide-react";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/generate", label: "Generate", icon: Box },
  { to: "/jobs", label: "Jobs", icon: ListTree },
  { to: "/gallery", label: "Gallery", icon: Image },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function AppLayout({ children }: { children: React.ReactNode }) {
  const loc = useLocation();
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex">
      <aside className="w-56 border-r border-zinc-800 bg-zinc-900/50 p-4 flex flex-col gap-4">
        <div className="flex items-center gap-2 text-amber-400 font-bold">
          <Radio size={20} /> splatmaker
        </div>
        <nav className="flex flex-col gap-1">
          {nav.map((n) => (
            <Link
              key={n.to}
              to={n.to}
              data-testid={`nav-${n.label.toLowerCase()}`}
              className={`flex items-center gap-2 rounded px-3 py-2 text-sm ${loc.pathname === n.to ? "bg-zinc-800 text-white" : "text-zinc-400 hover:bg-zinc-800/50"}`}
            >
              <n.icon size={16} /> {n.label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto text-xs text-zinc-500">Zero-cost splats · 4090 local</div>
      </aside>
      <main className="flex-1 p-6 overflow-auto">{children}</main>
    </div>
  );
}
