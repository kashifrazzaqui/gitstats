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

from .display import display_stats
from .identity_cli import setup_identity_parser
from .stats import count_workdays, get_repo_stats, is_workday

# Initialize colorama for cross-platform colored terminal output
colorama.init()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze Git repository statistics for developers."
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Default command (stats)
    stats_parser = subparsers.add_parser("stats", help="Analyze repository statistics")
    stats_parser.add_argument(
        "repo_paths",
        nargs="+",
        help="Path(s) to the Git repository/repositories to analyze",
    )
    stats_parser.add_argument(
        "--since",
        help="Only consider commits more recent than this date (format: YYYY-MM-DD)",
        default=None,
    )
    stats_parser.add_argument(
        "--until",
        help="Only consider commits older than this date (format: YYYY-MM-DD)",
        default=None,
    )
    stats_parser.add_argument(
        "--all-commits",
        action="store_true",
        help="Analyze all commits instead of only the last 30 days",
    )
    stats_parser.add_argument(
        "--branch", help="Analyze only a specific branch", default=None
    )
    stats_parser.add_argument(
        "--exclude", help="Comma-separated list of file patterns to exclude", default=""
    )
    stats_parser.add_argument(
        "--show-emails",
        help="Show email addresses in the output table",
        action="store_true",
    )
    stats_parser.add_argument(
        "--exclude-developers",
        help="Comma-separated list of developer names or emails to exclude from analysis",
        default="",
    )
    stats_parser.add_argument(
        "--verbose",
        help="Show detailed debug information during analysis",
        action="store_true",
    )
    stats_parser.set_defaults(func=handle_stats_command)

    # For backward compatibility, also allow the repo_path as a positional argument
    parser.add_argument(
        "repo_path_positional", nargs="?", help=argparse.SUPPRESS  # Hide from help
    )

    # Setup identity management commands
    setup_identity_parser(subparsers)

    return parser.parse_args()


def merge_stats(stats_list, since, verbose=False):
    """Merge statistics from multiple repositories."""
    # Initialize merged stats
    merged_stats = defaultdict(
        lambda: {
            "name": set(),
            "email": set(),
            "commits": 0,
            "lines_added": 0,
            "lines_deleted": 0,
            "net_lines": 0,
            "files_changed": 0,
            "first_commit": None,
            "last_commit": None,
            "commit_dates": [],
            "commit_days": defaultdict(int),
            "commit_weeks": defaultdict(int),
            "commit_months": defaultdict(int),
            "commit_hashes": set(),  # Use a set to avoid duplicate hashes
        }
    )

    # Merge stats from each repository
    repo_index = 0
    commit_hash_tracker = defaultdict(list)  # Track commit hashes to detect duplicates

    for stats in stats_list:
        repo_index += 1

        if verbose:
            print(
                f"\n{Fore.CYAN}Merging stats from repository #{repo_index}:{Style.RESET_ALL}"
            )

        for identity, data in stats.items():
            if verbose:
                print(f"  Processing developer: {identity} - {data['commits']} commits")

            # Merge basic stats
            merged_stats[identity]["name"].update(
                data["name"] if isinstance(data["name"], set) else {data["name"]}
            )
            merged_stats[identity]["email"].update(
                data["email"] if isinstance(data["email"], set) else {data["email"]}
            )

            # Track individual commit hashes to avoid duplicates
            prev_hash_count = len(merged_stats[identity]["commit_hashes"])

            if "commit_hashes" in data:
                # For backward compatibility, handle both list and set
                hashes_to_add = (
                    set(data["commit_hashes"])
                    if isinstance(data["commit_hashes"], list)
                    else data["commit_hashes"]
                )
                merged_stats[identity]["commit_hashes"].update(hashes_to_add)

                # Track hashes for detailed duplicate detection
                for commit_hash in hashes_to_add:
                    commit_hash_tracker[commit_hash].append((repo_index, identity))

            # Update commit count based on unique hashes, not by simply adding counts
            new_hash_count = len(merged_stats[identity]["commit_hashes"])
            commits_added = new_hash_count - prev_hash_count

            if verbose:
                if commits_added != data["commits"]:
                    print(
                        f"    {Fore.YELLOW}Adding {commits_added} unique commits (skipped {data['commits'] - commits_added} duplicates) -> new total: {new_hash_count}{Style.RESET_ALL}"
                    )
                else:
                    print(
                        f"    Adding {commits_added} commits -> new total: {new_hash_count}"
                    )

            # Use unique hash count as the true commit count
            merged_stats[identity]["commits"] = len(
                merged_stats[identity]["commit_hashes"]
            )

            merged_stats[identity]["lines_added"] += data["lines_added"]
            merged_stats[identity]["lines_deleted"] += data["lines_deleted"]
            merged_stats[identity]["net_lines"] += data["net_lines"]
            merged_stats[identity]["files_changed"] += data["files_changed"]

            # Only add unique commit dates
            existing_dates = {
                date.strftime("%Y-%m-%d %H:%M:%S")
                for date in merged_stats[identity]["commit_dates"]
            }
            for date in data["commit_dates"]:
                date_str = date.strftime("%Y-%m-%d %H:%M:%S")
                if date_str not in existing_dates:
                    merged_stats[identity]["commit_dates"].append(date)
                    existing_dates.add(date_str)

            # Merge commit frequency data
            for day, count in data["commit_days"].items():
                merged_stats[identity]["commit_days"][day] += count

            for week, count in data["commit_weeks"].items():
                merged_stats[identity]["commit_weeks"][week] += count

            for month, count in data["commit_months"].items():
                merged_stats[identity]["commit_months"][month] += count

            # Update first and last commit dates
            if merged_stats[identity]["first_commit"] is None or (
                data["first_commit"] is not None
                and data["first_commit"] < merged_stats[identity]["first_commit"]
            ):
                merged_stats[identity]["first_commit"] = data["first_commit"]

            if merged_stats[identity]["last_commit"] is None or (
                data["last_commit"] is not None
                and data["last_commit"] > merged_stats[identity]["last_commit"]
            ):
                merged_stats[identity]["last_commit"] = data["last_commit"]

    # Get today's date for frequency calculations
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Get the start date for calculations (either the overall first commit or the 'since' date)
    valid_stats = [data for data in merged_stats.values() if data["first_commit"]]
    if not valid_stats:
        return dict(merged_stats), None  # Return if no valid stats

    overall_start_date = min(data["first_commit"] for data in valid_stats)

    # If a 'since' date was provided, use it as the start for the overall period
    if since:
        period_start_date = max(
            overall_start_date, datetime.strptime(since, "%Y-%m-%d")
        )
    else:
        period_start_date = overall_start_date

    # Calculate overall duration for frequency scores
    overall_total_days = (today - period_start_date).days + 1

    # Calculate overall total weeks
    first_week = period_start_date.isocalendar()[1]
    first_year = period_start_date.isocalendar()[0]
    today_week = today.isocalendar()[1]
    today_year = today.isocalendar()[0]

    if first_year == today_year:
        overall_total_weeks = today_week - first_week + 1
    else:
        years_between = today_year - first_year - 1
        weeks_in_first_year = (
            datetime(first_year, 12, 28).isocalendar()[1] - first_week + 1
        )
        weeks_in_last_year = today_week
        overall_total_weeks = (
            weeks_in_first_year + (years_between * 52) + weeks_in_last_year
        )

    # Recalculate frequency metrics for each developer using the overall period
    for identity, data in merged_stats.items():
        if data["first_commit"]:
            # Days with commits
            days_with_commits = len(data["commit_days"])

            # Weeks with commits
            weeks_with_commits = len(data["commit_weeks"])

            # Months with commits
            months_with_commits = len(data["commit_months"])

            # Calculate ratios based on the overall period duration
            data["total_days"] = overall_total_days
            data["days_with_commits"] = days_with_commits
            data["commit_day_ratio"] = (
                days_with_commits / overall_total_days if overall_total_days > 0 else 0
            )

            data["total_weeks"] = overall_total_weeks
            data["weeks_with_commits"] = weeks_with_commits
            data["commit_week_ratio"] = (
                weeks_with_commits / overall_total_weeks
                if overall_total_weeks > 0
                else 0
            )

            # Month ratio calculation (using developer's active period is more relevant)
            if data["last_commit"]:
                dev_first_month = (
                    data["first_commit"].year * 12 + data["first_commit"].month
                )
                dev_last_month = (
                    data["last_commit"].year * 12 + data["last_commit"].month
                )
                dev_total_months = dev_last_month - dev_first_month + 1
                data["total_months"] = dev_total_months
                data["months_with_commits"] = months_with_commits
                data["commit_month_ratio"] = (
                    months_with_commits / dev_total_months
                    if dev_total_months > 0
                    else 0
                )
            else:
                data["total_months"] = 0
                data["months_with_commits"] = 0
                data["commit_month_ratio"] = 0

            # Calculate average gap between commits
            if len(data["commit_dates"]) > 1:
                sorted_dates = sorted(data["commit_dates"])
                gaps = [
                    (sorted_dates[i + 1] - sorted_dates[i]).total_seconds() / 86400
                    for i in range(len(sorted_dates) - 1)
                ]
                data["avg_gap_days"] = sum(gaps) / len(gaps)
                data["max_gap_days"] = max(gaps)

                # Calculate workday-aware metrics
                workday_gaps = []
                for i in range(len(sorted_dates) - 1):
                    start = sorted_dates[i]
                    end = sorted_dates[i + 1]
                    workday_gap = (
                        count_workdays(start, end) - 1
                    )  # -1 because we don't count the commit day
                    if workday_gap < 0:  # Handles same-day commits
                        workday_gap = 0
                    workday_gaps.append(workday_gap)

                data["workday_gaps"] = workday_gaps
                data["avg_workday_gap"] = (
                    sum(workday_gaps) / len(workday_gaps) if workday_gaps else 0
                )

                # Calculate weekday vs weekend commit ratio
                weekday_commits = sum(
                    1 for date in data["commit_dates"] if is_workday(date)
                )
                total_commits = len(data["commit_dates"])
                data["weekday_commit_ratio"] = (
                    weekday_commits / total_commits if total_commits > 0 else 0
                )
            else:
                data["avg_gap_days"] = 0
                data["max_gap_days"] = 0
                data["workday_gaps"] = []
                data["avg_workday_gap"] = 0

                # For a single commit, set weekday ratio based on if it's a workday
                if data["commit_dates"]:
                    data["weekday_commit_ratio"] = (
                        1.0 if is_workday(data["commit_dates"][0]) else 0.0
                    )
                else:
                    data["weekday_commit_ratio"] = 0.0

            # Calculate daily aggregation gap metrics
            if len(data["commit_days"]) > 1:
                # Convert day strings to datetime objects
                sorted_active_days = sorted(
                    [
                        datetime.strptime(day, "%Y-%m-%d")
                        for day in data["commit_days"].keys()
                    ]
                )

                # Calculate gaps between active days in days
                active_day_gaps = [
                    (sorted_active_days[i + 1] - sorted_active_days[i]).days
                    for i in range(len(sorted_active_days) - 1)
                ]

                # Calculate metrics
                data["active_day_gaps"] = active_day_gaps
                data["avg_active_day_gap"] = sum(active_day_gaps) / len(active_day_gaps)
                data["max_active_day_gap"] = max(active_day_gaps)

                # Calculate streak-to-gap ratio
                total_streak_days = 0
                total_gap_days = 0
                current_streak = 1

                # Calculate streaks and gaps
                for i in range(1, len(sorted_active_days)):
                    gap_days = (sorted_active_days[i] - sorted_active_days[i - 1]).days

                    if gap_days == 1:  # Consecutive days
                        current_streak += 1
                    else:  # Streak broken
                        total_streak_days += current_streak
                        total_gap_days += (
                            gap_days - 1
                        )  # -1 because the end date is counted in the next streak
                        current_streak = 1

                # Add the last streak
                total_streak_days += current_streak

                # Calculate ratio
                data["total_streak_days"] = total_streak_days
                data["total_gap_days"] = total_gap_days
                data["streak_gap_ratio"] = (
                    total_streak_days / (total_gap_days + 1)
                    if total_gap_days > 0
                    else total_streak_days
                )
            else:
                data["active_day_gaps"] = []
                data["avg_active_day_gap"] = 0
                data["max_active_day_gap"] = 0
                data["total_streak_days"] = len(data["commit_days"])
                data["total_gap_days"] = 0
                data["streak_gap_ratio"] = len(data["commit_days"])

            # Calculate commit streak metrics
            sorted_days = sorted(data["commit_days"].keys())
            if sorted_days:
                # Current streak
                current_streak = 1
                max_streak = 1

                for i in range(1, len(sorted_days)):
                    prev_day = datetime.strptime(sorted_days[i - 1], "%Y-%m-%d")
                    curr_day = datetime.strptime(sorted_days[i], "%Y-%m-%d")

                    # Calculate days difference
                    days_diff = (curr_day - prev_day).days

                    # Check if consecutive or over a weekend (Friday to Monday = 3 days)
                    # Friday is weekday 4, Monday is weekday 0
                    is_over_weekend = (
                        days_diff <= 3
                        and prev_day.weekday() == 4
                        and curr_day.weekday() == 0
                    )

                    if days_diff == 1 or is_over_weekend:
                        current_streak += 1
                        max_streak = max(max_streak, current_streak)
                    else:
                        current_streak = 1

                data["max_streak"] = max_streak
            else:
                data["max_streak"] = 0

            # Choose the most common name for display
            from collections import Counter

            name_counter = Counter(data["name"])
            data["display_name"] = name_counter.most_common(1)[0][0]

    # Check for potential duplicate commits if verbose mode is enabled
    if verbose and commit_hash_tracker:
        duplicate_count = 0
        for commit_hash, occurrences in commit_hash_tracker.items():
            if len(occurrences) > 1:
                duplicate_count += 1
                if duplicate_count <= 10:  # Limit output to avoid flooding
                    print(f"{Fore.RED}Duplicate commit detected: {commit_hash}")
                    for repo_idx, identity in occurrences:
                        print(f"  - Repository #{repo_idx}, Developer: {identity}")

        if duplicate_count > 10:
            print(
                f"{Fore.RED}... and {duplicate_count - 10} more duplicate commits{Style.RESET_ALL}"
            )
        elif duplicate_count > 0:
            print(
                f"{Fore.RED}Total duplicate commits: {duplicate_count}{Style.RESET_ALL}"
            )

    return dict(merged_stats), overall_start_date


def handle_stats_command(args):
    """Handle the stats command."""
    # For backward compatibility, handle positional argument
    if args.repo_path_positional and not args.repo_paths:
        args.repo_paths = [args.repo_path_positional]

    # Check if we have at least one repo
    if not args.repo_paths:
        print(
            f"{Fore.RED}Error: You must specify at least one repository path.{Style.RESET_ALL}"
        )
        sys.exit(1)

    # Parse excluded file patterns
    excluded_patterns = [
        pattern.strip() for pattern in args.exclude.split(",") if pattern.strip()
    ]

    # Parse excluded developers
    excluded_developers = [
        dev.strip() for dev in args.exclude_developers.split(",") if dev.strip()
    ]

    # Determine date range
    since = args.since
    until = args.until

    # Set default date range to last 30 days if not otherwise specified
    if not args.all_commits and not since:
        since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        print(
            f"{Fore.YELLOW}Note: Only analyzing commits from the last 30 days. Use --all-commits to analyze all commits.{Style.RESET_ALL}"
        )

    # Print information about filters
    filters = []
    if since:
        filters.append(f"since {since}")
    if until:
        filters.append(f"until {until}")
    if args.branch:
        filters.append(f"branch {args.branch}")
    if excluded_patterns:
        filters.append(f"excluding {len(excluded_patterns)} patterns")
    if excluded_developers:
        filters.append(f"excluding {len(excluded_developers)} cmdline developers")

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
                exclude_developers=excluded_developers,
                verbose=args.verbose,
            )
            stats_list.append(repo_stats)
        except Exception as e:
            print(
                f"{Fore.RED}Error analyzing repository {repo_path}: {str(e)}{Style.RESET_ALL}"
            )
            continue

    # Merge stats if we have multiple repositories
    if len(stats_list) > 1:
        merged_stats, overall_start_date = merge_stats(
            stats_list, args.since, verbose=args.verbose
        )

        # Debug specific developers if verbose is enabled
        if args.verbose:
            for identity, data in merged_stats.items():
                if (
                    data["commits"] > 50
                ):  # Focus on developers with suspiciously high commit counts
                    print(
                        f"\n{Fore.MAGENTA}Detailed analysis for {identity} with {data['commits']} commits:{Style.RESET_ALL}"
                    )
                    print(f"  Names used: {', '.join(data['name'])}")
                    print(f"  Emails used: {', '.join(data['email'])}")
                    print(f"  First commit: {data['first_commit']}")
                    print(f"  Last commit: {data['last_commit']}")
                    print(f"  Unique days with commits: {len(data['commit_days'])}")
                    if len(data["commit_dates"]) > 0:
                        print(
                            f"  Actual commit dates count: {len(data['commit_dates'])}"
                        )
                        # Sample a few commits to verify
                        print(f"  Sample of commit dates:")
                        sample_size = min(10, len(data["commit_dates"]))
                        for i, date in enumerate(
                            sorted(data["commit_dates"])[:sample_size]
                        ):
                            print(f"    {i+1}. {date.strftime('%Y-%m-%d %H:%M:%S')}")

        display_stats(
            merged_stats,
            show_emails=args.show_emails,
            is_merged=True,
            overall_start_date=overall_start_date,
        )
    elif stats_list:
        # If only one repository, display its stats directly
        display_stats(stats_list[0], show_emails=args.show_emails)
    else:
        print(f"{Fore.YELLOW}No commits found matching the criteria.{Style.RESET_ALL}")


def main():
    """Main function to run the script."""
    args = parse_args()

    # Handle backward compatibility for positional repo_path
    if (
        hasattr(args, "repo_path_positional")
        and args.repo_path_positional
        and not hasattr(args, "command")
    ):
        # If repo_path_positional is provided and no command is specified, use it as repo_path
        args.command = "stats"
        args.repo_paths = [args.repo_path_positional]
        args.since = None
        args.until = None
        args.branch = None
        args.exclude = ""
        args.show_emails = False
        args.all_commits = False
        args.func = handle_stats_command

    # If no command is specified but repo_path is, default to stats
    if not hasattr(args, "command") or not args.command:
        if hasattr(args, "repo_paths"):
            args.command = "stats"
            args.func = handle_stats_command
        else:
            print(f"{Fore.RED}Error: No command specified.{Style.RESET_ALL}")
            sys.exit(1)

    # Call the appropriate function for the command
    if hasattr(args, "func"):
        args.func(args)
    else:
        print(f"{Fore.RED}Error: Unknown command: {args.command}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
