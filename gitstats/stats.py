"""
Git repository statistics analysis functionality.
"""

import os
import sys
import re
from collections import defaultdict, Counter
from datetime import datetime, timedelta

import git
from colorama import Fore, Style

from .identity import (
    load_identity_mappings, 
    get_canonical_identity,
    get_excluded_developers
)

def normalize_email(email):
    """Normalize email address to handle common variations."""
    if not email:
        return "unknown@example.com"
    
    # Convert to lowercase
    email = email.lower()
    
    # Remove any whitespace
    email = email.strip()
    
    # Handle GitHub noreply emails which may contain username
    if '+' in email and '@users.noreply.github.com' in email:
        # Extract username from GitHub noreply email
        match = re.search(r'([^+]+)\+', email)
        if match:
            return f"{match.group(1)}@github.com"
    
    return email

def is_workday(date):
    """Returns True if date is a weekday (Monday-Friday)."""
    return date.weekday() < 5

def count_workdays(start_date, end_date):
    """Count workdays between two dates."""
    days = (end_date - start_date).days
    return sum(1 for i in range(days + 1) if is_workday(start_date + timedelta(days=i)))

def get_repo_stats(repo_path, since=None, until=None, branch=None, exclude=None, exclude_developers=None):
    """
    Analyze a Git repository and return statistics per developer.
    
    Args:
        repo_path: Path to the Git repository
        since: Only consider commits more recent than this date
        until: Only consider commits older than this date
        branch: Analyze only a specific branch
        exclude: List of file patterns to exclude
        exclude_developers: List of developer names or emails to exclude (in addition to configured exclusions)
        
    Returns:
        Dictionary with developer statistics
    """
    try:
        repo = git.Repo(repo_path)
    except git.exc.InvalidGitRepositoryError:
        print(f"{Fore.RED}Error: {repo_path} is not a valid Git repository.{Style.RESET_ALL}")
        sys.exit(1)
    except git.exc.NoSuchPathError:
        print(f"{Fore.RED}Error: Path {repo_path} does not exist.{Style.RESET_ALL}")
        sys.exit(1)
    
    # Load identity mappings for this repository
    identity_mappings = load_identity_mappings(repo_path)
    
    # Get excluded developers from config and combine with any provided via command line
    config_excluded_developers = get_excluded_developers(repo_path)
    
    # Prepare exclude_developers list
    if exclude_developers is None:
        exclude_developers = []
    
    # Combine both exclusion lists and convert to lowercase for case-insensitive comparison
    all_excluded_developers = [dev.lower() for dev in (exclude_developers + config_excluded_developers)]
    
    # Print info about excluded developers if any
    if all_excluded_developers:
        print(f"{Fore.YELLOW}Excluding {len(all_excluded_developers)} developer(s) from analysis{Style.RESET_ALL}")
    
    # Initialize stats dictionary
    # Use canonical identity as the primary key to avoid duplication of developers
    stats = defaultdict(lambda: {
        'name': set(),  # Store all name variations
        'email': set(),  # Store all email variations
        'commits': 0,
        'lines_added': 0,
        'lines_deleted': 0,
        'net_lines': 0,
        'files_changed': 0,
        'first_commit': None,
        'last_commit': None,
        'commit_dates': [],  # Store all commit dates for frequency analysis
        'commit_days': Counter(),  # Count commits per day
        'commit_weeks': Counter(),  # Count commits per week
        'commit_months': Counter()  # Count commits per month
    })
    
    # First pass: collect all author names and emails to build a mapping
    email_to_author = {}
    author_emails = defaultdict(set)
    
    for commit in repo.iter_commits('--all'):
        author_name = commit.author.name
        author_email = normalize_email(commit.author.email)
        
        # Skip excluded developers
        if (author_name.lower() in all_excluded_developers or 
            author_email.lower() in all_excluded_developers or 
            commit.author.email.lower() in all_excluded_developers):
            continue
        
        # Get the canonical identity for this author
        canonical_identity = get_canonical_identity(identity_mappings, author_name, author_email)
        
        # Skip if the canonical identity is in the exclude list
        if canonical_identity.lower() in all_excluded_developers:
            continue
        
        # Map this email to this author
        if author_email not in email_to_author:
            email_to_author[author_email] = canonical_identity
        
        # Map this author to this email
        author_emails[canonical_identity].add(author_email)
    
    # Build a consolidated mapping of all emails for the same author
    # This handles cases where the same person uses different email addresses
    consolidated_emails = {}
    processed_authors = set()
    
    for author, emails in author_emails.items():
        if author in processed_authors:
            continue
            
        # Find all related authors (those who share at least one email)
        related_authors = {author}
        all_emails = set(emails)
        
        # Find all authors who share emails with this author
        for other_author, other_emails in author_emails.items():
            if other_author != author and not emails.isdisjoint(other_emails):
                related_authors.add(other_author)
                all_emails.update(other_emails)
        
        # Mark all these authors as processed
        processed_authors.update(related_authors)
        
        # Create a canonical email for this group (use the first email alphabetically)
        canonical_email = sorted(all_emails)[0]
        
        # Map all emails to the canonical email
        for email in all_emails:
            consolidated_emails[email] = canonical_email
    
    # Use GitPython's built-in commit iteration instead of git log
    # This should handle dates correctly
    try:
        # Determine which commits to analyze
        if branch:
            try:
                commits = list(repo.iter_commits(branch, no_merges=True))
            except git.exc.GitCommandError:
                print(f"{Fore.RED}Error: Branch '{branch}' not found.{Style.RESET_ALL}")
                sys.exit(1)
        else:
            commits = list(repo.iter_commits('--all', no_merges=True))
        
        # Apply date filters if specified
        if since or until:
            filtered_commits = []
            for commit in commits:
                commit_date = datetime.fromtimestamp(commit.committed_date)
                
                if since:
                    since_date = datetime.strptime(since, '%Y-%m-%d')
                    if commit_date < since_date:
                        continue
                        
                if until:
                    until_date = datetime.strptime(until, '%Y-%m-%d')
                    if commit_date > until_date:
                        continue
                        
                filtered_commits.append(commit)
            commits = filtered_commits
        
        # Process each commit
        for commit in commits:
            author_name = commit.author.name
            raw_email = commit.author.email
            author_email = normalize_email(raw_email)
            
            # Skip excluded developers
            if (author_name.lower() in all_excluded_developers or 
                author_email.lower() in all_excluded_developers or 
                raw_email.lower() in all_excluded_developers):
                continue
            
            # Get the canonical identity for this author
            canonical_identity = get_canonical_identity(identity_mappings, author_name, author_email)
            
            # Skip if the canonical identity is in the exclude list
            if canonical_identity.lower() in all_excluded_developers:
                continue
            
            # Use the consolidated email as the key
            canonical_email = consolidated_emails.get(author_email, author_email)
            
            commit_date = datetime.fromtimestamp(commit.committed_date)
            
            # Update author information
            stats[canonical_identity]['name'].add(author_name)
            stats[canonical_identity]['email'].add(raw_email)
            
            # Update commit count and dates
            stats[canonical_identity]['commits'] += 1
            stats[canonical_identity]['commit_dates'].append(commit_date)
            
            # Track commit frequency by day, week, and month
            day_key = commit_date.strftime('%Y-%m-%d')
            week_key = f"{commit_date.isocalendar()[0]}-W{commit_date.isocalendar()[1]:02d}"
            month_key = commit_date.strftime('%Y-%m')
            
            stats[canonical_identity]['commit_days'][day_key] += 1
            stats[canonical_identity]['commit_weeks'][week_key] += 1
            stats[canonical_identity]['commit_months'][month_key] += 1
            
            if stats[canonical_identity]['first_commit'] is None or commit_date < stats[canonical_identity]['first_commit']:
                stats[canonical_identity]['first_commit'] = commit_date
                
            if stats[canonical_identity]['last_commit'] is None or commit_date > stats[canonical_identity]['last_commit']:
                stats[canonical_identity]['last_commit'] = commit_date
            
            # Get the diff stats for this commit
            if commit.parents:
                diff = commit.parents[0].diff(commit, create_patch=True)
                
                for diff_item in diff:
                    # Skip files matching exclude patterns
                    if exclude and diff_item.a_path and any(pattern in diff_item.a_path for pattern in exclude.split(',')):
                        continue
                    
                    # Count lines added and deleted
                    if hasattr(diff_item, 'a_path') and diff_item.a_path:
                        stats[canonical_identity]['files_changed'] += 1
                        
                        # Get line stats if available
                        if hasattr(diff_item, 'a_blob') and diff_item.a_blob and hasattr(diff_item, 'b_blob') and diff_item.b_blob:
                            try:
                                # Count lines in the diff
                                lines_added = 0
                                lines_deleted = 0
                                
                                for line in diff_item.diff.decode('utf-8', errors='replace').split('\n'):
                                    if line.startswith('+') and not line.startswith('+++'):
                                        lines_added += 1
                                    elif line.startswith('-') and not line.startswith('---'):
                                        lines_deleted += 1
                                
                                stats[canonical_identity]['lines_added'] += lines_added
                                stats[canonical_identity]['lines_deleted'] += lines_deleted
                                stats[canonical_identity]['net_lines'] += (lines_added - lines_deleted)
                            except (UnicodeDecodeError, AttributeError):
                                # Skip binary files or files with encoding issues
                                pass
        
        # Calculate commit frequency metrics for each developer
        for identity, data in stats.items():
            if data['first_commit']:
                # Get today's date for frequency calculations
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                
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
                name_counter = Counter(data['name'])
                data['display_name'] = name_counter.most_common(1)[0][0]
    
    except Exception as e:
        print(f"{Fore.RED}Error analyzing repository: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)
    
    return stats 