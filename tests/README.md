# SSH-SLURM Test Suite

This directory contains comprehensive tests for the ssh-slurm package using pytest.

## Test Coverage

### Core Components Tested

#### 1. Configuration Management (`test_config.py`)
- **ServerProfile class**:
  - Profile creation with basic and full parameters
  - Dictionary serialization/deserialization
  - SSH host configuration support
  
- **ConfigManager class**:
  - Configuration file loading and saving
  - Profile CRUD operations (Create, Read, Update, Delete)
  - Current profile management
  - Error handling for invalid configs and file permissions
  - Path expansion for SSH keys

#### 2. SSH Configuration Parsing (`test_ssh_config.py`)
- **SSHHost class**:
  - Host configuration with all SSH parameters
  - Effective property calculation (defaults, path expansion)
  - Proxy configuration support
  
- **SSHConfigParser class**:
  - SSH config file parsing with comments and empty lines
  - Host pattern matching (wildcards, exact matches)
  - Boolean value parsing
  - Case-insensitive parsing
  - Identity file discovery
  - ProxyJump and ProxyCommand support

## Test Files

- `test_config.py` - Configuration management tests (23 tests)
- `test_ssh_config.py` - SSH config parsing tests (27 tests)
- `pytest.ini` - pytest configuration
- `__init__.py` - Test package marker

## Running Tests

```bash
# Run all tests
uv run pytest tests/

# Run with verbose output
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_config.py -v

# Run specific test
uv run pytest tests/test_config.py::TestConfigManager::test_add_profile -v
```

## Test Results

Current test suite: **50 tests, all passing** ✅

- Configuration management: 23/23 passing
- SSH config parsing: 27/27 passing

## Key Test Features

1. **Temporary file fixtures** - Tests use temporary files for isolation
2. **Mocking** - External dependencies are mocked appropriately  
3. **Error scenarios** - Tests cover both success and failure paths
4. **Edge cases** - Handles malformed configs, missing files, permission errors
5. **Integration scenarios** - Tests realistic usage patterns

## Future Test Additions

For complete coverage, these areas could be added:

1. **SSH Client tests** - Connection handling, job submission, monitoring
2. **CLI tests** - Argument parsing, command routing, error handling
3. **Proxy client tests** - ProxyJump connection handling
4. **End-to-end integration tests** - Full workflow testing with mocked SSH

The current test suite provides solid coverage of the core configuration and SSH config parsing functionality, ensuring reliability of the most critical components.