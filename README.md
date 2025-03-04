# Project Overview Generator

A command-line tool that generates comprehensive Markdown documentation for your projects. It automatically creates a structured file showing your project's architecture and optionally includes code snippets.

## Features

- **Directory Tree Visualization**: Generates an ASCII tree representation of your project structure
- **Code Inclusion**: Optionally includes the actual code from each file, properly formatted with syntax highlighting
- **Smart Filtering**: Use wildcards to include or exclude specific files and directories
- **Git Integration**: Option to respect your `.gitignore` files
- **Customizable Output**: Control the format and detail level of the generated documentation

## Installation

The Project Overview Generator can be installed using `uv`, the extremely fast Python package manager:

```bash
uv tool install prj_overview
```

You can also install directly from the repository:

```bash
uv tool install git+https://github.com/username/prj_overview.git
```

Or from a local directory:

```bash
cd /path/to/prj_overview
uv tool install .
```

## Usage

After installation, use the `prj-overview` command:

```bash
prj-overview [DIRECTORY] [OPTIONS]
```

### Basic Examples

Generate an overview of the current directory:
```bash
prj-overview .
```

Specify an output file:
```bash
prj-overview . -o my-project-docs.md
```

Generate tree structure only (no code):
```bash
prj-overview . --tree-only
```

Filter to include only Python files:
```bash
prj-overview . --include "*.py"
```

Exclude test files:
```bash
prj-overview . --exclude "*test*" --exclude "*/__pycache__/*"
```

Respect `.gitignore` patterns:
```bash
prj-overview . --use-gitignore
```

### Command Line Options

- `--output`, `-o`: Output Markdown filename (default: "project_overview.md")
- `--exclude`, `-e`: Wildcard patterns to exclude (e.g., '*test*', '*.md')
- `--include`, `-i`: Wildcard patterns to include (e.g., '*src*', '*.py')
- `--use-gitignore`: Use .gitignore files as base patterns for excluding files
- `--log-level`, `-l`: Define log level: 'info', 'warning' or 'error' (default: 'error')
- `--tree-only`, `-t`: If set, only the tree section will be added to the markdown

## Example Output

The generated markdown file will include:

````markdown
# MyProject Overview

## Folder Structure
```tree
MyProject/
├── src/
│   ├── main.py
│   └── utils/
│       └── helpers.py
├── tests/
│   └── test_main.py
└── README.md
```

## Code
### src/main.py
```python
def main():
    print("Hello, world!")

if __name__ == "__main__":
    main()
```

### src/utils/helpers.py
```python
def helper_function():
    return "I'm helping!"
```
````

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License.