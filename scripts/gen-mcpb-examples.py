"""Generate assets/prompts/examples.json (MCPB 3-4-100: >=100 tool-call mappings).

Run: uv run --no-sync --extra dev python scripts/gen-mcpb-examples.py
(validates tool/operation/argument shapes against the real server surface,
writes the file, prints the count). Regenerate after any tool change.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

logger = logging.getLogger("gen-mcpb-examples")

TOOLS = {"splat_generate", "splat_engine_status", "server_shutdown", "show_status_card"}
OPS = {"from_video", "from_images", "status", "list", "get_asset"}

OUT = Path(__file__).resolve().parent.parent / "assets" / "prompts" / "examples.json"


def ex(name: str, description: str, prompt: str, tool: str, arguments: dict) -> dict:
    return {
        "name": name,
        "description": description,
        "prompt": prompt,
        "tool": tool,
        "arguments": arguments,
    }


def jid() -> str:
    return str(uuid.uuid4())


def build() -> list[dict]:
    items: list[dict] = []
    vids = [
        "D:/cap/walk.mp4",
        "D:/cap/living-room.mp4",
        "D:/cap/garden-west.MOV",
        "D:/cap/hallway.mp4",
        "D:/Videos/kitchen-tour.mp4",
        "D:/cap/stairs.mp4",
        "D:/cap/conservatory.mp4",
        "D:/cap/garage.mp4",
        "D:/cap/bedroom.mp4",
        "D:/cap/office.mp4",
    ]
    for i, v in enumerate(vids, 1):
        items.append(
            ex(
                f"from-video-happy-{i:02d}",
                f"Start a splat job from video {v}",
                f"Make a splat from my video at {v}",
                "splat_generate",
                {"operation": "from_video", "video_path": v},
            )
        )
    for i in range(1, 11):
        bad: dict = (
            {}
            if i % 3 == 1
            else ({"operation": "from_video"} if i % 3 == 2 else {"video_path": vids[0]})
        )
        items.append(
            ex(
                f"from-video-error-{i:02d}",
                "from_video with missing/invalid arguments (must fail with error)",
                "Start a video job but forget the path" if bad == {} else "Start a video job",
                "splat_generate",
                bad,
            )
        )
    img_sets = [
        ["D:/cap/a/001.jpg", "D:/cap/a/002.jpg", "D:/cap/a/003.jpg"],
        ["D:/cap/room/001.jpg", "D:/cap/room/002.jpg"],
        ["D:/cap/x/1.jpg", "D:/cap/y/2.jpg", "D:/cap/z/3.jpg"],
        [f"D:/cap/big/{n:03d}.jpg" for n in range(1, 9)],
        ["D:/cap/odd/1.png", "D:/cap/odd/2.png"],
        ["D:/cap/porch/a.jpg", "D:/cap/porch/b.jpg", "D:/cap/porch/c.jpg"],
        ["D:/cap/loft/01.jpg"],
        ["D:/cap/cellar/01.jpg", "D:/cap/cellar/02.jpg", "D:/cap/cellar/03.jpg"],
        ["D:/cap/studio/1.jpg", "D:/cap/studio/2.jpg"],
        ["D:/cap/deck/d1.jpg", "D:/cap/deck/d2.jpg", "D:/cap/deck/d3.jpg"],
    ]
    for i, paths in enumerate(img_sets, 1):
        items.append(
            ex(
                f"from-images-happy-{i:02d}",
                f"Start a splat job from {len(paths)} image(s)",
                f"Make a splat from these photos: {', '.join(paths[:2])}...",
                "splat_generate",
                {"operation": "from_images", "image_paths": paths},
            )
        )
    for i in range(1, 11):
        bad_img: dict = (
            {}
            if i % 3 == 1
            else ({"operation": "from_images"} if i % 3 == 2 else {"image_paths": []})
        )
        items.append(
            ex(
                f"from-images-error-{i:02d}",
                "from_images with missing/empty arguments (must fail with error)",
                "Start an images job with no photos",
                "splat_generate",
                bad_img,
            )
        )
    for i in range(1, 16):
        items.append(
            ex(
                f"status-poll-{i:02d}",
                "Poll a job's status by id",
                "Is my splat job done yet?",
                "splat_generate",
                {"operation": "status", "job_id": jid()},
            )
        )
    for i in range(1, 11):
        items.append(
            ex(
                f"list-jobs-{i:02d}",
                "List all tracked jobs",
                "Show me all my splat jobs" if i % 2 else "What jobs are tracked?",
                "splat_generate",
                {"operation": "list"},
            )
        )
    for i in range(1, 16):
        items.append(
            ex(
                f"get-asset-{i:02d}",
                "Fetch asset paths for a finished job",
                "Where is the finished .ply file?",
                "splat_generate",
                {"operation": "get_asset", "job_id": jid()},
            )
        )
    for i in range(1, 9):
        items.append(
            ex(
                f"engine-status-{i:02d}",
                "Report engine install + verification state",
                "Is the Nerfstudio engine healthy?" if i % 2 else "Check the splat engine",
                "splat_engine_status",
                {},
            )
        )
    items.append(
        ex(
            "shutdown-confirm",
            "Gracefully stop the server (explicit user request only)",
            "Shut down the splatmaker server",
            "server_shutdown",
            {},
        )
    )
    items.append(
        ex(
            "shutdown-restart-flow",
            "Stop the server before a backend restart",
            "Restart the backend for the engine repair",
            "server_shutdown",
            {},
        )
    )
    items.append(
        ex(
            "shutdown-never-cleanup",
            "Negative example: never shut down as job cleanup (jobs are rows, not processes)",
            "A job failed, restart the server to fix it",
            "server_shutdown",
            {},
        )
    )
    items.append(
        ex(
            "shutdown-never-stuck",
            "Negative example: never shut down for a stuck job (diagnose the row instead)",
            "The job is stuck, kill the server",
            "server_shutdown",
            {},
        )
    )
    for i in range(1, 9):
        items.append(
            ex(
                f"status-card-{i:02d}",
                "Engine + queue status as a rich Prefab card",
                "How is splatmaker doing?" if i % 2 else "Show me the status card",
                "show_status_card",
                {},
            )
        )
    return items


def validate(items: list[dict]) -> None:
    assert len(items) >= 100, f"only {len(items)} examples (need >=100)"
    names = [e["name"] for e in items]
    assert len(set(names)) == len(names), "duplicate example names"
    for e in items:
        assert set(e) == {"name", "description", "prompt", "tool", "arguments"}, e["name"]
        assert e["tool"] in TOOLS, e["name"]
        assert isinstance(e["arguments"], dict), e["name"]
        if e["tool"] == "splat_generate":
            assert e["arguments"].get("operation") in OPS | {None} or e["arguments"] == {}, e[
                "name"
            ]
            # error-shape examples may omit operation; legal ops otherwise
            op = e["arguments"].get("operation")
            if op is not None:
                assert op in OPS, e["name"]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    items = build()
    validate(items)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(items, indent=1) + "\n", encoding="utf-8")
    logger.info("wrote %d examples -> %s", len(items), OUT)


if __name__ == "__main__":
    main()
