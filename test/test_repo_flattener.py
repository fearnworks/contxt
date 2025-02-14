import os
import shutil
import tempfile
from pathlib import Path

from contxt.repo_flattener import main


def test_repo_flattener_no_config(runner, sample_repo, tmp_path):
    """
    GIVEN a sample repository and a temporary directory
    WHEN the flattener is run without a config file, specifying input and output dirs
    THEN the flattener runs successfully and creates the structure and flattened files.
    """
    result = runner.invoke(main, [str(sample_repo), str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / f"structure_{sample_repo.name}.toml").exists()
    assert (tmp_path / f"flattened_{sample_repo.name}.txt").exists()


def test_repo_flattener_with_config(runner, sample_repo, config_file, tmp_path):
    """
    GIVEN a sample repository, a config file, and a temporary directory
    WHEN the flattener is run with a config file
    THEN the flattener runs successfully and creates the structure and flattened files.
    """
    result = runner.invoke(main, ["-c", str(config_file)])
    assert result.exit_code == 0
    assert (tmp_path / f"structure_{sample_repo.name}.toml").exists()
    assert (tmp_path / f"flattened_{sample_repo.name}.txt").exists()


def test_repo_flattener_default_config(runner, sample_repo, tmp_path, monkeypatch):
    """
    GIVEN a sample repository, a temporary directory, and a monkeypatch fixture
    WHEN the flattener is run with a default contxt.toml in the current directory
    THEN the flattener runs successfully and creates the structure and flattened files in the temporary directory.
    """
    # Create a temporary directory and copy the config file into it
    temp_dir = Path(tempfile.mkdtemp())
    try:
        config_path = temp_dir / "contxt.toml"
        # Use relative paths in the config file and escape backslashes
        sample_repo_rel = os.path.relpath(sample_repo, temp_dir).replace("\\", "\\\\")
        config_path.write_text(f"""
input_dir = "{sample_repo_rel}"
output_dir = "."
""")
        # Change the current working directory to the temporary directory
        monkeypatch.chdir(temp_dir)
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert (temp_dir / f"structure_{sample_repo.name}.toml").exists()
        assert (temp_dir / f"flattened_{sample_repo.name}.txt").exists()
    finally:
        # Change directory back before cleanup
        monkeypatch.chdir(os.path.dirname(temp_dir))
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"Warning: Failed to clean up temporary directory: {e}")


def test_repo_flattener_structure_only(runner, sample_repo, tmp_path):
    """
    GIVEN a sample repository and a temporary directory
    WHEN the flattener is run with the --structure-only flag
    THEN the flattener runs successfully and creates only the structure file.
    """
    result = runner.invoke(main, [str(sample_repo), str(tmp_path), "--structure-only"])
    assert result.exit_code == 0
    assert (tmp_path / f"structure_{sample_repo.name}.toml").exists()
    assert not (tmp_path / f"flattened_{sample_repo.name}.txt").exists()


def test_repo_flattener_include_ignored(runner, sample_repo, tmp_path):
    """
    GIVEN a sample repository and a temporary directory
    WHEN the flattener is run with the --include-ignored flag
    THEN the flattener runs successfully and includes the ignored file in the flattened output.
    """
    result = runner.invoke(main, [str(sample_repo), str(tmp_path), "--include-ignored"])
    assert result.exit_code == 0
    assert (tmp_path / f"structure_{sample_repo.name}.toml").exists()
    assert (tmp_path / f"flattened_{sample_repo.name}.txt").exists()
    # Check if the ignored file is in the flattened output
    flattened_content = (tmp_path / f"flattened_{sample_repo.name}.txt").read_text()
    assert "ignored_file.txt" in flattened_content


def test_repo_flattener_action(runner, sample_repo, config_file, tmp_path):
    """
    GIVEN a sample repository, a config file, and a temporary directory
    WHEN the flattener is run with a config file and an action
    THEN the flattener runs successfully and applies the action-specific settings.
    """
    result = runner.invoke(main, ["-c", str(config_file), "-a", "test_action"])
    assert result.exit_code == 0
    action_output_dir = tmp_path / "action_output"
    assert (action_output_dir / f"structure_{sample_repo.name}.toml").exists()
    assert (action_output_dir / f"flattened_{sample_repo.name}.txt").exists()
    # Check if the ignored file is in the flattened output
    flattened_content = (action_output_dir / f"flattened_{sample_repo.name}.txt").read_text()
    assert "ignored_file.txt" in flattened_content
    # Check if the nested_dir files are not in the flattened output
    assert "nested_dir" not in flattened_content


def test_repo_flattener_local(runner, sample_repo, monkeypatch, tmp_path):
    """
    GIVEN a sample repository and a temporary working directory
    WHEN the flattener is run with the --local flag
    THEN the output is generated in .local/contxt/<repo_name> directory.
    """
    # Change working directory to tmp_path so that the standardized output is predictable
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(main, [str(sample_repo)])
    assert result.exit_code == 0
    local_output_dir = tmp_path / ".local" / "contxt" / sample_repo.name
    assert (local_output_dir / f"structure_{sample_repo.name}.toml").exists()
    assert (local_output_dir / f"flattened_{sample_repo.name}.txt").exists()
