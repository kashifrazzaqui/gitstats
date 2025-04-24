"""
Command-line interface for identity management.
"""

import argparse
import os
import sys

from colorama import Fore, Style
from tabulate import tabulate

from .identity import (add_identity_mapping, exclude_developer,
                       get_excluded_developers, get_identity_file,
                       include_developer, list_identity_mappings,
                       remove_identity_mapping)


def handle_identity_command(args):
    """Handle the identity management command."""
    if args.identity_command == "add":
        # Add an identity mapping
        if add_identity_mapping(
            args.repo_path, args.name_or_email, args.canonical_identity
        ):
            print(f"{Fore.GREEN}Successfully added identity mapping:{Style.RESET_ALL}")
            print(f"  {args.name_or_email} -> {args.canonical_identity}")
        else:
            print(f"{Fore.RED}Failed to add identity mapping.{Style.RESET_ALL}")
            sys.exit(1)

    elif args.identity_command == "remove":
        # Remove an identity mapping
        if remove_identity_mapping(args.repo_path, args.name_or_email):
            print(
                f"{Fore.GREEN}Successfully removed identity mapping for {args.name_or_email}.{Style.RESET_ALL}"
            )
        else:
            print(f"{Fore.RED}Failed to remove identity mapping.{Style.RESET_ALL}")
            sys.exit(1)

    elif args.identity_command == "list":
        # List all identity mappings
        mappings = list_identity_mappings(args.repo_path)

        # Check if there are any mappings
        if not mappings["canonical_names"] and not mappings["canonical_emails"]:
            print(
                f"{Fore.YELLOW}No identity mappings found for {args.repo_path}.{Style.RESET_ALL}"
            )
            print(
                f"Use 'gitstats identity add <repo_path> <name_or_email> <canonical_identity>' to add a mapping."
            )
            return

        # Display the mappings
        print(f"{Fore.CYAN}Identity mappings for {args.repo_path}:{Style.RESET_ALL}")
        print(f"Configuration file: {get_identity_file(args.repo_path)}")

        # Display name mappings
        if mappings["canonical_names"]:
            print(f"\n{Fore.CYAN}Name mappings:{Style.RESET_ALL}")
            name_table = [
                [name, canonical]
                for name, canonical in mappings["canonical_names"].items()
            ]
            print(
                tabulate(
                    name_table, headers=["Name", "Canonical Identity"], tablefmt="grid"
                )
            )

        # Display email mappings
        if mappings["canonical_emails"]:
            print(f"\n{Fore.CYAN}Email mappings:{Style.RESET_ALL}")
            email_table = [
                [email, canonical]
                for email, canonical in mappings["canonical_emails"].items()
            ]
            print(
                tabulate(
                    email_table,
                    headers=["Email", "Canonical Identity"],
                    tablefmt="grid",
                )
            )

        # Display excluded developers
        excluded_developers = get_excluded_developers(args.repo_path)
        if excluded_developers:
            print(f"\n{Fore.CYAN}Excluded developers:{Style.RESET_ALL}")
            excluded_table = [[dev] for dev in excluded_developers]
            print(tabulate(excluded_table, headers=["Name/Email"], tablefmt="grid"))

    elif args.identity_command == "exclude":
        # Exclude a developer from analysis
        if exclude_developer(args.repo_path, args.name_or_email):
            print(
                f"{Fore.GREEN}Successfully excluded developer '{args.name_or_email}' from analysis.{Style.RESET_ALL}"
            )
        else:
            print(f"{Fore.RED}Failed to exclude developer.{Style.RESET_ALL}")
            sys.exit(1)

    elif args.identity_command == "include":
        # Include a previously excluded developer
        if include_developer(args.repo_path, args.name_or_email):
            print(
                f"{Fore.GREEN}Successfully included developer '{args.name_or_email}' in analysis.{Style.RESET_ALL}"
            )
        else:
            print(f"{Fore.RED}Failed to include developer.{Style.RESET_ALL}")
            sys.exit(1)

    else:
        print(
            f"{Fore.RED}Unknown identity command: {args.identity_command}{Style.RESET_ALL}"
        )
        sys.exit(1)


def setup_identity_parser(subparsers):
    """Set up the identity management command parser."""
    identity_parser = subparsers.add_parser(
        "identity", help="Manage author identity mappings"
    )

    # Create subparsers for identity commands
    identity_subparsers = identity_parser.add_subparsers(
        dest="identity_command", help="Identity management command"
    )

    # Add command
    add_parser = identity_subparsers.add_parser("add", help="Add an identity mapping")
    add_parser.add_argument("repo_path", help="Path to the Git repository")
    add_parser.add_argument("name_or_email", help="Author name or email address to map")
    add_parser.add_argument("canonical_identity", help="Canonical identity to map to")

    # Remove command
    remove_parser = identity_subparsers.add_parser(
        "remove", help="Remove an identity mapping"
    )
    remove_parser.add_argument("repo_path", help="Path to the Git repository")
    remove_parser.add_argument(
        "name_or_email", help="Author name or email address to remove mapping for"
    )

    # List command
    list_parser = identity_subparsers.add_parser(
        "list", help="List all identity mappings for a repository"
    )
    list_parser.add_argument("repo_path", help="Path to the Git repository")

    # Exclude command
    exclude_parser = identity_subparsers.add_parser(
        "exclude", help="Exclude a developer from analysis"
    )
    exclude_parser.add_argument("repo_path", help="Path to the Git repository")
    exclude_parser.add_argument(
        "name_or_email", help="Developer name or email address to exclude"
    )

    # Include command
    include_parser = identity_subparsers.add_parser(
        "include", help="Include a previously excluded developer in analysis"
    )
    include_parser.add_argument("repo_path", help="Path to the Git repository")
    include_parser.add_argument(
        "name_or_email", help="Developer name or email address to include"
    )

    # Set the handler function
    identity_parser.set_defaults(func=handle_identity_command)
