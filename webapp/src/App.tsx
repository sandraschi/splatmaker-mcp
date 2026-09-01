import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { Dashboard } from "./pages/dashboard";
import { Jobs } from "./pages/jobs";
import { Generate } from "./pages/generate";

function Gallery() { return <div data-testid="gallery-page" className="p-4 text-sm text-zinc-400">Gallery — job PLYs land in <code>~/.splatmaker-mcp/jobs/&lt;id&gt;/export/*.ply</code>. Wire Spark viewer later.</div>; }
function Settings() { return <div data-testid="settings-page" className="p-4 text-sm text-zinc-400">Settings — engine: Nerfstudio, 15k iters. Override via <code>SPLATMAKER_MAX_ITERATIONS</code>. No API key needed (self-hosted).</div>; }

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/generate" element={<Generate />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/gallery" element={<Gallery />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  );
}