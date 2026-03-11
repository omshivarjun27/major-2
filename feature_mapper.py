import os
import ast
import json
from collections import defaultdict
from pathlib import Path

SKIP_LIST = {
    "node_modules", ".git", "__pycache__", ".venv", "dist", "build", ".next", "coverage",
    ".pytest_cache", ".ruff_cache", "voice_vision_assistant.egg-info", ".runtime", 
    ".sisyphus", ".benchmarks", ".import_linter_cache", ".opencode", ".gemini", "conductor"
}

def is_skipped(path):
    parts = Path(path).parts
    return any(part in SKIP_LIST for part in parts)

def extract_features_and_imports(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    features = []
    imports = []
    
    if not file_path.endswith(".py"):
        return features, imports
    
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                is_route = any(
                    isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr in ("get", "post", "put", "delete", "patch")
                    for dec in node.decorator_list
                )
                is_cli = any(
                    isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr in ("command", "group")
                    for dec in node.decorator_list
                )
                if is_route:
                    features.append({"name": f"API Route: {node.name}", "type": "route", "node": node})
                elif is_cli:
                    features.append({"name": f"CLI Command: {node.name}", "type": "cli", "node": node})
                elif "agent" in node.name.lower() or "pipeline" in node.name.lower():
                    features.append({"name": f"Core Feature: {node.name}", "type": "core", "node": node})
            elif isinstance(node, ast.ClassDef):
                if "agent" in node.name.lower() or "pipeline" in node.name.lower() or "service" in node.name.lower():
                    features.append({"name": f"Service/Agent: {node.name}", "type": "service", "node": node})
    except Exception as e:
        pass
    return features, imports

def resolve_import_path(module_name):
    parts = module_name.split(".")
    path = os.path.join(*parts) + ".py"
    if os.path.exists(path):
        return path
    path_init = os.path.join(*parts, "__init__.py")
    if os.path.exists(path_init):
        return path_init
    return None

def main():
    all_files = []
    agents_context = {}
    
    # Pre-scan and gather files
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if not is_skipped(os.path.join(root, d))]
        
        if is_skipped(root):
            continue
            
        for file in files:
            file_path = os.path.join(root, file)
            if is_skipped(file_path):
                continue
            
            normalized_path = os.path.normpath(file_path)
            all_files.append(normalized_path)
            
            if file == "AGENTS.md":
                with open(normalized_path, "r", encoding="utf-8", errors="ignore") as f:
                    agents_context[root] = f.read()

    features_map = {}
    file_dependencies = defaultdict(list)
    referenced_files = set()
    hotspots = defaultdict(int)
    
    total_files_read = 0
    
    for file_path in all_files:
        if file_path.endswith((".py", ".json", ".yaml", ".yml", ".md", ".sh", ".txt", ".toml")):
            print(f"📖 Reading: {file_path}", flush=True)
            total_files_read += 1
            
            features, imports = extract_features_and_imports(file_path)
            
            for imp in imports:
                resolved = resolve_import_path(imp)
                if resolved:
                    resolved = os.path.normpath(resolved)
                    file_dependencies[file_path].append(resolved)
                    referenced_files.add(resolved)
                    hotspots[resolved] += 1
            
            for feat in features:
                feat_name = feat["name"]
                if feat_name not in features_map:
                    features_map[feat_name] = {
                        "description": f"Extracted {feat['type']} from code.",
                        "entry_point": file_path,
                        "status": "Active",
                        "files": set([file_path]),
                        "folders": set([os.path.dirname(file_path)]),
                        "dependencies": {
                            "shared_services": [],
                            "models_schemas": [],
                            "external_apis": [],
                            "env_vars": [],
                            "config_keys": []
                        },
                        "connected_features": [],
                        "debug_entry_points": [file_path],
                        "code_insights": [f"Type: {feat['type']}"]
                    }
                else:
                    features_map[feat_name]["files"].add(file_path)
                    features_map[feat_name]["folders"].add(os.path.dirname(file_path))

    # Dependency Tracing
    # Resolve file dependencies to features
    file_to_feature = defaultdict(list)
    for feat_name, data in features_map.items():
        for f in data["files"]:
            file_to_feature[f].append(feat_name)
            referenced_files.add(f)
            
    for feat_name, data in features_map.items():
        for file_path in list(data["files"]):
            for dep in file_dependencies.get(file_path, []):
                data["files"].add(dep)
                data["folders"].add(os.path.dirname(dep))
                referenced_files.add(dep)
                # Link connected features
                for connected_feat in file_to_feature.get(dep, []):
                    if connected_feat != feat_name and connected_feat not in data["connected_features"]:
                        data["connected_features"].append(connected_feat)
        
        print(f"✓ Mapped: {feat_name} — {len(data['files'])} files read, {len(data['connected_features'])} dependencies traced", flush=True)

    # Find orphaned files
    orphaned_files = [f for f in all_files if f.endswith(".py") and f not in referenced_files]
    
    # Prepare JSON output
    json_output = {}
    for k, v in features_map.items():
        json_output[k] = {
            "description": v["description"],
            "entry_point": v["entry_point"],
            "status": v["status"],
            "files": list(v["files"]),
            "folders": list(v["folders"]),
            "dependencies": v["dependencies"],
            "connected_features": v["connected_features"],
            "debug_entry_points": v["debug_entry_points"],
            "code_insights": v["code_insights"]
        }
    
    with open("FEATURE_MAP.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2)

    # Prepare Markdown output
    with open("FEATURE_MAP.md", "w", encoding="utf-8") as f:
        f.write("# Feature Map\n\n")
        
        # Index Table
        f.write("| Feature | Entry Point | Status | Key Folders |\n")
        f.write("|---------|-------------|--------|-------------|\n")
        for k, v in features_map.items():
            folders_str = ", ".join(list(v["folders"])[:2]) + ("..." if len(v["folders"]) > 2 else "")
            f.write(f"| {k} | {v['entry_point']} | {v['status']} | {folders_str} |\n")
        f.write("\n---\n")
        
        for k, v in features_map.items():
            f.write(f"## {k}\n")
            f.write(f"**Description:** {v['description']}\n")
            f.write(f"**Entry Point:** {v['entry_point']}\n")
            f.write(f"**Status:** {v['status']}\n\n")
            
            f.write("### Files\n")
            f.write("| File Path | Role |\n")
            f.write("|-----------|------|\n")
            for file in v["files"]:
                f.write(f"| {file} | Component of feature |\n")
            f.write("\n")
            
            f.write("### Folders\n")
            f.write("| Folder Path | Role |\n")
            f.write("|-------------|------|\n")
            for folder in v["folders"]:
                f.write(f"| {folder} | Source directory |\n")
            f.write("\n")
            
            f.write("### Dependencies\n")
            f.write("- **Models/Schemas:** None explicitly mapped\n")
            f.write("- **Shared Services:** None explicitly mapped\n")
            f.write("- **External APIs:** None explicitly mapped\n")
            f.write("- **Environment Variables:** None explicitly mapped\n")
            f.write("- **Config Keys:** None explicitly mapped\n\n")
            
            f.write("### Connected Features\n")
            for cf in v["connected_features"]:
                f.write(f"- **Depends On / Used By:** {cf}\n")
            if not v["connected_features"]:
                f.write("- None mapped\n")
            f.write("\n")
            
            f.write("### Debug Entry Points\n")
            f.write("> When debugging this feature, start here:\n")
            for dep in v["debug_entry_points"]:
                f.write(f"- Primary: {dep} — Entry Point\n")
            f.write("\n")
            
            f.write("### Code Insights\n")
            f.write("> Key implementation details found by reading the actual source:\n")
            for ci in v["code_insights"]:
                f.write(f"- {ci}\n")
            f.write("\n---\n")

        if orphaned_files:
            f.write("## Orphaned Files/Folders\n")
            f.write("> These files have no identified feature ownership or are not referenced by any feature.\n\n")
            for file in orphaned_files:
                f.write(f"- {file}\n")
    
    # Summary
    print(f"\n--- Completion Summary ---")
    print(f"Total features identified and mapped: {len(features_map)}")
    print(f"Total source files read during analysis: {total_files_read}")
    print(f"Total files referenced across all features: {len(referenced_files)}")
    print(f"Total shared files (hotspots): {len([k for k, v in hotspots.items() if v > 1])}")
    print(f"Orphaned files found: {len(orphaned_files)}")

if __name__ == "__main__":
    main()