#!/usr/bin/env python3
"""
Command-line interface for GitStats.
"""

import argparse
import sys

import colorama
from colorama import Fore, Style

from .stats import get_repo_stats
from .display import display_stats
from .identity_cli import setup_identity_parser

# Initialize colorama for cross-platform colored terminal output
colorama.init()

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze Git repository statistics for developers."
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Default command (stats)
    stats_parser = subparsers.add_parser('stats', help='Analyze repository statistics')
    stats_parser.add_argument(
        "repo_path", 
        help="Path to the Git repository to analyze"
    )
    stats_parser.add_argument(
        "--since", 
        help="Only consider commits more recent than this date (format: YYYY-MM-DD)",
        default=None
    )
    stats_parser.add_argument(
        "--until", 
        help="Only consider commits older than this date (format: YYYY-MM-DD)",
        default=None
    )
    stats_parser.add_argument(
        "--branch", 
        help="Analyze only a specific branch",
        default=None
    )
    stats_parser.add_argument(
        "--exclude", 
        help="Comma-separated list of file patterns to exclude",
        default=""
    )
    stats_parser.add_argument(
        "--show-emails", 
        help="Show email addresses in the output table",
        action="store_true"
    )
    stats_parser.set_defaults(func=handle_stats_command)
    
    # For backward compatibility, also allow the repo_path as a positional argument
    parser.add_argument(
        "repo_path_positional", 
        nargs="?",
        help=argparse.SUPPRESS  # Hide from help
    )
    
    # Setup identity management commands
    setup_identity_parser(subparsers)
    
    return parser.parse_args()

def handle_stats_command(args):
    """Handle the stats command."""
    print(f"{Fore.CYAN}Analyzing Git repository at: {args.repo_path}{Style.RESET_ALL}")
    
    # Display filters if any
    filters = []
    if args.since:
        filters.append(f"since {args.since}")
    if args.until:
        filters.append(f"until {args.until}")
    if args.branch:
        filters.append(f"branch '{args.branch}'")
    if args.exclude:
        filters.append(f"excluding {args.exclude}")
        
    if filters:
        print(f"{Fore.CYAN}Filters: {', '.join(filters)}{Style.RESET_ALL}")
    
    # Get and display stats
    stats = get_repo_stats(
        args.repo_path,
        since=args.since,
        until=args.until,
        branch=args.branch,
        exclude=args.exclude
    )
    
    display_stats(stats, show_emails=args.show_emails)

def main():
    """Main function to run the script."""
    args = parse_args()
    
    # Handle backward compatibility for positional repo_path
    if hasattr(args, 'repo_path_positional') and args.repo_path_positional and not hasattr(args, 'command'):
        # If repo_path_positional is provided and no command is specified, use it as repo_path
        args.command = 'stats'
        args.repo_path = args.repo_path_positional
        args.since = None
        args.until = None
        args.branch = None
        args.exclude = ""
        args.show_emails = False
        args.func = handle_stats_command
    
    # If no command is specified but repo_path is, default to stats
    if not hasattr(args, 'command') or not args.command:
        if hasattr(args, 'repo_path'):
            args.command = 'stats'
            args.func = handle_stats_command
        else:
            print(f"{Fore.RED}Error: No command specified.{Style.RESET_ALL}")
            sys.exit(1)
    
    # Call the appropriate function for the command
    if hasattr(args, 'func'):
        args.func(args)
    else:
        print(f"{Fore.RED}Error: Unknown command: {args.command}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main() 