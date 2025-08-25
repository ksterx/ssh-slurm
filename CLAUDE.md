# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ssh-slurm is a Python CLI tool that enables submitting and monitoring SLURM jobs on remote DGX servers via SSH connections. It handles file uploads, proxy connections, and environment setup automatically.

## Architecture

### Core Components

- **SSHSlurmClient** (`src/ssh_slurm/ssh_client.py`): Main client class handling SSH connections, file operations, and SLURM job management
- **ProxySSHClient** (`src/ssh_slurm/proxy_client.py`): Handles SSH ProxyJump connections through bastion hosts  
- **ConfigManager** (`src/ssh_slurm/config.py`): Manages server profiles stored in `~/.config/ssh-slurm.json`
- **SSH Config Parser** (`src/ssh_slurm/ssh_config.py`): Parses `~/.ssh/config` for connection details

### CLI Commands

- **ssb**: Main job submission command (script `src/ssh_slurm/main_cli.py` -> `src/ssh_slurm/cli.py`)
- **ssb profile**: Profile management subcommand (script `src/ssh_slurm/enhanced_profile_cli.py`) 
- **ssproxy**: Proxy connection helper (script `src/ssh_slurm/proxy_helper.py`)
- **ssbatch**: Direct job submission (legacy command, script `src/ssh_slurm/cli.py`)

### Connection Methods (Priority Order)

1. `--host` flag: Uses SSH config host entries
2. `--profile` flag: Uses saved profiles from config file
3. Direct parameters: `--hostname`, `--username`, `--key-file`
4. Current profile: Fallback to default profile if set

### File Handling Logic

- **Local files** (no leading `/`): Uploaded to `/tmp/ssh-slurm/` with random suffix
- **Remote files** (leading `/`): Referenced directly on server
- Executable permissions auto-granted for `.sh`, `.py`, `.pl`, `.r` files
- Cleanup happens automatically unless `--no-cleanup` specified

## Key Development Patterns

### SLURM Environment Discovery

The `_initialize_slurm_paths()` method in SSHSlurmClient attempts multiple strategies:

1. Login shell detection: `bash -l -c 'which sbatch'`
2. Common path search: `/usr/bin`, `/usr/local/bin`, `/opt/slurm/bin`, `/cm/shared/apps/slurm/current/bin`
3. Environment capture from working sbatch session

### Proxy Connection Handling  

Uses paramiko's Channel forwarding for SSH ProxyJump. The ProxySSHClient creates tunnel connections through bastion hosts.

### Error Handling

Critical failure points:
- SLURM path discovery (currently failing - sbatch not in PATH despite detection)
- SSH key authentication 
- File upload permissions
- Remote script existence validation

## Common Development Commands

```bash
# Install in development mode
pip install -e .
# OR with uv
uv pip install -e .

# Run the main CLI
ssb script.sh --host myserver
# OR
uv run ssb script.sh --host myserver

# Profile management  
ssb profile list
ssb profile add myserver --ssh-host dgx1 --description "My DGX server"
ssb profile add direct --hostname dgx.example.com --username user --key-file ~/.ssh/id_rsa
```

## Recent Improvements

1. **SLURM PATH Issue**: ✅ RESOLVED - Enhanced `_execute_slurm_command()` to use full SLURM command paths and proper login shell environment loading.

2. **Environment Variable Support**: ✅ IMPLEMENTED - Added automatic detection and transfer of common environment variables (HF_TOKEN, WANDB_API_KEY, etc.) without requiring manual flags.

3. **Profile Management**: ✅ ENHANCED - Profiles now support both SSH config hosts (via `--ssh-host`) and direct connection parameters. Command changed from `sprofile` to `ssb profile`.

4. **Command Structure**: ✅ UPDATED - Main CLI now uses `ssb` with `profile` subcommand instead of separate `sprofile` command.

## Environment Variable Auto-Detection

The CLI automatically detects and transfers these common environment variables:
- HF_TOKEN, HUGGING_FACE_HUB_TOKEN
- WANDB_API_KEY, WANDB_ENTITY, WANDB_PROJECT
- OPENAI_API_KEY, ANTHROPIC_API_KEY
- CUDA_VISIBLE_DEVICES
- HF_HOME, HF_HUB_CACHE
- TRANSFORMERS_CACHE, TORCH_HOME

No manual `--env-local` flags required for these common variables.

## Dependencies

- **paramiko**: SSH client functionality
- **Python 3.11+**: Required runtime version

## Configuration Files

- **Profile config**: `~/.config/ssh-slurm.json` - Server connection profiles (supports both SSH config hosts and direct connection info)
- **SSH config**: `~/.ssh/config` - Standard SSH configuration (can be referenced in profiles)
- **Temporary uploads**: `/tmp/ssh-slurm/` on remote servers