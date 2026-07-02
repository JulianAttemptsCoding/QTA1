"""Backup-first reproducibility manifest. Written BEFORE any compute is launched;
uploaded to GCS next to run outputs. A run without a manifest is invalid by policy.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class RunManifest:
    run_id: str
    phase: str
    config_path: str
    config_sha256: str
    persona_bank_hash: str
    prompt_hashes: dict[str, str]
    model_ids: list[str]
    seed: int
    data_snapshot_hashes: dict[str, str] = field(default_factory=dict)
    created_unix: float = field(default_factory=time.time)
    notes: str = ""

    @classmethod
    def create(cls, run_id: str, phase: str, config_path: Path, persona_bank_hash: str,
               prompt_hashes: dict[str, str], model_ids: list[str], seed: int,
               data_snapshot_hashes: dict[str, str] | None = None, notes: str = "") -> "RunManifest":
        return cls(run_id=run_id, phase=phase, config_path=str(config_path),
                   config_sha256=sha256_file(config_path), persona_bank_hash=persona_bank_hash,
                   prompt_hashes=prompt_hashes, model_ids=model_ids, seed=seed,
                   data_snapshot_hashes=data_snapshot_hashes or {}, notes=notes)

    def write(self, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / f"manifest_{self.run_id}.json"
        p.write_text(json.dumps(asdict(self), indent=2, sort_keys=True))
        return p
