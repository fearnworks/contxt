#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
CLI Tool for flattening a directory tree into a single file with metadata.
Precursor to contxt content tools
"""

import os
import subprocess
import tomllib
from pathlib import Path

import click

from contxt.logger import logger


class RepoFlattener:
    def __init__(self, input_dir=None, output_dir=None, include_ignored=False, config_file=None, action=None):
        logger.info(f"Initializing RepoFlattener with input_dir={input_dir}, output_dir={output_dir}")
        # Initialize with None values to allow config override
        self.input_dir = Path(input_dir).resolve() if input_dir else None
        self.output_dir = Path(output_dir).resolve() if output_dir else None
        self.include_ignored = include_ignored
        self.ignored_dirs = set()
        self.structure_only = False

        # Load config and apply action if provided
        if config_file:
            self.load_config(config_file, action)
        else:
            # Check for contxt.toml in the directory the script was called from
            default_config_path = Path("contxt.toml").resolve()
            if default_config_path.exists():
                logger.info(f"Loading default config from {default_config_path}")
                self.load_config(default_config_path, action)

        # Validate that we have input and output dirs after config loading
        if not self.input_dir or not self.output_dir:
            raise ValueError("Input and output directories must be specified either via CLI or config file")

        # Use input directory name for output files
        dir_name = self.input_dir.name
        self.output_file = self.output_dir / f"structure_{dir_name}.toml"
        self.flattened_file = self.output_dir / f"flattened_{dir_name}.txt"

        # Special filenames without extensions
        self.special_filenames = {
            # Docker and Container Files
            "Dockerfile",
            "dockerfile",
            "Containerfile",
            "containerfile",
            # Build and Package Files
            "Makefile",
            "makefile",
            "Rakefile",
            "rakefile",
            "Gemfile",
            "gemfile",
            "Podfile",
            "podfile",
            "CMakeLists.txt",
            # Configuration Files
            ".env",
            ".gitignore",
            ".dockerignore",
            ".editorconfig",
            ".npmrc",
            ".eslintrc",
            ".prettierrc",
            ".babelrc",
            ".gitconfig",
            ".gitattributes",
            ".hgrc",
            ".bzrignore",
            "requirements.txt",
            "package.json",
            "composer.json",
            "config",
            "configure",
            # Shell and Scripts
            "configure.ac",
            "configure.in",
            # Editor and IDE Files
            ".vimrc",
            ".gvimrc",
            ".ideavimrc",
            # Documentation
            "README",
            "LICENSE",
            "LICENCE",
            "CONTRIBUTING",
            "CHANGELOG",
            "AUTHORS",
            "PATENTS",
            "NOTICE",
            # Security
            ".htaccess",
            ".htpasswd",
        }

        self.text_file_extensions = {
            # Programming Languages
            "py",
            "js",
            "ts",
            "jsx",
            "tsx",
            "vue",
            "rb",
            "php",
            "java",
            "go",
            "rs",
            "c",
            "cpp",
            "h",
            "hpp",
            "cs",
            "swift",
            "kt",
            "scala",
            "html",
            "css",
            "scss",
            "less",
            "md",
            "txt",
            "sh",
            "bash",
            "zsh",
            "json",
            "yaml",
            "yml",
            "xml",
            "sql",
            "graphql",
            "r",
            "m",
            "f",
            "f90",
            "jl",
            "lua",
            "pl",
            "pm",
            "t",
            "ps1",
            "bat",
            "asm",
            "s",
            "nim",
            "ex",
            "exs",
            "clj",
            "lisp",
            "hs",
            "erl",
            "elm",
            "toml",
            ".server",
            ".client",
            # Web Development
            "svelte",
            "astro",
            "liquid",
            "pug",
            "jade",
            "haml",
            "slim",
            "sass",
            "styl",
            "coffee",
            "mjs",
            "cjs",
            "ejs",
            "hbs",
            # Configuration Files
            "ini",
            "cfg",
            "conf",
            "config",
            "env",
            "properties",
            "gitignore",
            "dockerignore",
            "editorconfig",
            "npmrc",
            "eslintrc",
            "prettierrc",
            "babelrc",
            # Documentation
            "rst",
            "adoc",
            "asciidoc",
            "tex",
            "markdown",
            "rdoc",
            "wiki",
            "dokuwiki",
            "mediawiki",
            "creole",
            "mdc",  # Added .mdc extension for documentation
            # Data Formats
            "csv",
            "tsv",
            "jsonl",
            "proto",
            "avsc",
            "thrift",
            "graphqls",
            "prisma",
            "dhall",
            # Shell and Scripts
            "fish",
            "csh",
            "ksh",
            "tcsh",
            "pwsh",
            "cmd",
            "vbs",
            "applescript",
            "nu",
            "action",
            # Template Files
            "tmpl",
            "tpl",
            "j2",
            "jinja",
            "jinja2",
            "mustache",
            "handlebars",
            "hbs",
            "njk",
            "nunjucks",
            # Build and Package Files
            "make",
            "makefile",
            "dockerfile",
            "containerfile",
            "vagrantfile",
            "rakefile",
            "gemfile",
            "podfile",
            "cmake",
            "cabal",
            "gradle",
            # Other Development Files
            "vim",
            "nvim",
            "vimrc",
            "gvimrc",
            "ideavimrc",
            "gitconfig",
            "gitattributes",
            "hgrc",
            "bzrignore",
            # Security and Auth Files
            "pem",
            "crt",
            "key",
            "pub",
            "gpg",
            "asc",
            # Misc Text Files
            "log",
            "diff",
            "patch",
            "po",
            "pot",
            "msg",
            "lst",
            "text",
            "rtf",
            "man",
            "me",
            "ms",
        }

    def load_config(self, config_file, action=None):
        logger.info(f"Loading config from {config_file} with action={action}")
        try:
            with open(config_file, "rb") as f:
                config = tomllib.load(f)
                logger.debug(f"Loaded config: {config}")

                # Load base config settings
                if "input_dir" in config:
                    self.input_dir = Path(config["input_dir"]).resolve()
                if "output_dir" in config:
                    self.output_dir = Path(config["output_dir"]).resolve()
                if "ignore_dirs" in config:
                    self.ignored_dirs = set(config["ignore_dirs"])

                # Apply action-specific settings if a action is specified
                if action and "actions" in config and action in config["actions"]:
                    cmd_config = config["actions"][action]

                    # Update directories if specified in action
                    if "input_dir" in cmd_config:
                        self.input_dir = Path(cmd_config["input_dir"]).resolve()
                    if "output_dir" in cmd_config:
                        self.output_dir = Path(cmd_config["output_dir"]).resolve()

                    # Update ignore_dirs if specified in action
                    if "ignore_dirs" in cmd_config:
                        self.ignored_dirs.update(cmd_config["ignore_dirs"])

                    # Update other settings
                    if "include_ignored" in cmd_config:
                        self.include_ignored = cmd_config["include_ignored"]
                    if "structure_only" in cmd_config:
                        self.structure_only = cmd_config["structure_only"]

        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            logger.warning(f"Failed to load config file: {e}")

    def should_ignore(self, item):
        logger.debug(f"Checking if {item} should be ignored")
        base_item = os.path.basename(item)

        # Check if the file is a lock file
        if base_item.endswith('.lock') or base_item in {
            "package-lock.json", 
            "yarn.lock", 
            "pnpm-lock.yaml",
            "composer.lock",
            "Gemfile.lock",
            "Cargo.lock",
            "poetry.lock",
            "pdm.lock",
            "npm-shrinkwrap.json",
            "bun.lockb"
        }:
            logger.debug(f"Ignoring {item} because it's a lock file")
            return True

        # Check if the path is in ignored directories
        try:
            relative_path = str(Path(item).relative_to(self.input_dir))
            if any(ignored_dir in relative_path.split(os.sep) for ignored_dir in self.ignored_dirs):
                logger.debug(f"Ignoring {item} because it's in ignored directories")
                return True
        except ValueError:
            pass

        # Check if the file is fr.sh
        if base_item == "fr.sh":
            logger.debug(f"Ignoring {item} because it's fr.sh")
            return True

        # Check git ignore unless disabled
        if not self.include_ignored:
            try:
                subprocess.run(["git", "check-ignore", "-q", str(item)], check=True)
                logger.debug(f"Ignoring {item} because it's ignored by git")
                return True
            except subprocess.CalledProcessError:
                pass

        # Check .flattenignore
        flattenignore = self.input_dir / ".flattenignore"
        if flattenignore.exists():
            with open(flattenignore, "r") as f:
                ignored = [line.strip() for line in f if line.strip()]
                if base_item in ignored:
                    logger.debug(f"Ignoring {item} because it's in .flattenignore")
                    return True

        return False

    def create_structure(self):
        logger.info("Creating repository structure")
        structure = {}

        for root, dirs, files in os.walk(self.input_dir):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if not self.should_ignore(os.path.join(root, d))]

            for file in files:
                file_path = os.path.join(root, file)
                if self.should_ignore(file_path):
                    continue

                rel_path = os.path.relpath(file_path, self.input_dir)

                # Count lines in text files
                line_count = 0
                if file in self.special_filenames or Path(file).suffix[1:].lower() in self.text_file_extensions:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            line_count = sum(1 for _ in f)
                    except Exception as e:
                        logger.error(f"Warning: Could not count lines in {rel_path}: {e}")

                structure[rel_path] = {"type": "file", "size": os.path.getsize(file_path), "lines": line_count}
                logger.debug(
                    f"Added {rel_path} to structure (size={structure[rel_path]['size']},",
                    f"  lines={structure[rel_path]['lines']})",
                )

        return structure

    def write_structure_file(self, structure):
        logger.info(f"Writing structure file to {self.output_file}")
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Convert structure to TOML-friendly format
            toml_structure = {"files": {}}
            for path, info in structure.items():
                toml_structure["files"][path] = {"type": info["type"], "size": info["size"], "lines": info["lines"]}

            # Change output file extension to .toml
            self.output_file = self.output_file.with_suffix(".toml")

            with open(self.output_file, "w", encoding="utf-8") as f:
                # Since tomllib is read-only, we'll format the TOML manually
                f.write("# File structure\n\n")
                for path, info in toml_structure["files"].items():
                    f.write(f'[files."{path}"]\n')
                    f.write(f'type = "{info["type"]}"\n')
                    f.write(f"size = {info['size']}\n")
                    f.write(f"lines = {info['lines']}\n\n")

            logger.info(f"Successfully wrote structure file with {len(structure)} entries")
        except Exception as e:
            logger.error(f"Failed to write structure file: {e}")
            logger.warning(f"Failed to write structure file: {e}")

    def print_file_contents(self, file_path):
        logger.debug(f"Processing file contents for {file_path}")
        abs_file_path = self.input_dir / file_path.lstrip("/")

        if not abs_file_path.is_file():
            logger.warning(f"File does not exist: {abs_file_path}")
            return

        if abs_file_path.name == "fr.sh":
            logger.info("Skipping fr.sh script")
            return

        if (
            abs_file_path.name in self.special_filenames
            or abs_file_path.suffix[1:].lower() in self.text_file_extensions
        ):
            try:
                # Count lines first
                line_count = 0
                try:
                    with open(abs_file_path, "r", encoding="utf-8") as f:
                        line_count = sum(1 for _ in f)
                except Exception as e:
                    logger.error(f"Warning: Could not count lines in {file_path}: {e}")

                with open(self.flattened_file, "a", encoding="utf-8") as out:
                    # Try to read with utf-8 first
                    try:
                        with open(abs_file_path, "r", encoding="utf-8") as inp:
                            content = inp.read()
                    except UnicodeDecodeError:
                        # Fallback to read with utf-8 and error replacement
                        with open(abs_file_path, "r", encoding="utf-8", errors="replace") as inp:
                            content = inp.read()

                    out.write(f"<{file_path}> ({line_count} lines)\n")
                    out.write(content)
                    out.write(f"\n</{file_path}>\n\n")
                logger.info(f"Successfully wrote contents of {file_path} ({line_count} lines)")
            except Exception as e:
                logger.error(f"Failed to write contents of {file_path}: {e}")
        else:
            logger.info(f"Skipping non-text file: {file_path}")

    def write_flattened_file(self, structure):
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)

            with open(self.flattened_file, "w", encoding="utf-8") as f:
                for file_path, content in structure.items():
                    if content is None:
                        continue

                    f.write(f"\n=== {file_path} ===\n\n")
                    try:
                        f.write(content)
                    except UnicodeEncodeError as e:
                        logger.warning(f"Failed to write contents of {file_path}: {e}")
                        f.write("[Content contains unsupported characters]\n")
                    f.write("\n")
        except Exception as e:
            logger.error(f"Failed to write flattened file: {e}")

    def read_file_contents(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback to read as binary if UTF-8 fails
            try:
                with open(file_path, "rb") as f:
                    return f.read().decode("utf-8", errors="replace")
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")
                return None
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return None

    def write_markdown_report(self, structure):
        try:
            # Prepare data for sorting
            text_files = []
            for path, info in structure.items():
                # Check if it's a text file
                if (
                    Path(path).name in self.special_filenames
                    or Path(path).suffix[1:].lower() in self.text_file_extensions
                ):
                    text_files.append({"path": path, "size": info["size"], "lines": info["lines"]})

            # Sort by size and lines
            by_size = sorted(text_files, key=lambda x: x["size"], reverse=True)
            by_lines = sorted(text_files, key=lambda x: x["lines"], reverse=True)

            # Create markdown report
            report_path = self.output_dir / f"file_statistics_{self.input_dir.name}.md"
            with open(report_path, "w", encoding="utf-8") as f:
                # Write header
                f.write(f"# File Statistics Report for {self.input_dir.name}\n\n")

                # Files by size
                f.write("## Files Sorted by Size\n\n")
                f.write("| Size (bytes)   | Lines        | File                  |\n")
                f.write("|----------------|--------------|---------------------- |\n")
                for file in by_size[:20]:  # Top 20 files
                    f.write(f"| {file['size']:12,} | {file['lines']:10,} | {file['path']} |\n")

                f.write("\n")  # Spacing between sections

                # Files by line count
                f.write("## Files Sorted by Line Count\n\n")
                f.write("| Size (bytes)   | Lines        | File                  |\n")
                f.write("|----------------|--------------|---------------------- |\n")
                for file in by_lines[:20]:  # Top 20 files
                    f.write(f"| {file['size']:12,} | {file['lines']:10,} | {file['path']} |\n")

                # Summary statistics
                total_size = sum(f["size"] for f in text_files)
                total_lines = sum(f["lines"] for f in text_files)
                total_files = len(text_files)

                f.write("\n## Summary\n\n")
                f.write(f"- Total text files: {total_files:,}\n")
                f.write(f"- Total size: {total_size:,} bytes\n")
                f.write(f"- Total lines: {total_lines:,}\n")
                f.write(f"- Average size: {total_size / total_files:,.2f} bytes per file\n")
                f.write(f"- Average lines: {total_lines / total_files:,.2f} lines per file\n")

            logger.info(f"Markdown statistics report has been created as {report_path}")

        except Exception as e:
            logger.error(f"Failed to write markdown report: {e}")

    def run(self, structure_only=False):
        logger.info(f"Starting repository flattening (structure_only={structure_only})")
        # Delete existing files
        for file in [self.output_file, self.flattened_file]:
            if file.exists():
                file.unlink()

        # Generate structure and write to TOML file
        structure = self.create_structure()
        self.write_structure_file(structure)
        logger.info(f"TOML file with folder/file structure has been created as {self.output_file}")

        # Generate markdown report
        self.write_markdown_report(structure)

        if not structure_only:
            logger.info("Flattening repository...")
            self.flattened_file.touch()

            # Process each file in the structure
            for file_path in structure.keys():
                self.print_file_contents(file_path)

            logger.info(f"Flattened repository content has been created as {self.flattened_file}")
        else:
            logger.info(
                "Repository structure created. Use without --structure-only to include file contents in",
                f"{self.flattened_file}",
            )
        logger.success("Repository flattening completed successfully")


@click.command()
@click.argument(
    "input_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path), required=False
)
@click.argument("output_dir", type=click.Path(file_okay=False, dir_okay=True, path_type=Path), required=False)
@click.option("--structure-only", is_flag=True, help="Generate only the structure YAML file without file contents")
@click.option("--include-ignored", is_flag=True, help="Include files that are listed in .gitignore")
@click.option("--config", "-c", type=click.Path(exists=True, dir_okay=False), help="Path to config file (TOML)")
@click.option("--action", "-a", help="Use predefined action from config file")
def main(input_dir, output_dir, structure_only, include_ignored, config, action):
    """
    Flatten a repository structure into a YAML file and include file contents by default.

    INPUT_DIR: The directory to analyze (optional if specified in config)
    OUTPUT_DIR: The directory where output files will be created (optional if specified in config)
    """
    if input_dir and not output_dir:
        output_dir = Path(".local") / "contxt" / Path(input_dir).name
        logger.info(f"Using standardized local output directory: {output_dir.resolve()}")
    try:
        flattener = RepoFlattener(input_dir, output_dir, include_ignored, config, action)
        structure_only = flattener.structure_only if action else structure_only
        flattener.run(structure_only=structure_only)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
