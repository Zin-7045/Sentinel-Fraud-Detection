import os
import json
import joblib
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict

from backend.config import MODEL_PATH


@dataclass
class ModelRecord:
    name: str
    version: str
    model_type: str
    created_at: str
    metrics: Dict[str, float]
    status: str
    path: str
    description: str = ""  # Fixed: removed space in field name


class ModelRegistry:
    def __init__(self):
        self.registry_file = os.path.join(MODEL_PATH, "registry.json")
        self.registry: Dict[str, ModelRecord] = {}
        self._load_registry()

    def _load_registry(self):
        if os.path.exists(self.registry_file):
            with open(self.registry_file) as f:
                data = json.load(f)
                for k, v in data.items():
                    self.registry[k] = ModelRecord(**v)

    def _save_registry(self):
        with open(self.registry_file, "w") as f:
            json.dump({k: asdict(v) for k, v in self.registry.items()}, f, indent=2)

    def register(self, name: str, model_type: str, metrics: Dict[str, float],
                 model_obj, description: str = ""):
        version = self._next_version(name)
        path = os.path.join(MODEL_PATH, f"{name}_v{version}.pkl")
        joblib.dump(model_obj, path)
        record = ModelRecord(
            name=name,
            version=f"v{version}",
            model_type=model_type,
            created_at=datetime.utcnow().isoformat(),
            metrics=metrics,
            status="active",
            path=path,
            description=description,
        )
        self.registry[f"{name}:v{version}"] = record
        self._save_registry()
        return record

    def get(self, name: str, version: Optional[str] = None) -> Optional[ModelRecord]:
        if version:
            return self.registry.get(f"{name}:{version}")
        versions = [k for k in self.registry if k.startswith(f"{name}:")]
        if not versions:
            return None
        latest = sorted(versions, key=lambda x: self.registry[x].created_at)[-1]
        return self.registry[latest]

    def list_models(self) -> List[ModelRecord]:
        return list(self.registry.values())

    def list_active(self) -> List[ModelRecord]:
        return [r for r in self.registry.values() if r.status == "active"]

    def archive(self, name: str, version: Optional[str] = None):
        record = self.get(name, version)
        if record:
            record.status = "archived"
            self._save_registry()

    def promote(self, name: str, version: str):
        record = self.get(name, version)
        if record:
            for r in self.registry.values():
                if r.name == name:
                    r.status = "standby"
            record.status = "active"
            self._save_registry()

    def _next_version(self, name: str) -> int:
        versions = [k for k in self.registry if k.startswith(f"{name}:")]
        if not versions:
            return 1
        max_v = max(int(k.split(":v")[1]) for k in versions if ":v" in k)
        return max_v + 1
