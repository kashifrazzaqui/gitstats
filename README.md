# GitStats

A Python CLI tool to analyze Git repository statistics for developers with a focus on commit frequency and cadence.

## Features

- Track commits per developer
- Analyze lines of code added and deleted
- Calculate net impact on codebase
- Analyze commit frequency and developer productivity patterns
- Score developers based on commit consistency and cadence
- Filter by date range, branch, or file patterns
- Colorful terminal output with formatted tables

## Installation

### Using Poetry (Recommended)

1. Clone this repository:
   ```
   git clone https://github.com/kashifrazzaqui/gitstats.git
   cd gitstats
   ```

2. Install with Poetry:
   ```
   poetry install
   ```

3. Run the tool:
   ```
   poetry run gitstats /path/to/git/repository
   ```

### Manual Installation

1. Clone this repository:
   ```
   git clone https://github.com/kashifrazzaqui/gitstats.git
   cd gitstats
   ```

2. Install the required dependencies:
   ```
   pip install .
   ```

3. Run the tool:
   ```
   gitstats /path/to/git/repository
   ```

## Usage

Basic usage:

```
gitstats /path/to/git/repository
```

### Command Line Options

- `repo_path`: Path to the Git repository to analyze (required)
- `--since`: Only consider commits more recent than this date (format: YYYY-MM-DD)
- `--until`: Only consider commits older than this date (format: YYYY-MM-DD)
- `--branch`: Analyze only a specific branch
- `--exclude`: Comma-separated list of file patterns to exclude

### Examples

Analyze all commits in a repository:
```
gitstats /path/to/repo
```

Analyze commits from the last month:
```
gitstats /path/to/repo --since=2023-05-01
```

Analyze commits on a specific branch:
```
gitstats /path/to/repo --branch=main
```

Exclude certain file types:
```
gitstats /path/to/repo --exclude=.json,.md,node_modules
```

Combine multiple filters:
```
gitstats /path/to/repo --since=2023-01-01 --until=2023-12-31 --branch=develop --exclude=.json,.md
```

## Commit Frequency Metrics

GitStats provides a comprehensive analysis of developer commit patterns with a focus on frequency and consistency. The tool calculates various metrics to help understand how regularly developers are contributing to the codebase.

### Commit Frequency Score (0-10)

The core metric is a score from 0 to 10 that indicates how consistently a developer commits code. This score is color-coded in the output:

- **★8-10 (Green)**: Excellent - Very consistent commit pattern
- **★5-7 (Yellow)**: Good - Regular commits with some gaps
- **★0-4 (Red)**: Needs improvement - Infrequent or irregular commits

### How the Score is Calculated

The commit frequency score is based on several factors:

1. **Day Ratio (50% of score)**: 
   - Percentage of days with at least one commit during the active period
   - Formula: `(days with commits / total days in date range) * 100%`
   - Contributes up to 5 points to the score

2. **Week Ratio (30% of score)**:
   - Percentage of weeks with at least one commit during the active period
   - Formula: `(weeks with commits / total weeks in date range) * 100%`
   - Contributes up to 3 points to the score

3. **Commit Streak (20% of score)**:
   - Longest consecutive days with commits
   - Contributes up to 2 points to the score

4. **Gap Penalty**:
   - Penalizes for large gaps between commits
   - Starts applying when average gap exceeds 7 days
   - Can reduce score by up to 2 points

### Additional Metrics

For each developer, GitStats tracks and displays:

- **Activity Period**: First commit to last commit timeframe
- **Days with Commits**: Number of unique days with at least one commit
- **Weeks with Commits**: Number of unique weeks with at least one commit
- **Months with Commits**: Number of unique months with at least one commit
- **Commit Streak**: Longest consecutive days with commits
- **Average Gap**: Average time between commits in days
- **Maximum Gap**: Longest period without commits in days

### Interpreting the Results

- **High Frequency Score (8-10)**: Developers who commit very regularly, showing consistent work patterns and likely good progress
- **Medium Frequency Score (5-7)**: Developers with reasonably regular commits but with some gaps or inconsistencies
- **Low Frequency Score (0-4)**: Developers with infrequent or irregular commits, which might indicate challenges or blockers

### Example Output

```
+-----------------+-----------+----------------------------------------------------------+------------------+---------------+
| Developer       |   Commits | Commit Frequency                                         | Activity Period  | Code Impact   |
+=================+===========+==========================================================+==================+===============+
| Dylan Hanson    |       267 | ★9.4/10 (48.4% days, 92.9% weeks, 8d streak, 0.3d gap)   | 3mo ago → 31m ago| +38071/-18760 |
+-----------------+-----------+----------------------------------------------------------+------------------+---------------+
| Ryan Callihan   |       134 | ★7.7/10 (41.2% days, 100.0% weeks, 3d streak, 0.4d gap)  | 1mo ago → 8m ago | +7736/-5349   |
+-----------------+-----------+----------------------------------------------------------+------------------+---------------+
```

## Development

### Setup Development Environment

```
poetry install --with dev
```

### Run Tests

```
poetry run pytest
```

### Code Formatting

```
poetry run black .
poetry run isort .
```

## Output

The script outputs a formatted table with the following information for each developer:

- Number of commits
- Lines of code added
- Lines of code deleted
- Net impact on lines of code
- Number of files changed
- First and last commit dates
- Number of days active
- Average commits per day

A summary of the overall repository statistics is also displayed.

## License

MIT 