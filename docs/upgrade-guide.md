# Upgrade Guide

**Version**: 1.0.0 | **Date**: 2026-03-02

This guide covers how to upgrade Voice & Vision Assistant from a previous version
to the current release.

---

## Upgrading to 1.0.0

### Breaking Changes

None — this is the initial production release.

---

## General Upgrade Procedure

### 1. Review the CHANGELOG

```bash
# View changes since last release
cat CHANGELOG.md
```

### 2. Validate your environment

```bash
python scripts/validate_env.py
```

Fix any missing or changed environment variables before proceeding.

### 3. Pull the new image

```bash
docker pull voice-vision-assistant:NEW_VERSION
```

### 4. Run smoke tests in staging

Deploy the new image to a staging environment first:

```bash
docker run -d --name vva-staging -p 8001:8000 \
  --env-file .env.staging \
  voice-vision-assistant:NEW_VERSION

python scripts/run_smoke.py --base-url http://localhost:8001
```

### 5. Canary deploy to production

```bash
# Start canary at 10%
python scripts/canary_deploy.py start --image voice-vision-assistant:NEW_VERSION

# Monitor for 2 hours
python scripts/canary_analysis.py --watch

# Promote if metrics are healthy
python scripts/canary_promote.py promote --weight 100
```

### 6. Rollback if needed

```bash
python scripts/canary_promote.py rollback --reason "upgrade issue: <describe>"
```

---

## Configuration Changes

### New environment variables (per release)

Check the release notes for any new required or optional environment variables.
Run `python scripts/validate_env.py` after updating your `.env` file.

### Feature flag changes

New features are off by default. Review `shared/config/settings.py` to see
available feature flags and their defaults.

---

## Database / Data Migrations

### FAISS index

The FAISS index format is backward compatible within the same major version.
If upgrading across major versions, rebuild the index:

```bash
# Back up existing index
cp -r data/memory data/memory.bak

# Re-ingest from source data
python -m core.memory.ingester --rebuild
```

### Face embeddings

Face embeddings are stored encrypted. If the encryption key changes, you must
re-enrol faces. The system will detect format mismatches at startup and emit a
warning.

---

## Rollback Procedure

If an upgrade causes problems:

1. **Immediate rollback** (canary):
   ```bash
   python scripts/canary_promote.py rollback --reason "post-upgrade issues"
   ```

2. **Full rollback** (replace container):
   ```bash
   docker stop vva && docker rm vva
   docker run -d --name vva -p 8000:8000 -p 8081:8081 \
     --env-file .env voice-vision-assistant:PREVIOUS_VERSION
   ```

3. Verify health:
   ```bash
   python scripts/run_smoke.py
   ```

---

## Getting Help

For upgrade assistance, open an issue at:
<https://github.com/codingaslu/Envision-AI/issues>
