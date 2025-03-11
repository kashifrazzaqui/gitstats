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

# Initialize colorama for cross-platform colored terminal output
colorama.init()

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze Git repository statistics for developers."
    )
    parser.add_argument(
        "repo_path", 
        help="Path to the Git repository to analyze"
    )
    parser.add_argument(
        "--since", 
        help="Only consider commits more recent than this date (format: YYYY-MM-DD)",
        default=None
    )
    parser.add_argument(
        "--until", 
        help="Only consider commits older than this date (format: YYYY-MM-DD)",
        default=None
    )
    parser.add_argument(
        "--branch", 
        help="Analyze only a specific branch",
        default=None
    )
    parser.add_argument(
        "--exclude", 
        help="Comma-separated list of file patterns to exclude",
        default=""
    )
    return parser.parse_args()

def main():
    """Main function to run the script."""
    args = parse_args()
    
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
    
    display_stats(stats)

if __name__ == "__main__":
    main() 