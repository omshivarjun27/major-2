# T-106: Docker Compose Environments

## Status: completed

## Objective
Create Docker Compose configurations for dev, staging, and production environments with Prometheus/Grafana services, volume configs, and environment variable templates.

## Deliverables

### 1. Development Compose (`deployments/compose/docker-compose.dev.yml`)
- **Size**: 90 lines
- **Features**:
  - Hot-reloading via source volume mounts
  - Local Ollama service for LLM
  - Debug logging enabled
  - Relaxed timeouts
  - GPU support

### 2. Staging Compose (`deployments/compose/docker-compose.staging.yml`)
- **Size**: 133 lines
- **Features**:
  - Full monitoring stack (Prometheus, Grafana, Loki, Alertmanager)
  - Mirrors production with reduced resources (75%)
  - 14-day retention for metrics/logs
  - Container image from registry
  - Resource limits enforced

### 3. Production Compose (`deployments/compose/docker-compose.prod.yml`)
- **Size**: 245 lines
- **Features**:
  - Docker Secrets for sensitive credentials
  - Blue-green deployment configuration
  - Full monitoring stack
  - Nginx reverse proxy
  - Promtail log shipping
  - 30-day retention
  - Replicated service (2 instances)
  - Rolling update configuration
  - Health check dependencies

### 4. Test Compose (`deployments/compose/docker-compose.test.yml`)
- **Size**: 88 lines
- **Features**:
  - Mock LLM service
  - Integration test runner
  - Extended timeouts for CI
  - Test result volume

### 5. Key Features Across All Environments

#### Services Included
| Service | Dev | Staging | Prod | Test |
|---------|-----|---------|------|------|
| Assistant | ✅ | ✅ | ✅ (x2) | ✅ |
| Ollama | ✅ | - | - | Mock |
| Prometheus | - | ✅ | ✅ | - |
| Alertmanager | - | ✅ | ✅ | - |
| Grafana | - | ✅ | ✅ | - |
| Loki | - | ✅ | ✅ | - |
| Promtail | - | - | ✅ | - |
| Nginx | - | - | ✅ | - |

#### Environment Variables
- `ENVIRONMENT` - development/staging/production/test
- `LOG_LEVEL` - DEBUG/INFO/WARNING
- `LOG_FORMAT` - text/json
- `PII_SCRUB` - true/false

#### Volume Configuration
- Data persistence across restarts
- Log aggregation volumes
- Backup volumes (staging/prod)
- Prometheus/Grafana data volumes

#### Docker Secrets (Production)
```yaml
secrets:
  - deepgram_api_key
  - elevenlabs_api_key
  - ollama_api_key
  - livekit_api_key
  - livekit_api_secret
  - grafana_password
```

### 6. Usage Examples

```bash
# Development
docker compose -f deployments/compose/docker-compose.dev.yml up

# Staging
docker compose -f deployments/compose/docker-compose.staging.yml up -d

# Production
docker compose -f deployments/compose/docker-compose.prod.yml up -d

# Run tests
docker compose -f deployments/compose/docker-compose.test.yml --profile run-tests up
```

## Verification
- [x] Development compose with hot-reload
- [x] Staging compose with monitoring stack
- [x] Production compose with secrets and replicas
- [x] Test compose with mock services
- [x] All environments use consistent health checks
- [x] GPU support configured where needed
- [x] Network isolation per environment

## Completion Date
2026-02-28
