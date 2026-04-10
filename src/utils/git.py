from pathlib import Path
from git import Repo, InvalidGitRepositoryError, GitCommandError


def get_staged_files(path: Path) -> list[Path]:
    """
    Get all files that are currently staged in the git index.
    Returns absolute paths to the staged files.
    """
    try:
        repo = Repo(path, search_parent_directories=True)
    except InvalidGitRepositoryError:
        # Not a git repository
        return []

    staged_files = set()
    root_path = Path(repo.working_tree_dir)

    try:
        # Diff the index against HEAD to find staged changes
        diff_idx = repo.index.diff(repo.head.commit)
        for diff in diff_idx:
            # Add files that are added or modified (ignore deleted files)
            if diff.change_type != "D" and diff.b_path:
                staged_files.add(root_path / diff.b_path)
    except (ValueError, GitCommandError, TypeError):
        # If the repository has no commits yet (initial commit), HEAD doesn't exist.
        # In this case, everything in the index is staged.
        for entry in repo.index.entries.keys():
            path_str = entry[0]
            staged_files.add(root_path / path_str)

    # Filter out files that no longer exist on disk (just to be safe)
    return [p for p in staged_files if p.exists() and p.is_file()]
