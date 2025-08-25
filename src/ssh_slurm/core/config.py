import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Self


@dataclass
class ServerProfile:
    hostname: str
    username: str
    key_filename: str
    port: int = 22
    description: str | None = None
    ssh_host: str | None = None  # SSH config host name if using SSH config
    env_vars: dict[str, str] | None = None  # Environment variables for this profile

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**data)


class ConfigManager:
    def __init__(self, config_path: str | None = None):
        self.config_path = (
            Path(config_path) if config_path else self._get_default_config_path()
        )
        self.config_data: dict[str, Any] = {}
        self.load_config()

    def _get_default_config_path(self) -> Path:
        config_dir = Path.home() / ".config"
        config_dir.mkdir(exist_ok=True)
        return config_dir / "ssh-slurm.json"

    def load_config(self) -> None:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    self.config_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                raise RuntimeError(
                    f"Failed to load config from {self.config_path}: {e}"
                )
        else:
            self.config_data = {"current_profile": None, "profiles": {}}
            self.save_config()

    def save_config(self) -> None:
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config_data, f, indent=2)
        except IOError as e:
            raise RuntimeError(f"Failed to save config to {self.config_path}: {e}")

    def add_profile(self, name: str, profile: ServerProfile) -> None:
        if "profiles" not in self.config_data:
            self.config_data["profiles"] = {}

        self.config_data["profiles"][name] = profile.to_dict()
        self.save_config()

    def remove_profile(self, name: str) -> bool:
        if name in self.config_data.get("profiles", {}):
            del self.config_data["profiles"][name]

            if self.config_data.get("current_profile") == name:
                self.config_data["current_profile"] = None

            self.save_config()
            return True
        return False

    def get_profile(self, name: str) -> ServerProfile | None:
        profiles = self.config_data.get("profiles", {})
        if name in profiles:
            return ServerProfile.from_dict(profiles[name])
        return None

    def list_profiles(self) -> dict[str, ServerProfile]:
        profiles = {}
        for name, data in self.config_data.get("profiles", {}).items():
            profiles[name] = ServerProfile.from_dict(data)
        return profiles

    def set_current_profile(self, name: str) -> bool:
        if name in self.config_data.get("profiles", {}):
            self.config_data["current_profile"] = name
            self.save_config()
            return True
        return False

    def get_current_profile(self) -> ServerProfile | None:
        current_name = self.config_data.get("current_profile")
        if current_name:
            return self.get_profile(current_name)
        return None

    def get_current_profile_name(self) -> str | None:
        return self.config_data.get("current_profile")

    def update_profile(self, name: str, **kwargs) -> bool:
        if name in self.config_data.get("profiles", {}):
            profile_data = self.config_data["profiles"][name]

            for key, value in kwargs.items():
                if value is not None:  # Only update non-None values
                    profile_data[key] = value

            self.save_config()
            return True
        return False

    def expand_path(self, path: str) -> str:
        return os.path.expanduser(path)
