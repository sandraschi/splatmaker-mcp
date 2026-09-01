import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { Dashboard } from "./pages/dashboard";
import { Settings } from "./pages/settings";
import { Jobs } from "./pages/jobs";
import { Generate } from "./pages/generate";

function Gallery() { return <div data-testid="gallery-page" className="p-4 text-sm text-zinc-400">Gallery — job PLYs land in <code>~/.splatmaker-mcp/jobs/&lt;id&gt;/export/*.ply</code>. Wire Spark viewer later.</div>; }

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