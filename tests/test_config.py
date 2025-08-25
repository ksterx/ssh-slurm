import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ssh_slurm.core.config import ConfigManager, ServerProfile


class TestServerProfile:
    def test_create_basic_profile(self):
        profile = ServerProfile(
            hostname="example.com",
            username="testuser",
            key_filename="/home/user/.ssh/id_rsa",
        )

        assert profile.hostname == "example.com"
        assert profile.username == "testuser"
        assert profile.key_filename == "/home/user/.ssh/id_rsa"
        assert profile.port == 22  # default
        assert profile.description is None
        assert profile.ssh_host is None

    def test_create_profile_with_all_fields(self):
        profile = ServerProfile(
            hostname="dgx.example.com",
            username="researcher",
            key_filename="/home/user/.ssh/dgx_key",
            port=2222,
            description="DGX server for ML training",
            ssh_host="dgx-host",
        )

        assert profile.hostname == "dgx.example.com"
        assert profile.username == "researcher"
        assert profile.key_filename == "/home/user/.ssh/dgx_key"
        assert profile.port == 2222
        assert profile.description == "DGX server for ML training"
        assert profile.ssh_host == "dgx-host"

    def test_to_dict(self):
        profile = ServerProfile(
            hostname="example.com",
            username="testuser",
            key_filename="/home/user/.ssh/id_rsa",
            port=2222,
            description="Test server",
        )

        expected = {
            "hostname": "example.com",
            "username": "testuser",
            "key_filename": "/home/user/.ssh/id_rsa",
            "port": 2222,
            "description": "Test server",
            "ssh_host": None,
            "env_vars": None,
        }

        assert profile.to_dict() == expected

    def test_from_dict(self):
        data = {
            "hostname": "example.com",
            "username": "testuser",
            "key_filename": "/home/user/.ssh/id_rsa",
            "port": 2222,
            "description": "Test server",
            "ssh_host": "test-host",
        }

        profile = ServerProfile.from_dict(data)

        assert profile.hostname == "example.com"
        assert profile.username == "testuser"
        assert profile.key_filename == "/home/user/.ssh/id_rsa"
        assert profile.port == 2222
        assert profile.description == "Test server"
        assert profile.ssh_host == "test-host"


class TestConfigManager:
    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = f.name
        # Remove the empty file so tests can control whether it exists
        os.unlink(temp_path)
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def sample_config_data(self):
        return {
            "current_profile": "test-profile",
            "profiles": {
                "test-profile": {
                    "hostname": "example.com",
                    "username": "testuser",
                    "key_filename": "/home/user/.ssh/id_rsa",
                    "port": 22,
                    "description": "Test server",
                    "ssh_host": None,
                },
                "dgx-profile": {
                    "hostname": "dgx.example.com",
                    "username": "researcher",
                    "key_filename": "/home/user/.ssh/dgx_key",
                    "port": 2222,
                    "description": "DGX server",
                    "ssh_host": "dgx-host",
                },
            },
        }

    def test_init_with_existing_config(self, temp_config_file, sample_config_data):
        # Write sample config to temp file
        with open(temp_config_file, "w") as f:
            json.dump(sample_config_data, f)

        config_manager = ConfigManager(temp_config_file)

        assert config_manager.config_path == Path(temp_config_file)
        assert config_manager.config_data == sample_config_data

    def test_init_with_nonexistent_config(self, temp_config_file):
        # Don't create the file, just use the path
        config_manager = ConfigManager(temp_config_file)

        expected_data = {"current_profile": None, "profiles": {}}
        assert config_manager.config_data == expected_data

        # Should have created the file
        assert os.path.exists(temp_config_file)

    def test_init_with_invalid_json(self, temp_config_file):
        # Write invalid JSON to file
        with open(temp_config_file, "w") as f:
            f.write("invalid json content {")

        with pytest.raises(RuntimeError, match="Failed to load config"):
            ConfigManager(temp_config_file)

    @patch("pathlib.Path.home")
    def test_default_config_path(self, mock_home, temp_config_file):
        temp_dir = Path(temp_config_file).parent
        mock_home.return_value = temp_dir

        config_manager = ConfigManager()
        expected_path = temp_dir / ".config" / "ssh-slurm.json"

        assert config_manager.config_path == expected_path

    def test_add_profile(self, temp_config_file):
        config_manager = ConfigManager(temp_config_file)

        profile = ServerProfile(
            hostname="new.example.com",
            username="newuser",
            key_filename="/home/user/.ssh/new_key",
        )

        config_manager.add_profile("new-profile", profile)

        assert "new-profile" in config_manager.config_data["profiles"]
        assert (
            config_manager.config_data["profiles"]["new-profile"] == profile.to_dict()
        )

        # Verify it was saved to file
        with open(temp_config_file, "r") as f:
            saved_data = json.load(f)
        assert saved_data["profiles"]["new-profile"] == profile.to_dict()

    def test_get_profile_existing(self, temp_config_file, sample_config_data):
        with open(temp_config_file, "w") as f:
            json.dump(sample_config_data, f)

        config_manager = ConfigManager(temp_config_file)
        profile = config_manager.get_profile("test-profile")

        assert profile is not None
        assert profile.hostname == "example.com"
        assert profile.username == "testuser"

    def test_get_profile_nonexistent(self, temp_config_file):
        config_manager = ConfigManager(temp_config_file)
        profile = config_manager.get_profile("nonexistent")

        assert profile is None

    def test_list_profiles(self, temp_config_file, sample_config_data):
        with open(temp_config_file, "w") as f:
            json.dump(sample_config_data, f)

        config_manager = ConfigManager(temp_config_file)
        profiles = config_manager.list_profiles()

        assert len(profiles) == 2
        assert "test-profile" in profiles
        assert "dgx-profile" in profiles
        assert isinstance(profiles["test-profile"], ServerProfile)
        assert profiles["test-profile"].hostname == "example.com"

    def test_remove_profile_existing(self, temp_config_file, sample_config_data):
        with open(temp_config_file, "w") as f:
            json.dump(sample_config_data, f)

        config_manager = ConfigManager(temp_config_file)
        result = config_manager.remove_profile("test-profile")

        assert result is True
        assert "test-profile" not in config_manager.config_data["profiles"]
        # Should clear current profile if it was the removed one
        assert config_manager.config_data["current_profile"] is None

    def test_remove_profile_nonexistent(self, temp_config_file):
        config_manager = ConfigManager(temp_config_file)
        result = config_manager.remove_profile("nonexistent")

        assert result is False

    def test_set_current_profile_existing(self, temp_config_file, sample_config_data):
        with open(temp_config_file, "w") as f:
            json.dump(sample_config_data, f)

        config_manager = ConfigManager(temp_config_file)
        result = config_manager.set_current_profile("dgx-profile")

        assert result is True
        assert config_manager.config_data["current_profile"] == "dgx-profile"

    def test_set_current_profile_nonexistent(self, temp_config_file):
        config_manager = ConfigManager(temp_config_file)
        result = config_manager.set_current_profile("nonexistent")

        assert result is False
        assert config_manager.config_data["current_profile"] is None

    def test_get_current_profile(self, temp_config_file, sample_config_data):
        with open(temp_config_file, "w") as f:
            json.dump(sample_config_data, f)

        config_manager = ConfigManager(temp_config_file)
        current = config_manager.get_current_profile()

        assert current is not None
        assert current.hostname == "example.com"  # test-profile is current

    def test_get_current_profile_none_set(self, temp_config_file):
        config_manager = ConfigManager(temp_config_file)
        current = config_manager.get_current_profile()

        assert current is None

    def test_get_current_profile_name(self, temp_config_file, sample_config_data):
        with open(temp_config_file, "w") as f:
            json.dump(sample_config_data, f)

        config_manager = ConfigManager(temp_config_file)
        name = config_manager.get_current_profile_name()

        assert name == "test-profile"

    def test_update_profile_existing(self, temp_config_file, sample_config_data):
        with open(temp_config_file, "w") as f:
            json.dump(sample_config_data, f)

        config_manager = ConfigManager(temp_config_file)
        result = config_manager.update_profile(
            "test-profile",
            hostname="updated.example.com",
            description="Updated description",
        )

        assert result is True
        profile = config_manager.get_profile("test-profile")
        assert profile.hostname == "updated.example.com"
        assert profile.description == "Updated description"
        # Other fields should remain unchanged
        assert profile.username == "testuser"

    def test_update_profile_nonexistent(self, temp_config_file):
        config_manager = ConfigManager(temp_config_file)
        result = config_manager.update_profile(
            "nonexistent", hostname="new.example.com"
        )

        assert result is False

    def test_expand_path(self, temp_config_file):
        config_manager = ConfigManager(temp_config_file)

        # Test tilde expansion
        with patch.dict(os.environ, {"HOME": "/home/testuser"}):
            expanded = config_manager.expand_path("~/.ssh/id_rsa")
            assert expanded == "/home/testuser/.ssh/id_rsa"

    def test_save_config_error_handling(self, temp_config_file):
        config_manager = ConfigManager(temp_config_file)

        # Make file read-only to cause write error
        os.chmod(temp_config_file, 0o444)

        with pytest.raises(RuntimeError, match="Failed to save config"):
            config_manager.add_profile(
                "test",
                ServerProfile(
                    hostname="test.com", username="test", key_filename="/test/key"
                ),
            )

        # Restore permissions for cleanup
        os.chmod(temp_config_file, 0o644)
