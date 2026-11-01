"""Synthetic multi-view room for mock e2e: a textured cube shot from 24 poses.

Real projective geometry (pinhole camera, painter's-algorithm faces), so
COLMAP can actually solve poses. Textures are checker + noise (very
matchable). Output: <out_dir>/img_XX.png, 640x480.

Usage: python scripts/gen-synthetic-room.py <out_dir> [--views N]
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
from PIL import Image

W, H = 640, 480
FOCAL = 520.0
K = np.array([[FOCAL, 0.0, W / 2.0], [0.0, FOCAL, H / 2.0], [0.0, 0.0, 1.0]])


def make_texture(seed: int, hue: tuple[int, int, int], glyph: str = "") -> Image.Image:
    rng = np.random.default_rng(seed)
    s = 256
    arr = np.zeros((s, s, 3), dtype=np.uint8)
    cell = 16
    # Fully random per cell in BOTH hue and luminance. SIFT keys off
    # gradients of luminance — isoluminant colors (however different the hue)
    # all look identical to the detector and matches die in the ratio test.
    # Range 30..220 keeps everything printable (no clipping) but strongly varied.
    for y in range(0, s, cell):
        for x in range(0, s, cell):
            arr[y : y + cell, x : x + cell] = rng.integers(30, 221, size=3).astype(np.uint8)
    # subtle darker cell borders (structure without the aliasing of pure-black lines)
    arr[::cell, :] = (arr[::cell, :].astype(np.uint16) * 7 // 10).astype(np.uint8)
    arr[:, ::cell] = (arr[:, ::cell].astype(np.uint16) * 7 // 10).astype(np.uint8)
    # Sensor-noise analogue: per-pixel jitter gives SIFT unique high-frequency
    # gradients everywhere (flat fills are feature deserts; real photos are noisy).
    arr = np.clip(arr.astype(np.int32) + rng.integers(-25, 26, size=(s, s, 1)), 0, 255).astype(
        np.uint8
    )
    img = Image.fromarray(arr)
    if glyph:
        # Big per-face glyph: unmistakable identity kills cross-face
        # doppelganger matches (symmetric geometry + similar texture
        # otherwise verifies wrong pairs and the seed model is garbage).
        from PIL import ImageDraw, ImageFont

        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default(size=180)
        except TypeError:
            font = ImageFont.load_default()
        d.text(
            (128, 128),
            glyph,
            fill=(255, 255, 255),
            font=font,
            anchor="mm",
            stroke_width=2,
            stroke_fill=(0, 0, 0),
        )
    return img


# Cube faces: (3d corners CCW from outside, texture seed, hue)
_BASE_FACES = [
    (np.array([[-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, -1]], float), 11, (200, 60, 60)),
    (np.array([[1, -1, -1], [-1, -1, -1], [-1, 1, -1], [1, 1, -1]], float), 22, (60, 200, 60)),
    (np.array([[-1, -1, -1], [-1, -1, 1], [-1, 1, 1], [-1, 1, -1]], float), 33, (60, 60, 200)),
    (np.array([[1, -1, 1], [1, -1, -1], [1, 1, -1], [1, 1, 1]], float), 44, (200, 200, 60)),
    (np.array([[-1, 1, 1], [1, 1, 1], [1, 1, -1], [-1, 1, -1]], float), 55, (200, 200, 60)),
    (np.array([[-1, -1, -1], [1, -1, -1], [1, -1, 1], [-1, -1, 1]], float), 66, (60, 200, 200)),
    # Floor: large, far, asymmetric context. Breaks the cube's symmetry so
    # the mapper cannot build a consistent-but-wrong doppelganger model.
    # Corners stay far from every camera (no near-plane crossings).
    (
        np.array([[-10, -3, -10], [-10, -3, 10], [10, -3, 10], [10, -3, -10]], float),
        77,
        (120, 120, 120),
    ),
]


def _rotx(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _roty(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


# Static tilt so EVERY view sees 2-3 faces: axis-aligned turntables
# degenerate to single-plane views and COLMAP fragments the model.
_TILT = _roty(math.radians(24)) @ _rotx(math.radians(17))
_GLYPHS = {11: "A", 22: "B", 33: "C", 44: "D", 55: "E", 66: "F", 77: "G"}
_FACES = [((_TILT @ corners.T).T, seed, hue) for corners, seed, hue in _BASE_FACES]
_TEXTURES = [make_texture(seed, hue, _GLYPHS[seed]) for _, seed, hue in _FACES]


def look_at(eye: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # Standard: zaxis points from target to camera, depth = +z in front.
    zaxis = eye / np.linalg.norm(eye)
    xaxis = np.cross(np.array([0.0, 1.0, 0.0]), zaxis)
    xaxis /= np.linalg.norm(xaxis)
    yaxis = np.cross(zaxis, xaxis)
    r = np.stack([xaxis, yaxis, zaxis], axis=0)
    t = -r @ eye
    return r, t


def _normalize(pts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Hartley normalization: centroid 0, mean radius sqrt(2)."""
    c = pts.mean(axis=0)
    s = np.sqrt(2) / (np.linalg.norm(pts - c, axis=1).mean() + 1e-12)
    t = np.array([[s, 0, -s * c[0]], [0, s, -s * c[1]], [0, 0, 1]])
    return t, (t @ np.concatenate([pts, np.ones((len(pts), 1))], axis=1).T).T[:, :2]


def find_h(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """Homography src->dst from 4 correspondences (normalized DLT)."""
    ts, src_n = _normalize(src)
    td, dst_n = _normalize(dst)
    a = []
    for (x, y), (u, v) in zip(src_n, dst_n, strict=True):
        a.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        a.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, vt = np.linalg.svd(np.asarray(a, float))
    h = (vt[-1] / vt[-1, -1]).reshape(3, 3)
    h = np.linalg.inv(td) @ h @ ts
    return h / h[2, 2]


def render(n_views: int, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    rect = np.array([[0, 0], [0, 256], [256, 256], [256, 0]], float)
    paths = []
    for i in range(n_views):
        # Fibonacci hemisphere: every view sees top + sides (level
        # turntables degenerate to single-plane edge-on views whose grazing
        # faces rasterize to nothing and starve COLMAP of 3D constraints).
        frac = (i + 0.5) / n_views
        el = math.radians(18 + 54 * frac)
        az = 2 * math.pi * i * 0.61803398875
        radius = 4.2 * math.cos(el)
        height = 4.2 * math.sin(el)
        eye = np.array([radius * math.cos(az), height, radius * math.sin(az)])
        r, t = look_at(eye)
        canvas = Image.new("RGB", (W, H), (18, 18, 22))

        # painter: far faces first (depth = -z in this R convention)
        def _depth(f: int, _r: np.ndarray = r, _t: np.ndarray = t) -> float:
            c = (_FACES[f][0] @ _r.T) + _t
            return float(np.mean(-c[..., 2]))

        order = sorted(range(6), key=_depth, reverse=True)
        for f in order:
            corners = _FACES[f][0]
            # world-space facing cull (convention-proof): outward normal
            # must point at the camera.
            n = np.cross(corners[1] - corners[0], corners[2] - corners[0])
            n /= np.linalg.norm(n)
            if float(n @ (eye - corners.mean(axis=0))) <= 0:
                continue
            cam = (corners @ r.T) + t
            # Clamp per-corner depth: corners at/behind the near plane would
            # project mirrored (bowtie quad, singular homography, black
            # warp). Clamping keeps a consistent mapping; the clipped sliver
            # stretches texture harmlessly instead of poisoning the frame.
            depth = np.maximum(-cam[:, 2], 0.4)
            pix = cam[:, :2] / depth[:, None] * FOCAL + np.array([W / 2.0, H / 2.0])
            # drop rasterization noise (slivers contribute no matchable area)
            area2 = abs(
                (pix[1, 0] - pix[0, 0]) * (pix[2, 1] - pix[0, 1])
                - (pix[2, 0] - pix[0, 0]) * (pix[1, 1] - pix[0, 1])
            ) + abs(
                (pix[2, 0] - pix[0, 0]) * (pix[3, 1] - pix[0, 1])
                - (pix[3, 0] - pix[0, 0]) * (pix[2, 1] - pix[0, 1])
            )
            if area2 < 600:
                continue
            h = find_h(rect, pix)  # texture rect -> projected quad
            hi = np.linalg.inv(h).ravel()[:8]
            coeffs = (hi[0], hi[1], hi[2], hi[3], hi[4], hi[5], hi[6], hi[7])
            warped = _TEXTURES[f].transform(
                (W, H), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC
            )
            m = Image.new("L", (256, 256), 255).transform(
                (W, H), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.NEAREST
            )
            # Painter's algorithm: order is far-to-near, paste overwrites.
            # (A mask-union + Image.composite variant silently blacked out
            # already-drawn faces — paste is exact here.)
            canvas.paste(warped, (0, 0), m)
        p = os.path.join(out_dir, f"img_{i:02d}.png")
        canvas.save(p)
        paths.append(p)
    return paths


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "synthetic-room"
    n = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[2] == "--views" else 24
    paths = render(n, out)
    print(f"wrote {len(paths)} views -> {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
