#!/usr/bin/env python3

import argparse
import sys


def main():
    """Main CLI entry point with clean subcommand routing"""

    # Check if first argument is 'profile' - if so, handle profile commands
    if len(sys.argv) > 1 and sys.argv[1] == "profile":
        from .profile import handle_profile_command

        # Create profile parser
        parser = argparse.ArgumentParser(
            prog="ssb profile", description="Manage SSH SLURM server profiles"
        )
        parser.add_argument(
            "--config", help="Config file path (default: ~/.config/ssh-slurm.json)"
        )

        subparsers = parser.add_subparsers(
            dest="profile_command", help="Profile commands"
        )

        # Add profile subcommands
        add_parser = subparsers.add_parser("add", help="Add a new profile")
        add_parser.add_argument("name", help="Profile name")
        add_parser.add_argument(
            "--ssh-host", help="SSH config host name (from ~/.ssh/config)"
        )

        # Direct connection parameters group
        direct_group = add_parser.add_argument_group(
            "Direct connection (use when not using --ssh-host)"
        )
        direct_group.add_argument("--hostname", help="Server hostname")
        direct_group.add_argument("--username", help="SSH username")
        direct_group.add_argument("--key-file", help="SSH private key file path")
        direct_group.add_argument(
            "--port", type=int, default=22, help="SSH port (default: 22)"
        )
        add_parser.add_argument("--description", help="Profile description")

        # Other profile subcommands
        remove_parser = subparsers.add_parser("remove", help="Remove a profile")
        remove_parser.add_argument("name", help="Profile name")

        subparsers.add_parser("list", help="List all profiles")

        set_parser = subparsers.add_parser("set", help="Set current profile")
        set_parser.add_argument("name", help="Profile name")

        show_parser = subparsers.add_parser("show", help="Show profile details")
        show_parser.add_argument(
            "name", nargs="?", help="Profile name (default: current)"
        )

        update_parser = subparsers.add_parser("update", help="Update a profile")
        update_parser.add_argument("name", help="Profile name")
        update_parser.add_argument("--ssh-host", help="SSH config host name")
        update_parser.add_argument("--hostname", help="Server hostname")
        update_parser.add_argument("--username", help="SSH username")
        update_parser.add_argument("--key-file", help="SSH private key file path")
        update_parser.add_argument("--port", type=int, help="SSH port")
        update_parser.add_argument("--description", help="Profile description")

        # Environment variable management
        env_parser = subparsers.add_parser(
            "env", help="Manage environment variables for a profile"
        )
        env_parser.add_argument("name", help="Profile name")
        env_subparsers = env_parser.add_subparsers(
            dest="env_command", help="Environment variable commands"
        )

        env_set_parser = env_subparsers.add_parser(
            "set", help="Set environment variable"
        )
        env_set_parser.add_argument("key", help="Environment variable name")
        env_set_parser.add_argument("value", help="Environment variable value")

        env_unset_parser = env_subparsers.add_parser(
            "unset", help="Unset environment variable"
        )
        env_unset_parser.add_argument("key", help="Environment variable name")

        env_subparsers.add_parser("list", help="List environment variables")

        # Remove 'profile' from argv and parse
        sys.argv = ["ssb profile"] + sys.argv[2:]
        args = parser.parse_args()
        handle_profile_command(args)
        return

    # Default behavior - job submission
    from .submit import main as submit_main

    submit_main()


if __name__ == "__main__":
    main()
