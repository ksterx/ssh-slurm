# SSH SLURM Client

A Python library and CLI tool for submitting and monitoring SLURM jobs on DGX servers via SSH.

## Features

- SLURM job submission via SSH connections
- Automatic job ID extraction
- Periodic job status monitoring
- Job log output retrieval
- **File handling**:
  - Local files: Automatically uploaded to server's temporary folder (/tmp/ssh-slurm) and executed
  - Remote files: Direct execution of existing files on server (specified with absolute path)
- **Connection management**:
  - `.ssh/config` support
  - Custom profile management (SSH config hosts or direct connection info)
- **Automatic environment variable transfer**:
  - Auto-detection and transfer of common environment variables like HF_TOKEN, WANDB_API_KEY, etc.
- Available as both CLI tool and Python library

## Installation

```bash
pip install -e .
```

## Usage

### As CLI Tool

#### Basic Usage

```bash
# Execute local script file
ssb my_script.sh --host dgx1

# Execute remote script file
ssb /home/user/scripts/remote_script.sh --host dgx1

# Use profile
ssb my_script.sh --profile dgx1

# Use SSH config settings
ssb my_script.sh --host my-dgx-server

# Direct specification
ssb my_script.sh --hostname dgx.example.com --username user --key-file ~/.ssh/id_rsa
```

#### Detailed Options

```bash
# Verbose logging, job name specification, monitoring interval
ssb script.sh --host dgx1 --job-name my_job --poll-interval 5 --verbose

# Don't delete uploaded files
ssb script.sh --host dgx1 --no-cleanup

# Submit job without monitoring
ssb script.sh --host dgx1 --no-monitor

# Environment variables are automatically detected and transferred (HF_TOKEN, WANDB_API_KEY, etc.)
ssb script.sh --host dgx1

# Additionally pass local environment variables
ssb script.sh --host dgx1 --env-local CUSTOM_TOKEN

# Set custom environment variables
ssb script.sh --host dgx1 --env "CUSTOM_VAR=value" --env "DEBUG=true"

# Combined usage
ssb script.sh --host dgx1 --env-local CUSTOM_TOKEN --env "MODEL_NAME=llama3" --verbose
```

### Profile Management

#### Adding Profiles

**Using SSH config host:**
```bash
# Specify host configured in SSH config
ssb profile add dgx1 --ssh-host my-dgx-host --description "DGX-1 server"
```

**Specifying direct connection info:**
```bash
ssb profile add dgx1 --hostname dgx1.example.com --username user --key-file ~/.ssh/id_rsa --description "DGX-1 server"
ssb profile add dgx2 --hostname dgx2.example.com --username user --key-file ~/.ssh/id_rsa --port 2222 --description "DGX-2 server"
```

#### Profile List and Management

```bash
# List profiles
ssb profile list

# Set current profile
ssb profile set dgx1

# Show profile details
ssb profile show dgx1

# Update profile
ssb profile update dgx1 --hostname new-dgx1.example.com

# Change to SSH config host
ssb profile update dgx1 --ssh-host my-dgx-host

# Remove profile
ssb profile remove dgx1
```

### Using SSH Config

You can utilize settings described in `~/.ssh/config`:

```
Host dgx1
    HostName dgx1.example.com
    User username
    Port 22
    IdentityFile ~/.ssh/id_rsa

Host dgx-a100
    HostName 192.168.1.100
    User gpu_user
    Port 2222
    IdentityFile ~/.ssh/dgx_key
```

Usage examples:
```bash
ssb my_script.sh --host dgx1
ssb my_script.sh --host dgx-a100
```

### As Python Library

```python
from ssh_slurm import SSHSlurmClient
from ssh_slurm.config import ConfigManager
from ssh_slurm.ssh_config import get_ssh_config_host

# Get settings from SSH config
ssh_host = get_ssh_config_host("dgx1")

# Create client
with SSHSlurmClient(
    hostname=ssh_host.effective_hostname,
    username=ssh_host.effective_user,
    key_filename=ssh_host.effective_identity_file,
    port=ssh_host.effective_port
) as client:
    
    # Submit local file
    job = client.submit_sbatch_file("./my_script.sh", job_name="test_job")
    
    # Or submit remote file
    job = client.submit_sbatch_file("/home/user/remote_script.sh", job_name="remote_job")
    
    if job:
        print(f"Job submitted: {job.job_id}")
        if job.is_local_script:
            print(f"Script uploaded to: {job.script_path}")
        
        # Monitor job
        job = client.monitor_job(job, poll_interval=10)
        
        # Get results
        stdout, stderr = client.get_job_output(job.job_id)
        print(f"Output: {stdout}")
        
        # Cleanup
        client.cleanup_job_files(job)
```

## File Handling

### Local Files
- Specified with relative or absolute path (not starting with `/`)
- Automatically uploaded to server's `/tmp/ssh-slurm/`
- Executable permissions automatically granted (.sh, .py, .pl, .r files)
- Automatically deleted after job completion (can be disabled with `--no-cleanup`)

### Remote Files
- Specified with absolute path (starting with `/`)
- Direct execution of existing files on server
- File existence verification performed

## Configuration Files

### Profile Settings (~/.config/ssh-slurm.json)

```json
{
  "current_profile": "dgx1",
  "profiles": {
    "dgx1": {
      "hostname": "dgx1.example.com",
      "username": "user",
      "key_filename": "/home/user/.ssh/id_rsa",
      "port": 22,
      "description": "DGX-1 server",
      "ssh_host": null
    },
    "dgx2": {
      "hostname": "dgx2.internal.com",
      "username": "gpuuser",
      "key_filename": "/home/user/.ssh/dgx_key",
      "port": 22,
      "description": "DGX-2 via SSH config",
      "ssh_host": "dgx2-internal"
    }
  }
}
```

### SSH Config (~/.ssh/config)

Supports standard SSH configuration files:

```
Host pattern
    HostName hostname
    User username
    Port port
    IdentityFile ~/.ssh/key_file
    ProxyJump jump_host
    # Other SSH settings
```

## Security

- **Passwords are not stored in configuration files**
- Only SSH private key file authentication is supported
- Uploaded files are temporarily stored on server and deleted after completion

## Command Reference

### ssb (Job Execution)

```bash
ssb <script_path> [options]

Connection options:
  --host, -H          SSH host from .ssh/config
  --profile, -p       Use saved profile  
  --hostname          DGX server hostname
  --username          SSH username
  --key-file          SSH private key file path
  --port              SSH port (default: 22)
  --ssh-config        SSH config file path (default: ~/.ssh/config)

Job options:
  --job-name          Job name
  --poll-interval     Job status polling interval in seconds (default: 10)
  --timeout           Job monitoring timeout in seconds
  --no-monitor        Submit job without monitoring
  --no-cleanup        Do not cleanup uploaded script files

Environment options:
  --env KEY=VALUE     Pass environment variable to remote job (can be used multiple times)
  --env-local KEY     Pass local environment variable to remote job (can be used multiple times)
  
  Note: Common environment variables (HF_TOKEN, WANDB_API_KEY, etc.) are automatically detected and transferred

Other options:
  --verbose, -v       Enable verbose logging
```

### ssb profile (Profile Management)

```bash
ssb profile <command> [options]

Commands:
  add <name>        - Add a new profile
    --ssh-host      Use SSH config host
    --hostname      Direct hostname (requires --username, --key-file)
    --username      SSH username
    --key-file      SSH key file path
    --port          SSH port (default: 22)
    --description   Profile description
    
  list              - List all profiles
  set <name>        - Set current profile
  show [name]       - Show profile details
  update <name>     - Update a profile
  remove <name>     - Remove a profile
```

## Usage Examples

```bash
# Use SSH config host
ssb train.sh --host dgx1

# Use profile
ssb train.sh --profile my-dgx

# Execute remote script
ssb /shared/scripts/training.sh --host dgx1

# Detailed settings
ssb local_script.sh --host dgx1 --job-name training_job --poll-interval 30 --verbose
```

## Dependencies

- Python 3.13+
- paramiko 4.0.0+

## License

MIT