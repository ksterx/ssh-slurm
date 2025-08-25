import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ssh_slurm.core.ssh_config import SSHConfigParser, SSHHost, get_ssh_config_host


class TestSSHHost:
    def test_create_basic_host(self):
        host = SSHHost(hostname="example.com")

        assert host.hostname == "example.com"
        assert host.user is None
        assert host.port is None
        assert host.identity_file is None
        assert host.proxy_command is None
        assert host.proxy_jump is None
        assert host.forward_agent is None

    def test_create_full_host(self):
        host = SSHHost(
            hostname="dgx.example.com",
            user="researcher",
            port=2222,
            identity_file="~/.ssh/dgx_key",
            proxy_command="ssh proxy-host nc %h %p",
            proxy_jump="bastion.example.com",
            forward_agent=True,
        )

        assert host.hostname == "dgx.example.com"
        assert host.user == "researcher"
        assert host.port == 2222
        assert host.identity_file == "~/.ssh/dgx_key"
        assert host.proxy_command == "ssh proxy-host nc %h %p"
        assert host.proxy_jump == "bastion.example.com"
        assert host.forward_agent is True

    def test_effective_properties(self):
        host = SSHHost(
            hostname="example.com",
            user="testuser",
            port=2222,
            identity_file="~/.ssh/test_key",
        )

        assert host.effective_hostname == "example.com"
        assert host.effective_user == "testuser"
        assert host.effective_port == 2222

    def test_effective_port_default(self):
        host = SSHHost(hostname="example.com")
        assert host.effective_port == 22

    def test_effective_identity_file_expansion(self):
        host = SSHHost(hostname="example.com", identity_file="~/.ssh/id_rsa")

        with patch.dict(os.environ, {"HOME": "/home/testuser"}):
            assert host.effective_identity_file == "/home/testuser/.ssh/id_rsa"

    def test_effective_identity_file_none(self):
        host = SSHHost(hostname="example.com")
        assert host.effective_identity_file is None


class TestSSHConfigParser:
    @pytest.fixture
    def temp_ssh_config(self):
        """Create a temporary SSH config file for testing"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ssh_config"
        ) as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def sample_ssh_config(self):
        return """# Sample SSH config
Host dgx1
    HostName dgx1.example.com
    User researcher
    Port 2222
    IdentityFile ~/.ssh/dgx_key
    ForwardAgent yes

Host bastion
    HostName bastion.company.com
    User admin
    IdentityFile ~/.ssh/company_key

Host dgx-*
    HostName %h.example.com
    User researcher
    ProxyJump bastion
    IdentityFile ~/.ssh/dgx_wildcard_key

Host proxy-test
    HostName internal.example.com
    ProxyCommand ssh bastion nc %h %p

Host *
    User defaultuser
    Port 22
    IdentityFile ~/.ssh/id_rsa

# Comment at the end
"""

    def test_init_with_existing_config(self, temp_ssh_config, sample_ssh_config):
        with open(temp_ssh_config, "w") as f:
            f.write(sample_ssh_config)

        parser = SSHConfigParser(temp_ssh_config)

        assert parser.config_path == Path(temp_ssh_config)
        assert len(parser.hosts) == 5  # dgx1, bastion, dgx-*, proxy-test, *

    def test_init_with_nonexistent_config(self, temp_ssh_config):
        # Don't create the file, just use the path
        parser = SSHConfigParser(temp_ssh_config)

        assert parser.config_path == Path(temp_ssh_config)
        assert len(parser.hosts) == 0

    @patch("pathlib.Path.home")
    def test_default_config_path(self, mock_home):
        mock_home.return_value = Path("/home/testuser")

        parser = SSHConfigParser()
        expected_path = Path("/home/testuser/.ssh/config")

        assert parser.config_path == expected_path

    def test_parse_basic_host(self, temp_ssh_config):
        config = """Host testhost
    HostName test.example.com
    User testuser
    Port 2222
    IdentityFile ~/.ssh/test_key
"""

        with open(temp_ssh_config, "w") as f:
            f.write(config)

        parser = SSHConfigParser(temp_ssh_config)

        assert "testhost" in parser.hosts
        host = parser.hosts["testhost"]
        assert host.hostname == "test.example.com"
        assert host.user == "testuser"
        assert host.port == 2222
        assert host.identity_file == "~/.ssh/test_key"

    def test_parse_proxy_settings(self, temp_ssh_config):
        config = """Host proxied
    HostName internal.example.com
    ProxyJump bastion.example.com
    ProxyCommand ssh proxy nc %h %p
    ForwardAgent yes
"""

        with open(temp_ssh_config, "w") as f:
            f.write(config)

        parser = SSHConfigParser(temp_ssh_config)

        host = parser.hosts["proxied"]
        assert host.proxy_jump == "bastion.example.com"
        assert host.proxy_command == "ssh proxy nc %h %p"
        assert host.forward_agent is True

    def test_parse_comments_and_empty_lines(self, temp_ssh_config):
        config = """# This is a comment
Host testhost
    # Another comment
    HostName test.example.com
    
    User testuser
    # More comments

Host another
    HostName another.example.com
"""

        with open(temp_ssh_config, "w") as f:
            f.write(config)

        parser = SSHConfigParser(temp_ssh_config)

        assert len(parser.hosts) == 2
        assert parser.hosts["testhost"].hostname == "test.example.com"
        assert parser.hosts["testhost"].user == "testuser"

    def test_parse_boolean_values(self, temp_ssh_config):
        config = """Host test-true
    ForwardAgent yes

Host test-false
    ForwardAgent no

Host test-numeric
    ForwardAgent 1
"""

        with open(temp_ssh_config, "w") as f:
            f.write(config)

        parser = SSHConfigParser(temp_ssh_config)

        assert parser.hosts["test-true"].forward_agent is True
        assert parser.hosts["test-false"].forward_agent is False
        assert parser.hosts["test-numeric"].forward_agent is True

    def test_parse_invalid_port(self, temp_ssh_config):
        config = """Host testhost
    Port invalid_port
    HostName test.example.com
"""

        with open(temp_ssh_config, "w") as f:
            f.write(config)

        parser = SSHConfigParser(temp_ssh_config)

        # Should handle invalid port gracefully
        host = parser.hosts["testhost"]
        assert host.port is None

    def test_get_host_exact_match(self, temp_ssh_config, sample_ssh_config):
        with open(temp_ssh_config, "w") as f:
            f.write(sample_ssh_config)

        parser = SSHConfigParser(temp_ssh_config)
        host = parser.get_host("dgx1")

        assert host is not None
        assert host.hostname == "dgx1.example.com"
        assert host.user == "researcher"
        assert host.port == 2222

    def test_get_host_pattern_match(self, temp_ssh_config, sample_ssh_config):
        with open(temp_ssh_config, "w") as f:
            f.write(sample_ssh_config)

        parser = SSHConfigParser(temp_ssh_config)
        host = parser.get_host("dgx-01")  # Should match dgx-* pattern

        assert host is not None
        assert host.hostname == "%h.example.com"  # Pattern hostname from config
        assert host.user == "researcher"
        assert host.proxy_jump == "bastion"

    def test_get_host_wildcard_fallback(self, temp_ssh_config, sample_ssh_config):
        with open(temp_ssh_config, "w") as f:
            f.write(sample_ssh_config)

        parser = SSHConfigParser(temp_ssh_config)
        host = parser.get_host("unknown.example.com")  # Should match * pattern

        assert host is not None
        assert host.hostname == "unknown.example.com"
        assert host.user == "defaultuser"
        assert host.port == 22

    def test_get_host_no_match(self, temp_ssh_config):
        with open(temp_ssh_config, "w") as f:
            f.write("Host specific\n    HostName specific.com\n")

        parser = SSHConfigParser(temp_ssh_config)
        host = parser.get_host("nonexistent")

        assert host is None

    def test_match_pattern_exact(self, temp_ssh_config):
        parser = SSHConfigParser(temp_ssh_config)

        assert parser._match_pattern("exact", "exact") is True
        assert parser._match_pattern("exact", "different") is False

    def test_match_pattern_wildcard(self, temp_ssh_config):
        parser = SSHConfigParser(temp_ssh_config)

        assert parser._match_pattern("dgx-*", "dgx-01") is True
        assert parser._match_pattern("dgx-*", "dgx-02") is True
        assert parser._match_pattern("dgx-*", "gpu-01") is False
        assert parser._match_pattern("*", "anything") is True

    def test_match_pattern_question_mark(self, temp_ssh_config):
        parser = SSHConfigParser(temp_ssh_config)

        assert parser._match_pattern("host?", "host1") is True
        assert parser._match_pattern("host?", "host2") is True
        assert parser._match_pattern("host?", "host12") is False

    def test_list_hosts(self, temp_ssh_config, sample_ssh_config):
        with open(temp_ssh_config, "w") as f:
            f.write(sample_ssh_config)

        parser = SSHConfigParser(temp_ssh_config)
        hosts = parser.list_hosts()

        assert len(hosts) == 5
        assert "dgx1" in hosts
        assert "bastion" in hosts
        assert isinstance(hosts["dgx1"], SSHHost)

    def test_find_identity_files_with_config(self, temp_ssh_config):
        config = """Host testhost
    IdentityFile ~/.ssh/custom_key
"""

        with open(temp_ssh_config, "w") as f:
            f.write(config)

        parser = SSHConfigParser(temp_ssh_config)

        with patch.dict(os.environ, {"HOME": "/home/testuser"}):
            files = parser.find_identity_files("testhost")
            assert "/home/testuser/.ssh/custom_key" in files

    def test_find_identity_files_defaults(self, temp_ssh_config):
        parser = SSHConfigParser(temp_ssh_config)

        # Mock existing default key files
        mock_files = ["/home/testuser/.ssh/id_rsa", "/home/testuser/.ssh/id_ed25519"]

        with (
            patch("os.path.exists") as mock_exists,
            patch.dict(os.environ, {"HOME": "/home/testuser"}),
        ):
            mock_exists.side_effect = lambda path: path in mock_files

            files = parser.find_identity_files("unknown_host")

            assert "/home/testuser/.ssh/id_rsa" in files
            assert "/home/testuser/.ssh/id_ed25519" in files

    def test_case_insensitive_parsing(self, temp_ssh_config):
        config = """HOST testhost
    HOSTNAME test.example.com
    USER testuser
    PORT 2222
"""

        with open(temp_ssh_config, "w") as f:
            f.write(config)

        parser = SSHConfigParser(temp_ssh_config)

        host = parser.hosts["testhost"]
        assert host.hostname == "test.example.com"
        assert host.user == "testuser"
        assert host.port == 2222


class TestConvenienceFunction:
    @pytest.fixture
    def temp_ssh_config(self):
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ssh_config"
        ) as f:
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_get_ssh_config_host(self, temp_ssh_config):
        config = """Host testhost
    HostName test.example.com
    User testuser
"""

        with open(temp_ssh_config, "w") as f:
            f.write(config)

        host = get_ssh_config_host("testhost", temp_ssh_config)

        assert host is not None
        assert host.hostname == "test.example.com"
        assert host.user == "testuser"

    def test_get_ssh_config_host_not_found(self, temp_ssh_config):
        host = get_ssh_config_host("nonexistent", temp_ssh_config)
        assert host is None
