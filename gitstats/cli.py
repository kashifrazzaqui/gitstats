#!/usr/bin/env python3
"""
Command-line interface for GitStats.
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import colorama
from colorama import Fore, Style

from .stats import get_repo_stats, is_workday, count_workdays
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
        "repo_paths", 
        nargs='+',
        help="Path(s) to the Git repository/repositories to analyze"
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
        "--all-commits",
        action="store_true",
        help="Analyze all commits instead of only the last 30 days"
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
    stats_parser.add_argument(
        "--exclude-developers", 
        help="Comma-separated list of developer names or emails to exclude from analysis",
        default=""
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

def merge_stats(stats_list):
    """Merge statistics from multiple repositories."""
    # Initialize merged stats
    merged_stats = defaultdict(lambda: {
        'name': set(),
        'email': set(),
        'commits': 0,
        'lines_added': 0,
        'lines_deleted': 0,
        'net_lines': 0,
        'files_changed': 0,
        'first_commit': None,
        'last_commit': None,
        'commit_dates': [],
        'commit_days': defaultdict(int),
        'commit_weeks': defaultdict(int),
        'commit_months': defaultdict(int)
    })
    
    # Merge stats from each repository
    for stats in stats_list:
        for identity, data in stats.items():
            # Merge basic stats
            merged_stats[identity]['name'].update(data['name'] if isinstance(data['name'], set) else {data['name']})
            merged_stats[identity]['email'].update(data['email'] if isinstance(data['email'], set) else {data['email']})
            merged_stats[identity]['commits'] += data['commits']
            merged_stats[identity]['lines_added'] += data['lines_added']
            merged_stats[identity]['lines_deleted'] += data['lines_deleted']
            merged_stats[identity]['net_lines'] += data['net_lines']
            merged_stats[identity]['files_changed'] += data['files_changed']
            merged_stats[identity]['commit_dates'].extend(data['commit_dates'])
            
            # Merge commit frequency data
            for day, count in data['commit_days'].items():
                merged_stats[identity]['commit_days'][day] += count
            
            for week, count in data['commit_weeks'].items():
                merged_stats[identity]['commit_weeks'][week] += count
            
            for month, count in data['commit_months'].items():
                merged_stats[identity]['commit_months'][month] += count
            
            # Update first and last commit dates
            if (merged_stats[identity]['first_commit'] is None or 
                (data['first_commit'] is not None and data['first_commit'] < merged_stats[identity]['first_commit'])):
                merged_stats[identity]['first_commit'] = data['first_commit']
            
            if (merged_stats[identity]['last_commit'] is None or 
                (data['last_commit'] is not None and data['last_commit'] > merged_stats[identity]['last_commit'])):
                merged_stats[identity]['last_commit'] = data['last_commit']
    
    # Get today's date for frequency calculations
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Recalculate frequency metrics for each developer
    for identity, data in merged_stats.items():
        if data['first_commit']:
            # Calculate total days from first commit to today (not just to last commit)
            total_days = (today - data['first_commit']).days + 1
            
            # Calculate days with commits
            days_with_commits = len(data['commit_days'])
            
            # Calculate weeks with commits
            weeks_with_commits = len(data['commit_weeks'])
            
            # Calculate months with commits
            months_with_commits = len(data['commit_months'])
            
            # Calculate commit frequency metrics
            data['total_days'] = total_days
            data['days_with_commits'] = days_with_commits
            data['commit_day_ratio'] = days_with_commits / total_days if total_days > 0 else 0
            
            # Calculate weeks in the date range using ISO calendar weeks
            first_week = data['first_commit'].isocalendar()[1]
            first_year = data['first_commit'].isocalendar()[0]
            today_week = today.isocalendar()[1]
            today_year = today.isocalendar()[0]
            
            # Calculate total weeks between first commit and today
            if first_year == today_year:
                total_weeks = today_week - first_week + 1
            else:
                # Handle spanning multiple years
                years_between = today_year - first_year - 1  # Years between (not including first and last)
                weeks_in_first_year = datetime(first_year, 12, 28).isocalendar()[1] - first_week + 1  # Weeks from first week to end of year
                weeks_in_last_year = today_week  # Weeks from start of year to today
                total_weeks = weeks_in_first_year + (years_between * 52) + weeks_in_last_year
            
            data['total_weeks'] = total_weeks
            data['weeks_with_commits'] = weeks_with_commits
            data['commit_week_ratio'] = weeks_with_commits / total_weeks if total_weeks > 0 else 0
            
            # Calculate months in the date range
            first_month = data['first_commit'].year * 12 + data['first_commit'].month
            today_month = today.year * 12 + today.month
            total_months = today_month - first_month + 1
            data['total_months'] = total_months
            data['months_with_commits'] = months_with_commits
            data['commit_month_ratio'] = months_with_commits / total_months if total_months > 0 else 0
            
            # Calculate average gap between commits
            if len(data['commit_dates']) > 1:
                sorted_dates = sorted(data['commit_dates'])
                gaps = [(sorted_dates[i+1] - sorted_dates[i]).total_seconds() / 86400 for i in range(len(sorted_dates)-1)]
                data['avg_gap_days'] = sum(gaps) / len(gaps)
                data['max_gap_days'] = max(gaps)
                
                # Calculate workday-aware metrics
                workday_gaps = []
                for i in range(len(sorted_dates)-1):
                    start = sorted_dates[i]
                    end = sorted_dates[i+1]
                    workday_gap = count_workdays(start, end) - 1  # -1 because we don't count the commit day
                    if workday_gap < 0:  # Handles same-day commits
                        workday_gap = 0
                    workday_gaps.append(workday_gap)
                
                data['workday_gaps'] = workday_gaps
                data['avg_workday_gap'] = sum(workday_gaps) / len(workday_gaps) if workday_gaps else 0
                
                # Calculate weekday vs weekend commit ratio
                weekday_commits = sum(1 for date in data['commit_dates'] if is_workday(date))
                total_commits = len(data['commit_dates'])
                data['weekday_commit_ratio'] = weekday_commits / total_commits if total_commits > 0 else 0
            else:
                data['avg_gap_days'] = 0
                data['max_gap_days'] = 0
                data['workday_gaps'] = []
                data['avg_workday_gap'] = 0
                
                # For a single commit, set weekday ratio based on if it's a workday
                if data['commit_dates']:
                    data['weekday_commit_ratio'] = 1.0 if is_workday(data['commit_dates'][0]) else 0.0
                else:
                    data['weekday_commit_ratio'] = 0.0
            
            # Calculate daily aggregation gap metrics
            if len(data['commit_days']) > 1:
                # Convert day strings to datetime objects
                sorted_active_days = sorted([datetime.strptime(day, '%Y-%m-%d') for day in data['commit_days'].keys()])
                
                # Calculate gaps between active days in days
                active_day_gaps = [(sorted_active_days[i+1] - sorted_active_days[i]).days 
                                 for i in range(len(sorted_active_days)-1)]
                
                # Calculate metrics
                data['active_day_gaps'] = active_day_gaps
                data['avg_active_day_gap'] = sum(active_day_gaps) / len(active_day_gaps)
                data['max_active_day_gap'] = max(active_day_gaps)
                
                # Calculate streak-to-gap ratio
                total_streak_days = 0
                total_gap_days = 0
                current_streak = 1
                
                # Calculate streaks and gaps
                for i in range(1, len(sorted_active_days)):
                    gap_days = (sorted_active_days[i] - sorted_active_days[i-1]).days
                    
                    if gap_days == 1:  # Consecutive days
                        current_streak += 1
                    else:  # Streak broken
                        total_streak_days += current_streak
                        total_gap_days += gap_days - 1  # -1 because the end date is counted in the next streak
                        current_streak = 1
                
                # Add the last streak
                total_streak_days += current_streak
                
                # Calculate ratio
                data['total_streak_days'] = total_streak_days
                data['total_gap_days'] = total_gap_days
                data['streak_gap_ratio'] = total_streak_days / (total_gap_days + 1) if total_gap_days > 0 else total_streak_days
            else:
                data['active_day_gaps'] = []
                data['avg_active_day_gap'] = 0
                data['max_active_day_gap'] = 0
                data['total_streak_days'] = len(data['commit_days'])
                data['total_gap_days'] = 0
                data['streak_gap_ratio'] = len(data['commit_days'])
            
            # Calculate commit streak metrics
            sorted_days = sorted(data['commit_days'].keys())
            if sorted_days:
                # Current streak
                current_streak = 1
                max_streak = 1
                
                for i in range(1, len(sorted_days)):
                    prev_day = datetime.strptime(sorted_days[i-1], '%Y-%m-%d')
                    curr_day = datetime.strptime(sorted_days[i], '%Y-%m-%d')
                    
                    # Calculate days difference
                    days_diff = (curr_day - prev_day).days
                    
                    # Check if consecutive or over a weekend (Friday to Monday = 3 days)
                    # Friday is weekday 4, Monday is weekday 0
                    is_over_weekend = days_diff <= 3 and prev_day.weekday() == 4 and curr_day.weekday() == 0
                    
                    if days_diff == 1 or is_over_weekend:
                        current_streak += 1
                        max_streak = max(max_streak, current_streak)
                    else:
                        current_streak = 1
                
                data['max_streak'] = max_streak
            else:
                data['max_streak'] = 0
            
            # Choose the most common name for display
            from collections import Counter
            name_counter = Counter(data['name'])
            data['display_name'] = name_counter.most_common(1)[0][0]
    
    return dict(merged_stats)

def handle_stats_command(args):
    """Handle the stats command."""
    # For backward compatibility, handle positional argument
    if args.repo_path_positional and not args.repo_paths:
        args.repo_paths = [args.repo_path_positional]
    
    # Check if we have at least one repo
    if not args.repo_paths:
        print(f"{Fore.RED}Error: You must specify at least one repository path.{Style.RESET_ALL}")
        sys.exit(1)
    
    # Parse excluded file patterns
    excluded_patterns = [pattern.strip() for pattern in args.exclude.split(',') if pattern.strip()]
    
    # Parse excluded developers
    excluded_developers = [dev.strip() for dev in args.exclude_developers.split(',') if dev.strip()]
    
    # Determine date range
    since = args.since
    until = args.until
    
    # Check if we should limit to last 30 days
    if not args.all_commits and not args.since:
        # Calculate date 30 days ago
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        args.since = thirty_days_ago
        print(f"{Fore.CYAN}Note: Only analyzing commits from the last 30 days. Use --all-commits to analyze all commits.{Style.RESET_ALL}")
    
    # Check if we have multiple repositories
    if len(args.repo_paths) > 1:
        print(f"{Fore.CYAN}Analyzing {len(args.repo_paths)} Git repositories:{Style.RESET_ALL}")
        for repo_path in args.repo_paths:
            print(f"  - {repo_path}")
    else:
        print(f"{Fore.CYAN}Analyzing Git repository at: {args.repo_paths[0]}{Style.RESET_ALL}")
    
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
    
    # Process each repository
    stats_list = []
    for repo_path in args.repo_paths:
        print(f"\n{Fore.CYAN}Analyzing repository: {repo_path}{Style.RESET_ALL}")
        try:
            repo_stats = get_repo_stats(
                repo_path, 
                since=since, 
                until=until, 
                branch=args.branch, 
                exclude=excluded_patterns,
                exclude_developers=excluded_developers
            )
            stats_list.append(repo_stats)
        except Exception as e:
            print(f"{Fore.RED}Error analyzing repository {repo_path}: {str(e)}{Style.RESET_ALL}")
            continue
    
    # Merge stats if we have multiple repositories
    if len(stats_list) > 1:
        merged_stats = merge_stats(stats_list)
        display_stats(merged_stats, show_emails=args.show_emails, is_merged=True)
    elif len(stats_list) == 1:
        display_stats(stats_list[0], show_emails=args.show_emails)
    else:
        print(f"{Fore.RED}No valid repositories to analyze.{Style.RESET_ALL}")

def main():
    """Main function to run the script."""
    args = parse_args()
    
    # Handle backward compatibility for positional repo_path
    if hasattr(args, 'repo_path_positional') and args.repo_path_positional and not hasattr(args, 'command'):
        # If repo_path_positional is provided and no command is specified, use it as repo_path
        args.command = 'stats'
        args.repo_paths = [args.repo_path_positional]
        args.since = None
        args.until = None
        args.branch = None
        args.exclude = ""
        args.show_emails = False
        args.all_commits = False
        args.func = handle_stats_command
    
    # If no command is specified but repo_path is, default to stats
    if not hasattr(args, 'command') or not args.command:
        if hasattr(args, 'repo_paths'):
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