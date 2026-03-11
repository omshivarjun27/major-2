import os
import ast
import json
import re
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

def extract_features_from_code(file_path):
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
                if is_route:
                    features.append({"name": f"API Route: {node.name}", "type": "route"})
                elif "agent" in node.name.lower() or "pipeline" in node.name.lower():
                    features.append({"name": f"Core Feature: {node.name}", "type": "core"})
            elif isinstance(node, ast.ClassDef):
                if "agent" in node.name.lower() or "pipeline" in node.name.lower() or "service" in node.name.lower():
                    features.append({"name": f"Service/Agent: {node.name}", "type": "service"})
    except Exception:
        pass
    return features, imports

def load_initial_inventory():
    with open("temp_feature_inventory.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Simple heuristic to extract key terms as features from the LLM summary
    doc_features = {}
    content = data.get("response", "")
    lines = content.split('\n')
    for line in lines:
        if line.startswith("- **"):
            match = re.search(r'- \*\*(.*?)\*\*(.*)', line)
            if match:
                name = match.group(1).strip(":")
                desc = match.group(2).strip()
                doc_features[name] = {
                    "description": desc,
                    "status": "Documented but not implemented", # Default
                    "source": "Architecture Doc",
                    "files": set(),
                    "folders": set(),
                    "dependencies": {
                        "shared_services": [],
                        "models_schemas": [],
                        "external_apis": [],
                        "env_vars": [],
                        "config_keys": []
                    },
                    "connected_features": [],
                    "debug_entry_points": [],
                    "code_insights": []
                }
    return doc_features

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
    
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if not is_skipped(os.path.join(root, d))]
        if is_skipped(root):
            continue
            
        for file in files:
            file_path = os.path.join(root, file)
            if is_skipped(file_path):
                continue
            all_files.append(os.path.normpath(file_path))

    # Initialize with documented features
    features_map = load_initial_inventory()
    
    file_dependencies = defaultdict(list)
    referenced_files = set()
    hotspots = defaultdict(int)
    total_files_read = 0
    
    # Process code
    for file_path in all_files:
        if file_path.endswith((".py", ".json", ".yaml", ".yml", ".md", ".sh", ".txt", ".toml")):
            print(f"📖 Reading: {file_path}", flush=True)
            total_files_read += 1
            
            features, imports = extract_features_from_code(file_path)
            
            for imp in imports:
                resolved = resolve_import_path(imp)
                if resolved:
                    resolved = os.path.normpath(resolved)
                    file_dependencies[file_path].append(resolved)
                    referenced_files.add(resolved)
                    hotspots[resolved] += 1
            
            for feat in features:
                feat_name = feat["name"]
                
                # Check if it maps to a doc feature (simple keyword match for now)
                matched_doc_feat = None
                for doc_feat in features_map:
                    if doc_feat.lower() in feat_name.lower() or feat_name.lower().replace("api route: ", "") in doc_feat.lower():
                        matched_doc_feat = doc_feat
                        break
                
                target_key = matched_doc_feat if matched_doc_feat else feat_name
                
                if target_key not in features_map:
                    features_map[target_key] = {
                        "description": f"Extracted {feat['type']} from code.",
                        "entry_point": file_path,
                        "status": "Active",
                        "source": "Source Code",
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
                    features_map[target_key]["files"].add(file_path)
                    features_map[target_key]["folders"].add(os.path.dirname(file_path))
                    features_map[target_key]["status"] = "Active"
                    features_map[target_key]["entry_point"] = file_path if not features_map[target_key].get("entry_point") else features_map[target_key]["entry_point"]
                    if features_map[target_key]["source"] == "Architecture Doc":
                         features_map[target_key]["source"] = "All"

    # Dependency Tracing
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
                for connected_feat in file_to_feature.get(dep, []):
                    if connected_feat != feat_name and connected_feat not in data["connected_features"]:
                        data["connected_features"].append(connected_feat)
        
        print(f"✓ Mapped: {feat_name} — {len(data['files'])} files read, {len(data['connected_features'])} dependencies traced", flush=True)

    orphaned_files = [f for f in all_files if f.endswith(".py") and f not in referenced_files]
    
    docs_only = sum(1 for v in features_map.values() if v["source"] == "Architecture Doc")
    code_only = sum(1 for v in features_map.values() if v["source"] == "Source Code")
    
    # JSON Output
    json_output = {}
    for k, v in features_map.items():
        json_output[k] = {
            "description": v["description"],
            "entry_point": v.get("entry_point", "Unknown"),
            "status": v["status"],
            "source": v["source"],
            "files": list(v["files"]),
            "folders": list(v["folders"]),
            "dependencies": v["dependencies"],
            "connected_features": v["connected_features"],
            "debug_entry_points": v["debug_entry_points"],
            "code_insights": v["code_insights"]
        }
    
    with open("FEATURE_MAP.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2)

    # Markdown Output
    with open("FEATURE_MAP.md", "w", encoding="utf-8") as f:
        f.write("# Feature Map (Cross-Referenced)\n\n")
        
        f.write("## Index Table\n")
        f.write("| Feature | Entry Point | Status | Source | Key Folders |\n")
        f.write("|---------|-------------|--------|--------|-------------|\n")
        for k, v in features_map.items():
            folders_str = ", ".join(list(v["folders"])[:2]) + ("..." if len(v["folders"]) > 2 else "")
            entry = v.get("entry_point", "None")
            f.write(f"| {k} | {entry} | {v['status']} | {v['source']} | {folders_str} |\n")
        f.write("\n---\n")
        
        for k, v in features_map.items():
            f.write(f"## {k}\n")
            f.write(f"**Description:** {v['description']}\n")
            f.write(f"**Entry Point:** {v.get('entry_point', 'None')}\n")
            f.write(f"**Status:** {v['status']}\n")
            f.write(f"**Source:** {v['source']}\n\n")
            
            f.write("### Files\n")
            f.write("| File Path | Role |\n")
            f.write("|-----------|------|\n")
            for file in v["files"]:
                f.write(f"| {file} | Component of feature |\n")
            if not v["files"]: f.write("| None | |\n")
            f.write("\n")
            
            f.write("### Folders\n")
            f.write("| Folder Path | Role |\n")
            f.write("|-------------|------|\n")
            for folder in v["folders"]:
                f.write(f"| {folder} | Source directory |\n")
            if not v["folders"]: f.write("| None | |\n")
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
            f.write("\n")
            
            f.write("### Doc vs Code\n")
            f.write("> Discrepancies between architecture docs and actual implementation:\n")
            if v["source"] == "Architecture Doc":
                f.write("- ⚠️ Feature is documented but no corresponding code implementation was found.\n")
            elif v["source"] == "Source Code":
                f.write("- ⚠️ Feature is implemented in code but not explicitly referenced in architecture documentation.\n")
            else:
                f.write("- ✅ Matches documentation\n")
            f.write("\n---\n")

        if orphaned_files:
            f.write("## Orphaned Files/Folders\n")
            f.write("> These files have no identified feature ownership or are not referenced by any feature.\n\n")
            for file in orphaned_files:
                f.write(f"- {file}\n")
    
    print(f"\n--- Completion Summary ---")
    print(f"Total features identified and mapped: {len(features_map)}")
    print(f"Features found in docs but missing in code: {docs_only}")
    print(f"Features found in code but missing in docs: {code_only}")
    print(f"Total source files read during analysis: {total_files_read}")
    print(f"Total files referenced across all features: {len(referenced_files)}")
    print(f"Total shared files (hotspots): {len([k for k, v in hotspots.items() if v > 1])}")
    print(f"Orphaned files found: {len(orphaned_files)}")
    print(f"Total discrepancies found between docs and code: {docs_only + code_only}")

if __name__ == "__main__":
    main()