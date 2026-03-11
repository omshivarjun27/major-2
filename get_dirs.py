import os

def get_bottom_up_dirs(root_dir, ignore_dirs):
    dir_list = []
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        # Filter out ignored directories
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs and not d.startswith('.pytest_cache') and not d.startswith('.ruff_cache')]
        
        # Check if current dir path contains any ignored directory (since topdown=False doesn't prevent entering them if not filtered properly, wait topdown=False means we process children first. We need to filter paths)
        parts = dirpath.split(os.sep)
        if any(p in ignore_dirs or p.startswith('.pytest_cache') or p.startswith('.ruff_cache') for p in parts):
            continue
            
        if dirpath == ".":
            continue
        dir_list.append(dirpath)
    return dir_list

if __name__ == "__main__":
    ignore = {"node_modules", ".git", "__pycache__", ".venv", "dist", "build", ".next", "coverage", ".pytest_cache", ".ruff_cache", "voice_vision_assistant.egg-info", ".runtime", ".sisyphus", ".benchmarks", ".import_linter_cache", ".opencode", ".gemini", "conductor"}
    
    dirs = get_bottom_up_dirs(".", ignore)
    with open("bottom_up_dirs.txt", "w") as f:
        for d in dirs:
            f.write(f"{d}\n")
    print(f"Total directories to process: {len(dirs)}")
