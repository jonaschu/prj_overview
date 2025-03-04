from pathlib import Path
import typer
from typing import List, Tuple, Optional
import fnmatch
import logging
import pathspec

app = typer.Typer()


def matches_any(identifier: str, patterns: List[str]) -> bool:
    """
    Check if the given string identifier matches any of the provided glob patterns.
    The identifier is expected to be the file's (or directory's) path relative to the project root,
    using POSIX (forward slash) notation.
    """
    for pattern in patterns:
        if fnmatch.fnmatch(identifier, pattern):
            logging.info(f"Match: '{pattern}' for identifier: '{identifier}'")
            return True
    return False


def should_process(
    path: Path,
    exclude_patterns: List[str],
    ignore_specs: List[Tuple[Path, Path, str, pathspec.PathSpec]],
    project_root: Path,
) -> bool:
    """
    Decide whether the given file or directory should be processed based on patterns.

    Pattern priority (highest to lowest):
    1. CLI exclude patterns (--exclude-patterns)
    2. .llmignore files (unless --no-llmignore is set)
    3. .gitignore files (if --use-gitignore flag is set)

    Any file or folder inside a ".git" directory is always ignored.
    """
    try:
        relative_parts = path.relative_to(project_root).parts
    except ValueError:
        relative_parts = path.parts
    # Always ignore anything inside a .git folder.
    if ".git" in relative_parts:
        logging.info(f"Ignoring .git folder or file: {path}")
        return False

    identifier = path.relative_to(project_root).as_posix()

    # Check CLI exclude patterns (highest priority)
    if matches_any(identifier, exclude_patterns):
        logging.info(f"Excluded by CLI exclude pattern: {identifier}")
        return False

    # Apply .llmignore and .gitignore rules if provided
    if ignore_specs:
        for base_dir, ignore_path, content, spec in ignore_specs:
            try:
                rel = path.relative_to(base_dir).as_posix()
            except ValueError:
                continue
            if spec.match_file(rel):
                logging.info(f"Excluded by ignore file ({ignore_path}) for: {rel}")
                return False

    logging.info(f"Included: {identifier}")
    return True


def load_ignore_files(
    project_dir: Path, file_name: str
) -> List[Tuple[Path, Path, str, pathspec.PathSpec]]:
    """
    Recursively find all ignore files (e.g., .llmignore or .gitignore) in the project directory,
    and return a list of tuples: (base_directory, ignore_file_path, file_content, pathspec_object)
    """
    ignore_list = []
    for ignore_file in project_dir.rglob(file_name):
        try:
            content = ignore_file.read_text(encoding="utf-8")
        except Exception as e:
            logging.warning(f"Could not read {ignore_file}: {e}")
            continue
        lines = content.splitlines()
        spec = pathspec.PathSpec.from_lines("gitwildmatch", lines)
        ignore_list.append((ignore_file.parent, ignore_file, content, spec))
    return ignore_list


def generate_tree(
    dir_path: Path,
    exclude_patterns: List[str],
    ignore_specs: List[Tuple[Path, Path, str, pathspec.PathSpec]],
    project_root: Optional[Path] = None,
) -> str:
    """
    Generate a tree-like string representation of the folder structure,
    applying pattern filtering.
    """
    if project_root is None:
        project_root = dir_path

    def _tree(current_path: Path, prefix: str = "") -> List[str]:
        tree_lines = []
        # Filter out __pycache__ and .git directories
        entries = sorted(
            [
                p
                for p in current_path.iterdir()
                if p.name not in {"__pycache__", ".git"}
            ],
            key=lambda x: (not x.is_dir(), x.name.lower()),
        )
        entries_count = len(entries)
        for index, entry in enumerate(entries):
            if not should_process(entry, exclude_patterns, ignore_specs, project_root):
                continue
            connector = "└──" if index == entries_count - 1 else "├──"
            if entry.is_dir():
                tree_lines.append(f"{prefix}{connector} {entry.name}/")
                extension = "    " if index == entries_count - 1 else "│   "
                tree_lines.extend(_tree(entry, prefix + extension))
            else:
                if entry.name == "__init__.py" and entry.stat().st_size == 0:
                    continue
                tree_lines.append(f"{prefix}{connector} {entry.name}")
        return tree_lines

    tree_lines = [dir_path.name + "/"]
    tree_lines.extend(_tree(dir_path))
    return "\n".join(tree_lines)


def get_code_files(
    dir_path: Path,
    exclude_patterns: List[str],
    ignore_specs: List[Tuple[Path, Path, str, pathspec.PathSpec]],
    project_root: Optional[Path] = None,
) -> List[Tuple[str, Path]]:
    """
    Gather a list of code files under dir_path that pass the pattern filters.
    Each file is returned as a tuple (relative_path_str, file_path).
    """
    if project_root is None:
        project_root = dir_path

    code_files = []
    for path in dir_path.rglob("*"):
        try:
            relative_parts = path.relative_to(project_root).parts
        except ValueError:
            relative_parts = path.parts
        if ".git" in relative_parts:
            continue
        if not should_process(path, exclude_patterns, ignore_specs, project_root):
            continue
        if path.is_file():
            if path.name == "__init__.py" and path.stat().st_size == 0:
                continue
            rel_path = path.relative_to(dir_path)
            code_files.append((str(rel_path), path))
    return code_files


def create_markdown(
    dir_path: Path,
    output_file: Path,
    exclude_patterns: List[str],
    ignore_specs: List[Tuple[Path, Path, str, pathspec.PathSpec]],
    tree_only: bool = False,
):
    """
    Create a Markdown file containing the project overview, folder structure (as a tree),
    and code sections (unless tree_only is True).
    """
    project_name = dir_path.resolve().name
    with output_file.open("w", encoding="utf-8") as md_file:
        # Project Overview
        md_file.write(f"# {project_name} Overview\n\n")

        # Folder Structure
        md_file.write("## Folder Structure\n")
        md_file.write("```tree\n")
        tree_str = generate_tree(
            dir_path,
            exclude_patterns,
            ignore_specs,
            project_root=dir_path,
        )
        md_file.write(f"{tree_str}\n")
        md_file.write("```\n\n")

        # Code Sections
        if not tree_only:
            md_file.write("## Code\n")
            code_files = get_code_files(
                dir_path,
                exclude_patterns,
                ignore_specs,
                project_root=dir_path,
            )
            for rel_path, file_path in code_files:
                md_file.write(f"### {rel_path}\n")
                extension = file_path.suffix[1:] if file_path.suffix else file_path.stem
                # use 4 backticks if markdown file, to ensure a correct rendering of code blocks
                # containing markdown code.
                code_block_start = (
                    f"````{extension}\n" if extension == "md" else f"```{extension}\n"
                )
                md_file.write(code_block_start)
                try:
                    content = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = "# [Binary file not displayed]\n"
                md_file.write(f"{content}\n")
                code_block_end = "````\n\n" if extension == "md" else "```\n\n"
                md_file.write(code_block_end)


@app.command()
def main(
    directory: Path = typer.Argument(..., help="The root directory of the project"),
    output: Path = typer.Option(
        "project_overview.md", "-o", "--output", help="Output Markdown filename"
    ),
    exclude_patterns: List[str] = typer.Option(
        [],
        "--exclude",
        "-e",
        help="Wildcard patterns to exclude (e.g., '*test*', '*.md'). These patterns are matched against each file's path relative to the project root.",
        metavar="PATTERN",
    ),
    no_llmignore: bool = typer.Option(
        False,
        "--no-llmignore",
        help="Disable the use of .llmignore files for pattern filtering.",
    ),
    use_gitignore: bool = typer.Option(
        False,
        "--use-gitignore",
        help="Use .gitignore files for pattern filtering (lower priority than .llmignore).",
    ),
    log_level: Optional[str] = typer.Option(
        "error",
        "--log-level",
        "-l",
        help="Define log level: 'info', 'warning' or 'error' (default)",
    ),
    tree_only: bool = typer.Option(
        False,
        "--tree-only",
        "-t",
        help="If flag is set, then only the tree section will be added to the markdown.",
    ),
):
    """
    Convert folder structure and code files to Markdown with pattern filtering.

    Pattern sources in order of precedence:
    1. --exclude-patterns (highest priority)
    2. .llmignore files (default, unless --no-llmignore is set)
    3. .gitignore files (only if --use-gitignore flag is set)
    """
    if log_level == "error":
        logging.basicConfig(level=logging.ERROR)
    elif log_level == "warning":
        logging.basicConfig(level=logging.WARNING)
    elif log_level == "info":
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.ERROR)

    if not directory.exists() or not directory.is_dir():
        typer.echo(
            f"Error: The directory '{directory}' does not exist or is not a directory.",
            err=True,
        )
        raise typer.Exit(code=1)

    # Collect all ignore specifications in order of precedence
    ignore_specs = []

    # Load .llmignore files (unless disabled)
    if not no_llmignore:
        llmignore_data = load_ignore_files(directory, ".llmignore")
        if llmignore_data:
            logging.info(f"Found {len(llmignore_data)} .llmignore files")
            ignore_specs.extend(llmignore_data)
        else:
            logging.info("No .llmignore files found")

    # Load .gitignore files (if enabled)
    if use_gitignore:
        gitignore_data = load_ignore_files(directory, ".gitignore")
        if gitignore_data:
            logging.info(f"Found {len(gitignore_data)} .gitignore files")
            ignore_specs.extend(gitignore_data)
        else:
            logging.info("No .gitignore files found")

    create_markdown(directory, output, exclude_patterns, ignore_specs, tree_only)
    typer.echo(f"Markdown file '{output}' has been generated.")


if __name__ == "__main__":
    app()
