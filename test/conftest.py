import pytest
from click.testing import CliRunner


@pytest.fixture
def sample_repo(tmp_path):
    """Creates a sample repository structure for testing."""
    repo_path = tmp_path / "sample_repo"
    repo_path.mkdir()

    (repo_path / "file1.txt").write_text("This is file1.")
    (repo_path / "file2.txt").write_text("This is file2.")

    # Create a nested directory with a file
    nested_dir = repo_path / "nested_dir"
    nested_dir.mkdir()
    (nested_dir / "file3.txt").write_text("This is file3 in nested_dir.")

    # Add a .gitignore file
    (repo_path / ".gitignore").write_text("ignored_file.txt")
    (repo_path / "ignored_file.txt").write_text("This file should be ignored.")

    return repo_path


@pytest.fixture
def config_file(tmp_path, sample_repo):
    """Creates a sample contxt.toml config file."""
    config_path = tmp_path / "contxt.toml"
    # Use forward slashes for paths in the TOML string
    sample_repo_str = str(sample_repo).replace("\\", "/")
    tmp_path_str = str(tmp_path).replace("\\", "/")
    action_output_str = str(tmp_path / "action_output").replace("\\", "/")
    config_path.write_text(f"""
input_dir = "{sample_repo_str}"
output_dir = "{tmp_path_str}"
ignore_dirs = ["nested_dir"]

[actions.test_action]
input_dir = "{sample_repo_str}"
output_dir = "{action_output_str}"
include_ignored = true
""")
    return config_path


@pytest.fixture
def runner():
    """Returns a CliRunner instance for testing CLI commands."""
    return CliRunner()
