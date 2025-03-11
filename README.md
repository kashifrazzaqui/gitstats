# GitStats

A Python CLI tool to analyze Git repository statistics for developers.

## Features

- Track commits per developer
- Analyze lines of code added and deleted
- Calculate net impact on codebase
- Filter by date range, branch, or file patterns
- Colorful terminal output with formatted tables

## Installation

### Using Poetry (Recommended)

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/gitstats.git
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
   git clone https://github.com/yourusername/gitstats.git
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