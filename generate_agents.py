import os
import json
from pathlib import Path

SKIP_LIST = {'node_modules', '.git', '__pycache__', '.venv', 'dist', 'build', '.next', 'coverage'}

def is_skipped(path_str):
    parts = Path(path_str).parts
    return any(part in SKIP_LIST for part in parts)

def generate_directory_tree(root_dir, out_file):
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write("# Project Directory Tree\n\n```text\n")
        for root, dirs, files in os.walk(root_dir):
            dirs.sort()
            files.sort()
            # remove skipped dirs
            dirs[:] = [d for d in dirs if d not in SKIP_LIST]
            
            rel_path = os.path.relpath(root, root_dir)
            if rel_path == '.':
                level = 0
                f.write(".\n")
            else:
                level = len(rel_path.split(os.sep))
                indent = '    ' * (level - 1)
                basename = os.path.basename(root)
                f.write(f"{indent}├── {basename}/\n")
                
            subindent = '    ' * level
            for file in files:
                f.write(f"{subindent}├── {file}\n")
        f.write("```\n")

def generate_heuristic_content(dir_path, is_root=False):
    dir_name = os.path.basename(os.path.abspath(dir_path))
    if is_root:
        dir_name = "Root Directory"
        
    try:
        files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
        dirs = [d for d in os.listdir(dir_path) if os.path.isdir(os.path.join(dir_path, d)) and d not in SKIP_LIST]
    except:
        files = []
        dirs = []
        
    if is_root:
        content = f"""# {dir_name} Context

## Overall Project Purpose and Architecture
This is the root directory of the Voice-Vision-Assistant-for-Blind project. It contains the primary configuration, orchestration, and documentation for the entire application. The architecture relies on various modules for audio, vision, reasoning, and speech.

## Tech Stack and Major Dependencies
- Python (Core application)
- Containerization (Docker/Compose)
- Various ML/AI APIs (LLM, Speech, Vision)
- Infrastructure components (Grafana, Prometheus, Loki)

## Build, Run, and Test Instructions
- Run: Use `docker-compose` or equivalent deployment scripts in `deployments/`.
- Test: Run `pytest tests/`.
- Build: Refer to `Dockerfile` and setup guides in `docs/`.

## High-Level Folder Structure Overview
{', '.join(dirs) if dirs else 'N/A'}

## Immediate Subdirectories
"""
        for d in dirs:
            content += f"- [{d}](./{d}/AGENTS.md)\n"
            
    else:
        purpose_guess = f"Module responsible for {dir_name.replace('_', ' ')} functionality."
        if 'test' in dir_name.lower():
            purpose_guess = f"Testing directory for {dir_name.replace('_', ' ')}."
        elif 'docs' in dir_name.lower():
            purpose_guess = "Documentation and reference materials."
            
        content = f"""# {dir_name.capitalize()} Context

## Purpose
{purpose_guess}

## Key Files
"""
        if files:
            for f in files[:10]: # limit to 10
                content += f"- `{f}`: Implementation/configuration file.\n"
            if len(files) > 10:
                content += f"- ... and {len(files)-10} more files.\n"
        else:
            content += "No prominent files directly in this directory.\n"

        content += f"""
## Patterns and Conventions
- Follow standard Python naming conventions.
- Maintain modularity and single responsibility.
- Refer to `conductor/` or root guidelines for specific architectural patterns.

## Dependencies
- Interacts with sibling modules and shared utilities.
{'- Relies on core/ and shared/ components.' if dir_name not in ['core', 'shared'] else ''}

## Gotchas and Important Notes
- Ensure paths are resolved relative to the project root.
- Watch out for circular dependencies when importing from other modules.
"""
    return content

def main():
    try:
        with open('bottom_up_dirs.txt', 'r', encoding='utf-8') as f:
            dirs_to_process = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading bottom_up_dirs.txt: {e}")
        return
        
    if '.' not in dirs_to_process and '.\\' not in dirs_to_process and './' not in dirs_to_process:
        dirs_to_process.append('.')
        
    scanned = 0
    created = 0
    updated = 0
    skipped = 0
    
    generate_directory_tree('.', 'DIRECTORY_TREE.md')
    
    for dir_path in dirs_to_process:
        scanned += 1
        
        norm_path = os.path.normpath(dir_path)
        
        # Format display path strictly as ./path/to/something
        display_path = dir_path.replace('\\\\', '/').replace('\\', '/')
        if display_path == '.':
            pass
        elif display_path.startswith('./'):
            pass
        else:
            display_path = './' + display_path
            
        if is_skipped(norm_path):
            print(f"⊘ Skipped: {display_path} (excluded)")
            skipped += 1
            continue
            
        is_root = (norm_path == '.' or norm_path == '')
        
        agents_file = os.path.join(norm_path, 'AGENTS.md')
        content = generate_heuristic_content(norm_path, is_root)
        
        if os.path.exists(agents_file):
            updated += 1
        else:
            created += 1
            
        try:
            with open(agents_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            if display_path == '.':
                print(f"✓ Written: ./AGENTS.md")
            else:
                print(f"✓ Written: {display_path}/AGENTS.md")
        except Exception as e:
            print(f"Error writing to {agents_file}: {e}")
            
    print(f"\nSummary: {scanned} scanned, {created} created, {updated} updated, {skipped} skipped.")

if __name__ == "__main__":
    main()
