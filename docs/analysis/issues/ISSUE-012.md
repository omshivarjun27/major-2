---
id: ISSUE-012
title: FAISS Index and Memory Metadata Not Encrypted at Rest
severity: medium
source_artifact: architecture_risks.md
architecture_layer: core
---

## Description
The FAISS index and `metadata.json` are stored as plaintext files on disk. An import for `shared.utils.encryption.get_encryption_manager` exists in `core/memory/indexer.py` but is not wired into the `add()`, `_save()`, or `_load()` methods. Memory summaries (potentially containing personal location/activity data) are stored unencrypted.

## Root Cause
Encryption infrastructure was partially implemented (import exists) but never integrated into the persistence path. The `_save()` method writes raw FAISS binary and JSON without invoking encryption.

## Impact
Personal data (location history, activity descriptions, object sightings) stored in plaintext on disk. If the device is lost or compromised, sensitive user data is exposed. This is particularly concerning for an assistive device used by vulnerable users.

## Reproducibility
always

## Remediation Plan
1. Wire the existing `get_encryption_manager()` into `FAISSIndexer._save()` and `_load()`.
2. Encrypt `metadata.json` and FAISS index binary before writing to disk.
3. Add key management (e.g., derive from user passphrase or device-bound key).
4. Handle migration: encrypt existing unencrypted files on first load.

## Implementation Suggestion
```python
def _save(self):
    enc = get_encryption_manager()
    # Save FAISS index to bytes buffer
    index_bytes = faiss.serialize_index(self.index)
    encrypted_index = enc.encrypt(index_bytes)
    with open(self.index_path, 'wb') as f:
        f.write(encrypted_index)
    # Encrypt metadata
    meta_json = json.dumps(self.metadata).encode()
    with open(self.metadata_path, 'wb') as f:
        f.write(enc.encrypt(meta_json))
```

## GPU Impact
N/A

## Cloud Impact
N/A

## Acceptance Criteria
- [ ] FAISS index file encrypted at rest using `get_encryption_manager()`
- [ ] `metadata.json` encrypted at rest
- [ ] Existing unencrypted indexes auto-migrated to encrypted format on first load
- [ ] Decryption verified on application restart (index loads successfully)
