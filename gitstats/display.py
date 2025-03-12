"""
Display functionality for Git repository statistics.
"""

from datetime import datetime
from colorama import Fore, Style
from tabulate import tabulate

def format_time_elapsed(date):
    """Format the time elapsed since a date in a human-readable format."""
    now = datetime.now()
    delta = now - date
    
    if delta.days < 0:
        # Future date (could be a recent commit with small clock differences)
        return "recently"
    
    if delta.days == 0:
        hours = delta.seconds // 3600
        if hours == 0:
            minutes = delta.seconds // 60
            return f"{minutes}m ago"
        return f"{hours}h ago"
    elif delta.days < 30:
        return f"{delta.days}d ago"
    elif delta.days < 365:
        months = delta.days // 30
        return f"{months}mo ago"
    else:
        years = delta.days // 365
        return f"{years}y ago"

def get_commit_frequency_score(data):
    """Calculate a commit frequency score from 0-10 based on various metrics."""
    # Base score on commit day ratio (percentage of days with commits)
    day_ratio_score = min(data['commit_day_ratio'] * 10, 5)
    
    # Add points for weekly commit consistency
    week_ratio_score = min(data['commit_week_ratio'] * 5, 3)
    
    # Add points for streak length
    streak_score = min(data['max_streak'] / 5, 2)
    
    # Penalize for large gaps between commits
    gap_penalty = 0
    if data['avg_gap_days'] > 7:
        gap_penalty = min((data['avg_gap_days'] - 7) / 7, 2)
    
    # Calculate final score
    score = day_ratio_score + week_ratio_score + streak_score - gap_penalty
    return max(min(round(score, 1), 10), 0)  # Ensure score is between 0-10

def get_frequency_color(score):
    """Return a color based on the frequency score."""
    if score >= 8:
        return Fore.GREEN
    elif score >= 5:
        return Fore.YELLOW
    else:
        return Fore.RED

def format_frequency_metrics(data):
    """Format commit frequency metrics in a readable way."""
    # Calculate frequency score
    score = get_commit_frequency_score(data)
    color = get_frequency_color(score)
    
    # Format metrics
    day_ratio = f"{data['commit_day_ratio']*100:.1f}%"
    week_ratio = f"{data['commit_week_ratio']*100:.1f}%"
    
    # Format streak
    streak = f"{data['max_streak']}d"
    
    # Format gap
    avg_gap = f"{data['avg_gap_days']:.1f}d"
    
    return f"{color}★{score}/10{Style.RESET_ALL} ({day_ratio} days, {week_ratio} weeks, {streak} streak, {avg_gap} gap)"

def display_stats(stats, show_emails=False, is_merged=False):
    """Display the collected statistics in a formatted table."""
    if not stats:
        print(f"{Fore.YELLOW}No commits found matching the criteria.{Style.RESET_ALL}")
        return
        
    # Prepare table data
    table_data = []
    for email, data in sorted(stats.items(), key=lambda x: get_commit_frequency_score(x[1]), reverse=True):
        # Get the display name (most common name used by this email)
        display_name = data['display_name']
        
        # Format dates more concisely
        first_commit = format_time_elapsed(data['first_commit'])
        last_commit = format_time_elapsed(data['last_commit'])
        
        # Format code impact
        code_impact = f"+{data['lines_added']}/-{data['lines_deleted']}"
        
        # Format commit frequency metrics
        frequency = format_frequency_metrics(data)
        
        # Format name variations if there are multiple
        name_variations = ""
        if len(data['name']) > 1:
            other_names = [name for name in data['name'] if name != display_name]
            if other_names:
                name_variations = f" ({', '.join(other_names)})"
        
        # Format email addresses if requested
        email_info = ""
        if show_emails:
            # Format the canonical email and any variations
            canonical_email = email
            
            # Filter out invalid email addresses
            valid_emails = [e for e in data['email'] if '@' in e and e != '--global' and e != 'user.email']
            
            if valid_emails:
                # Show all valid emails to help debug name consolidation issues
                email_info = "\n".join(valid_emails)
            else:
                email_info = canonical_email
        
        # Add row to table
        row = [
            f"{display_name}{name_variations}",
            data['commits'],
            frequency,
            f"{first_commit} → {last_commit}",
            code_impact
        ]
        
        # Add email column if requested
        if show_emails:
            row.insert(1, email_info)
        
        table_data.append(row)
    
    # Display table with more concise headers
    headers = [
        "Developer", 
        "Commits", 
        "Commit Frequency",
        "Activity Period",
        "Code Impact"
    ]
    
    # Add email header if requested
    if show_emails:
        headers.insert(1, "Email")
    
    title = f"{Fore.CYAN}Git Repository Commit Frequency Analysis"
    if is_merged:
        title = f"{Fore.CYAN}Aggregated Git Repositories Commit Frequency Analysis"
    
    print(f"\n{title}{Style.RESET_ALL}")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Display summary
    total_commits = sum(data['commits'] for data in stats.values())
    total_lines_added = sum(data['lines_added'] for data in stats.values())
    total_lines_deleted = sum(data['lines_deleted'] for data in stats.values())
    
    print(f"\n{Fore.GREEN}Summary:{Style.RESET_ALL}")
    print(f"Total Developers: {len(stats)}")
    print(f"Total Commits: {total_commits}")
    print(f"Code Impact: +{total_lines_added}/-{total_lines_deleted}")
    
    # Display frequency legend
    print(f"\n{Fore.CYAN}Commit Frequency Score Legend:{Style.RESET_ALL}")
    print(f"{Fore.GREEN}★8-10{Style.RESET_ALL}: Excellent - Very consistent commit pattern")
    print(f"{Fore.YELLOW}★5-7{Style.RESET_ALL}: Good - Regular commits with some gaps")
    print(f"{Fore.RED}★0-4{Style.RESET_ALL}: Needs improvement - Infrequent or irregular commits") 