#!/usr/bin/env python3
import os
from pathlib import Path


# Directories we don't want to include
IGNORED_DIRS = {
	"venv", ".venv", "__pycache__", ".git", ".hg", ".svn", ".idea", ".vscode",
	"node_modules", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
	"dist", "build", "target", ".terraform", ".coverage",
	"decom", "flask_session"   # <-- explicitly excluded
}


# File extensions to skip (compiled, binaries, media, archives, etc.)
IGNORED_EXTS = {
	".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe", ".bin",
	".zip", ".tar", ".gz", ".bz2", ".xz", ".7z",
	".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".pdf",
	".mov", ".mp4", ".mp3", ".wav", ".ogg", ".flac",
	".db", ".sqlite", ".lock", ".DS_Store", ".pem", ".md", ".txt", ".env", "env", ".example"
}


OUTPUT_FILE = "project_dump.txt"   # written in the current directory
SCRIPT_FILE = "dump.py"        	# skip this file
MAX_FILE_SIZE_MB = 2.0         	# skip files larger than this




def looks_binary(sample: bytes) -> bool:
	"""Heuristic: detect if file looks binary from a sample chunk."""
	if b"\x00" in sample:
		return True
	textchars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x7F)))
	if not sample:
		return False
	nontext = sum(b not in textchars for b in sample)
	return (nontext / len(sample)) > 0.30




def main():
	project_path = Path.cwd()
	output_path = project_path / OUTPUT_FILE
	script_path = project_path / SCRIPT_FILE


	with open(output_path, "w", encoding="utf-8") as out:
		files_written = 0
		files_skipped = 0
		dirs_seen = 0


		for root, dirs, files in os.walk(project_path, topdown=True, followlinks=False):
			# Filter out ignored directories
			dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
			# Skip hidden dirs (except .github)
			dirs[:] = [d for d in dirs if not d.startswith(".") or d in {".github"}]


			rel_path = os.path.relpath(root, project_path)
			rel_path = "" if rel_path == "." else rel_path


			# Write directory header
			out.write(f"\n# Directory: {rel_path or project_path}\n")
			out.write("=" * (len(rel_path or str(project_path)) + 12) + "\n\n")
			dirs_seen += 1


			for fname in files:
				fpath = Path(root) / fname


				# Skip the output file and this script itself
				if fpath.resolve() in {output_path.resolve(), script_path.resolve()}:
					files_skipped += 1
					continue


				# Skip by extension
				if fpath.suffix.lower() in IGNORED_EXTS:
					files_skipped += 1
					continue


				# Skip large files
				try:
					if fpath.stat().st_size > MAX_FILE_SIZE_MB * 1024 * 1024:
						files_skipped += 1
						continue
				except Exception:
					files_skipped += 1
					continue


				# Binary check
				try:
					with open(fpath, "rb") as fb:
						if looks_binary(fb.read(8192)):
							files_skipped += 1
							continue
				except Exception:
					files_skipped += 1
					continue


				# Read text content
				try:
					content = fpath.read_text(encoding="utf-8")
				except UnicodeDecodeError:
					try:
						content = fpath.read_text(encoding="latin-1")
					except Exception as e:
						content = f"<<Could not read file (latin-1): {e}>>"
				except Exception as e:
					content = f"<<Could not read file: {e}>>"


				out.write(f"## File: {os.path.join(rel_path, fname) if rel_path else fname}\n\n")
				out.write(content)
				out.write("\n\n" + ("-" * 80) + "\n\n")
				files_written += 1


		# Write summary
		out.write(f"\n# Summary\n")
		out.write(f"Directories seen: {dirs_seen}\n")
		out.write(f"Files written:	{files_written}\n")
		out.write(f"Files skipped:	{files_skipped}\n")


	print(f"Wrote {OUTPUT_FILE} in {project_path}")




if __name__ == "__main__":
	main()

