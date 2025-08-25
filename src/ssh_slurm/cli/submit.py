#!/usr/bin/env python3

import argparse
import logging
import sys
from pathlib import Path

from ..core.client import SSHSlurmClient
from ..core.config import ConfigManager
from ..core.ssh_config import get_ssh_config_host


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=level)


def main():
    parser = argparse.ArgumentParser(
        description="Submit and monitor SLURM jobs via SSH"
    )

    parser.add_argument("script_path", help="Path to sbatch script file")

    # Connection options
    conn_group = parser.add_argument_group("Connection options")
    conn_group.add_argument("--host", "-H", help="SSH host from .ssh/config")
    conn_group.add_argument("--profile", "-p", help="Use saved profile")
    conn_group.add_argument("--hostname", help="DGX server hostname")
    conn_group.add_argument("--username", help="SSH username")
    conn_group.add_argument("--key-file", help="SSH private key file path")
    conn_group.add_argument(
        "--port", type=int, default=22, help="SSH port (default: 22)"
    )
    conn_group.add_argument(
        "--config", help="Config file path (default: ~/.config/ssh-slurm.json)"
    )
    conn_group.add_argument(
        "--ssh-config", help="SSH config file path (default: ~/.ssh/config)"
    )

    # Job options
    job_group = parser.add_argument_group("Job options")
    job_group.add_argument("--job-name", help="Job name")
    job_group.add_argument(
        "--poll-interval",
        "-i",
        type=int,
        default=10,
        help="Job status polling interval in seconds (default: 10)",
    )
    job_group.add_argument(
        "--timeout", type=int, help="Job monitoring timeout in seconds"
    )
    job_group.add_argument(
        "--no-monitor", action="store_true", help="Submit job without monitoring"
    )
    job_group.add_argument(
        "--no-cleanup", action="store_true", help="Do not cleanup uploaded script files"
    )

    # Environment options
    env_group = parser.add_argument_group("Environment options")
    env_group.add_argument(
        "--env",
        action="append",
        metavar="KEY=VALUE",
        help="Pass environment variable to remote job (can be used multiple times)",
    )
    env_group.add_argument(
        "--env-local",
        action="append",
        metavar="KEY",
        help="Pass local environment variable to remote job (can be used multiple times)",
    )

    # Other options
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    # Validate script path
    script_path = Path(args.script_path).resolve()
    if not script_path.exists():
        print(f"Error: Script file '{script_path}' not found", file=sys.stderr)
        sys.exit(1)

    # Determine connection parameters
    try:
        config_manager = ConfigManager(args.config)
        connection_params = {}

        if args.host:
            # Use SSH config host
            ssh_host = get_ssh_config_host(args.host, args.ssh_config)
            if not ssh_host:
                print(f"Error: SSH host '{args.host}' not found", file=sys.stderr)
                sys.exit(1)

            connection_params = {
                "hostname": ssh_host.effective_hostname,
                "username": ssh_host.effective_user,
                "key_filename": ssh_host.effective_identity_file,
                "port": ssh_host.effective_port,
                "proxy_jump": ssh_host.proxy_jump,
            }

        elif args.profile:
            # Use saved profile
            profile = config_manager.get_profile(args.profile)
            if not profile:
                print(f"Error: Profile '{args.profile}' not found", file=sys.stderr)
                sys.exit(1)

            if profile.ssh_host:
                # Profile uses SSH config host
                ssh_host = get_ssh_config_host(profile.ssh_host, args.ssh_config)
                if not ssh_host:
                    print(
                        f"Error: SSH host '{profile.ssh_host}' not found",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                connection_params = {
                    "hostname": ssh_host.effective_hostname,
                    "username": ssh_host.effective_user,
                    "key_filename": ssh_host.effective_identity_file,
                    "port": ssh_host.effective_port,
                    "proxy_jump": ssh_host.proxy_jump,
                }
            else:
                # Profile uses direct connection
                connection_params = {
                    "hostname": profile.hostname,
                    "username": profile.username,
                    "key_filename": profile.key_filename,
                    "port": profile.port,
                }

        elif all([args.hostname, args.username, args.key_file]):
            # Use direct parameters
            key_path = config_manager.expand_path(args.key_file)
            if not Path(key_path).exists():
                print(f"Error: SSH key file '{key_path}' not found", file=sys.stderr)
                sys.exit(1)

            connection_params = {
                "hostname": args.hostname,
                "username": args.username,
                "key_filename": key_path,
                "port": args.port,
            }
        else:
            # Try current profile as fallback
            profile = config_manager.get_current_profile()
            if profile:
                if profile.ssh_host:
                    # Profile uses SSH config host
                    ssh_host = get_ssh_config_host(profile.ssh_host, args.ssh_config)
                    if not ssh_host:
                        print(
                            f"Error: SSH host '{profile.ssh_host}' not found",
                            file=sys.stderr,
                        )
                        sys.exit(1)
                    connection_params = {
                        "hostname": ssh_host.effective_hostname,
                        "username": ssh_host.effective_user,
                        "key_filename": ssh_host.effective_identity_file,
                        "port": ssh_host.effective_port,
                        "proxy_jump": ssh_host.proxy_jump,
                    }
                else:
                    # Profile uses direct connection
                    connection_params = {
                        "hostname": profile.hostname,
                        "username": profile.username,
                        "key_filename": profile.key_filename,
                        "port": profile.port,
                    }
            else:
                print("Error: No connection method specified", file=sys.stderr)
                print(
                    "Use --host, --profile, or provide --hostname/--username/--key-file",
                    file=sys.stderr,
                )
                sys.exit(1)

        # Process environment variables
        import os

        env_vars = {}

        # Auto-detect common environment variables
        common_env_vars = [
            "HF_TOKEN",
            "HUGGING_FACE_HUB_TOKEN",
            "WANDB_API_KEY",
            "WANDB_ENTITY",
            "WANDB_PROJECT",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "CUDA_VISIBLE_DEVICES",
            "HF_HOME",
            "HF_HUB_CACHE",
            "TRANSFORMERS_CACHE",
            "TORCH_HOME",
        ]

        for key in common_env_vars:
            if key in os.environ:
                env_vars[key] = os.environ[key]
                if args.verbose:
                    print(f"Auto-detected environment variable: {key}")

        # Add explicitly provided environment variables
        if args.env:
            for env_var in args.env:
                if "=" not in env_var:
                    print(
                        f"Error: Invalid environment variable format: {env_var}",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                key, value = env_var.split("=", 1)
                env_vars[key] = value

        # Add explicitly requested local environment variables
        if args.env_local:
            for key in args.env_local:
                if key in os.environ:
                    env_vars[key] = os.environ[key]
                else:
                    print(
                        f"Warning: Local environment variable '{key}' not found",
                        file=sys.stderr,
                    )

        # Create client and connect
        client = SSHSlurmClient(env_vars=env_vars, **connection_params)

        if not client.connect():
            print("Error: Failed to connect to server", file=sys.stderr)
            print(
                "Please check your connection parameters and SSH credentials",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            # Submit job
            job = client.submit_sbatch_file(
                script_path=str(script_path),
                job_name=args.job_name,
                cleanup=not args.no_cleanup,
            )

            if not job:
                print("Error: Failed to submit job", file=sys.stderr)
                sys.exit(1)

            print(f"Job submitted: {job.job_id}")

            # Monitor job if requested
            if not args.no_monitor:
                print(f"Monitoring job {job.job_id}...")
                final_status = client.monitor_job(
                    job, poll_interval=args.poll_interval, timeout=args.timeout
                )
                print(f"Job {job.job_id} finished with status: {final_status}")

        finally:
            # Always disconnect
            client.disconnect()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
