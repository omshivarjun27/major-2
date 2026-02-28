# OpenCode + AWS Bedrock — Setup & Integration Guide

> Complete guide covering IAM setup, credential configuration, model selection, SDK examples, CI/CD, and troubleshooting.

---

## 1 — Quick Overview

| Step | Action |
|------|--------|
| 1 | Get Bedrock model access in AWS Console |
| 2 | Give an IAM identity permission to call Bedrock (`InvokeModel`, `ListFoundationModels`, etc.) |
| 3 | Install OpenCode and configure provider credentials (env vars or AWS profile) |
| 4 | Use OpenCode's `/models` and `--model` flags to pick a Bedrock model and run prompts |

---

## 2 — Prerequisites

- **AWS account** with Bedrock access in your chosen region (you may need to request access to specific third-party models in the Bedrock model catalog).
- **IAM user/role** with Bedrock permissions (see next section).
- **OpenCode** installed on your machine (or the `oh-my-opencode` overlay).

Install examples:

```bash
# Option A — curl installer
curl -fsSL https://opencode.ai/install | bash

# Option B — npm
npm install -g opencode-ai
```

---

## 3 — IAM & Permissions

Attach either a custom policy or `AmazonBedrockFullAccess` (prototyping only).

### Minimal IAM Policy (prototype — restrict more in prod)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel",
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
```

> [!IMPORTANT]
> If using a marketplace model that requires subscription, the account needs **AWS Marketplace subscribe permissions** for initial enablement (one-time per model).

---

## 4 — Configure Credentials

OpenCode supports multiple auth methods.

### Option A — AWS Profile / CLI (recommended for local dev)

```bash
aws configure --profile opencode-dev
# or set default
aws configure
```

Then run OpenCode with the profile:

```bash
AWS_PROFILE=opencode-dev opencode
```

### Option B — Environment Variables (quick start)

```bash
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1
# optionally:
# export AWS_BEARER_TOKEN_BEDROCK=...
opencode
```

---

## 5 — Install & Enable OpenCode + Bedrock Provider

Verify installation:

```bash
opencode --version
```

Start OpenCode or run a single command:

```bash
# Interactive TUI
opencode

# One-off job with a specific Bedrock model
opencode --model bedrock/<model-id> run "Refactor this function to be async"
```

> Model identifiers follow the `bedrock/<model-id>` format. Use `/models` inside the TUI to list available models.

---

## 6 — Pick & List Bedrock Models

### A. From OpenCode

Run OpenCode → type `/models` → browse and select.

### B. Directly with AWS SDK

**JavaScript (SDK v3):**

```javascript
import { BedrockClient, ListFoundationModelsCommand } from "@aws-sdk/client-bedrock";

const client = new BedrockClient({ region: "us-east-1" });
const resp = await client.send(new ListFoundationModelsCommand({}));
console.log(resp.modelSummaries);
```

**Python (boto3):**

```python
import boto3

client = boto3.client("bedrock", region_name="us-east-1")
print(client.list_foundation_models())
```

---

## 7 — Run a Prompt Through OpenCode Using Bedrock

1. Ensure env vars / profile are set (see section 4).
2. Pick your model id via `/models` or the SDK listing.
3. Run:

```bash
opencode --model bedrock/amazon.titan-text-v1 run "Generate unit tests for src/sort.js"
```

Or inside the TUI, use `/models` to select and then run prompts normally.

---

## 8 — Call Bedrock Directly from Code

### Node.js (SDK v3)

```javascript
import {
  BedrockRuntimeClient,
  InvokeModelCommand,
} from "@aws-sdk/client-bedrock-runtime";

const client = new BedrockRuntimeClient({ region: "us-east-1" });

const resp = await client.send(
  new InvokeModelCommand({
    modelId: "amazon.titan-text-v1",
    contentType: "application/json",
    accept: "application/json",
    body: JSON.stringify({
      inputText: "Write a short readme for this repo.",
    }),
  })
);

// parse resp.body (stream/Uint8Array) depending on SDK version
console.log(await streamToString(resp.body));
```

### Python (boto3)

```python
import boto3, json

client = boto3.client("bedrock", region_name="us-east-1")
resp = client.invoke_model(
    modelId="amazon.titan-text-v1",
    contentType="application/json",
    accept="application/json",
    body=json.dumps({"inputText": "Summarize the change in README.md"}),
)
print(resp["body"].read())
```

---

## 9 — CI with GitHub Actions

Store AWS credentials as repository secrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`).

```yaml
name: opencode-bedrock
on:
  issue_comment:
    types: [created]

jobs:
  opencode:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - name: Run OpenCode (opencode action)
        uses: anomalyco/opencode/github@latest
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: ${{ secrets.AWS_REGION }}
        with:
          model: bedrock/amazon.titan-text-v1
```

> [!TIP]
> For better security, use **OIDC + short-lived credentials** by configuring an IAM role for the Action runner to assume instead of long-lived keys.

---

## 10 — Official Samples & Repos

| Resource | Link |
|----------|------|
| AWS Bedrock code examples (Python/JS) | [AWS Code Library](https://docs.aws.amazon.com/code-library/latest/ug/bedrock_code_examples.html) |
| Sample repo: OpenCode + Bedrock | [aws-samples/sample-opencode-with-bedrock](https://github.com/aws-samples/sample-opencode-with-bedrock) |

---

## 11 — Costs, Security & Best Practices

| Area | Guidance |
|------|----------|
| **Costs** | Bedrock charges by model and tokens/requests — check [AWS Bedrock pricing](https://aws.amazon.com/bedrock/pricing/). Use Cost Explorer, set budgets/alerts. |
| **Security** | Prefer IAM roles (OIDC) in CI. Avoid long-lived keys in repos. Scope Bedrock permissions to only what you need. |
| **Quotas** | Some models require subscription/enabling through the Bedrock model catalog (one-time per model per account). |

---

## 12 — Troubleshooting

| Issue | Fix |
|-------|-----|
| **Model not found in OpenCode** | Confirm model is enabled in Bedrock console for your account and region. Run SDK `ListFoundationModels` to verify. |
| **Permissions errors** | Confirm IAM policy includes `bedrock:InvokeModel` and `bedrock:ListFoundationModels`. For marketplace subscription errors, someone with Marketplace rights must enable the model once. |
| **Credentials not picked up** | Try `AWS_PROFILE=... opencode` or set env vars explicitly in the same shell where you run `opencode`. |

---

## 13 — Quick Checklist

- [x] Request model access in AWS Bedrock console
- [x] Create IAM user/role with `bedrock:InvokeModel` + `bedrock:ListFoundationModels`
- [x] Install OpenCode (`curl` installer or `npm`)
- [x] Configure credentials: `aws configure` OR `export AWS_ACCESS_KEY_ID/...`
- [x] Run `opencode`, type `/models` and pick a Bedrock model
- [x] Test: `opencode --model bedrock/<model-id> run "Explain this file"`
- [x] Add CI: store AWS creds in GH secrets, add opencode workflow
