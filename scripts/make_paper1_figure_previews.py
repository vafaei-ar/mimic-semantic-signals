from __future__ import annotations

import base64
from pathlib import Path

from PIL import Image

ROOT = Path(".")
OUT = ROOT / "outputs" / "manuscript"

for stem in ("Figure_1", "Figure_2"):
    src = OUT / f"{stem}.png"
    img = Image.open(src).convert("RGB")
    img.thumbnail((420, 620))
    jpg = OUT / f"{stem}_preview.jpg"
    img.save(jpg, format="JPEG", quality=45, optimize=True)
    data = base64.b64encode(jpg.read_bytes()).decode("ascii")
    (OUT / f"{stem}_preview_data_uri.txt").write_text(
        "data:image/jpeg;base64," + data,
        encoding="utf-8",
    )
    print(stem, img.size, jpg.stat().st_size)
