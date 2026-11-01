import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { Chat } from "./pages/chat";
import { Dashboard } from "./pages/dashboard";
import { Gallery } from "./pages/gallery";
import { Generate } from "./pages/generate";
import { Help } from "./pages/help";
import { Inbox } from "./pages/inbox";
import { Jobs } from "./pages/jobs";
import { Logs } from "./pages/logs";
import { Settings } from "./pages/settings";
import { Skills } from "./pages/skills";
import { Tools } from "./pages/tools";

export default function App() {
	return (
		<BrowserRouter>
			<AppLayout>
				<Routes>
					<Route path="/" element={<Dashboard />} />
					<Route path="/generate" element={<Generate />} />
					<Route path="/jobs" element={<Jobs />} />
					<Route path="/inbox" element={<Inbox />} />
					<Route path="/gallery" element={<Gallery />} />
					<Route path="/tools" element={<Tools />} />
					<Route path="/skills" element={<Skills />} />
					<Route path="/chat" element={<Chat />} />
					<Route path="/logs" element={<Logs />} />
					<Route path="/help" element={<Help />} />
					<Route path="/settings" element={<Settings />} />
				</Routes>
			</AppLayout>
		</BrowserRouter>
	);
}
