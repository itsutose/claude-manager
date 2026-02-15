from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    claude_dir: Path = field(default_factory=lambda: Path.home() / ".claude")
    manager_dir: Path = field(default_factory=lambda: Path.home() / ".claude-manager")
    port: int = 8420
    poll_interval_sec: int = 5
    theme: str = "dark"
    notification_enabled: bool = True

    @property
    def projects_dir(self) -> Path:
        return self.claude_dir / "projects"

    @property
    def history_file(self) -> Path:
        return self.claude_dir / "history.jsonl"

    @property
    def pins_file(self) -> Path:
        return self.manager_dir / "pins.json"

    @property
    def read_state_file(self) -> Path:
        return self.manager_dir / "read_state.json"

    @property
    def group_config_file(self) -> Path:
        return self.manager_dir / "group_config.json"

    @property
    def hidden_file(self) -> Path:
        return self.manager_dir / "hidden.json"

    def ensure_manager_dir(self) -> None:
        self.manager_dir.mkdir(parents=True, exist_ok=True)
        for f in [self.pins_file, self.read_state_file, self.group_config_file]:
            if not f.exists():
                f.write_text("{}")

    @classmethod
    def load(cls) -> Config:
        config = cls()
        config.ensure_manager_dir()
        config_file = config.manager_dir / "config.json"
        if config_file.exists():
            data = json.loads(config_file.read_text())
            if "claude_dir" in data:
                config.claude_dir = Path(data["claude_dir"]).expanduser()
            if "port" in data:
                config.port = data["port"]
            if "poll_interval_sec" in data:
                config.poll_interval_sec = data["poll_interval_sec"]
            if "theme" in data:
                config.theme = data["theme"]
            if "notification_enabled" in data:
                config.notification_enabled = data["notification_enabled"]
        return config
