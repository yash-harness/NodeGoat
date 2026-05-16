---
name: create-pipeline-v1
description: >-
  Use when asked to create a Harness pipeline using v1/simplified syntax, when user mentions
  v1 pipeline format, new pipeline syntax, simplified pipelines, or explicitly requests v1
  over v0/standard format. Supports CI stages (run, run-test, background), CD stages
  (service/environment with action steps for K8s, Helm, ECS), approval (stage-level and inline),
  parallel execution, matrix/for/while strategies, caching, volumes, and template composition.
  Uses flat structure, ${{ }} expressions, and script field. Do NOT use for v0/standard pipelines
  (use create-pipeline). Trigger phrases: "v1 pipeline", "simplified pipeline", "new pipeline format",
  "create v1", "modern pipeline syntax", "global template pipeline".
metadata:
  author: Harness
  version: 4.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2) with the `pipeline_v1` resource type
---

# Create Pipeline v1

Generate Harness v1 simplified Pipeline YAML and optionally push to Harness via MCP.

## Instructions (Template-First Workflow)

The primary workflow is: **discover templates → match to requirements → fetch inputs → assemble pipeline**. Only fall back to `run:` steps for custom build/test/lint commands that have no template or action equivalent.

1. **Confirm v1 format** — User must specifically want v1 syntax. Default to v0 (`/create-pipeline`) if unclear.
2. **Clarify requirements** — Pipeline type (CI, CD, or both), language/framework, deployment target, approval needs.
3. **Discover available templates** — This is the critical step. Before writing ANY step YAML:
   - Run `harness_list(resource_type='template', params={"global": "true"})` to discover global (Harness-maintained) templates.
   - Use `search_term` to filter by domain (e.g., `"docker"`, `"kubernetes"`, `"terraform"`, `"security"`).
   - Also run `harness_list(resource_type='template', org_id='<org>')` to discover account/org-level templates the user may have.
   - Build a candidate list of templates that match the user's requirements.
4. **Fetch template inputs** — For each template you plan to use, call `harness_get` to read its full definition and input schema. Determine required vs. optional inputs. See the **Template Discovery & Usage** section below.
5. **Match requirements to templates** — Map each pipeline step to its best implementation:
   - **First choice**: `template: uses:` — a discovered template that matches the task
   - **Second choice**: `action: uses:` — a spec-defined action (see `references/native-actions.md`)
   - **Last resort**: `run:` — only for custom build/test/lint commands with no native equivalent
6. **Consult the spec reference** — Use `references/v1-spec-schema.md` for pipeline structure, expressions, strategies, and other v1 syntax details.
7. **Generate v1 YAML** — Assemble the pipeline from templates and actions. Use flat structure, `${{ }}` expressions, and `script` field for any `run:` steps.
8. **Create via MCP** — See the "Creating via MCP" section below (`resource_type: "pipeline_v1"`, NOT `"pipeline"`).

### Step Selection Priority

```
┌─────────────────────────────────────────────────────────┐
│ 1. template: uses: <discovered_template>                │  ← PREFERRED
│    (global or account template from harness_list)       │
├─────────────────────────────────────────────────────────┤
│ 2. action: uses: <spec_action>                          │  ← GOOD
│    (spec-defined actions: k8s, helm, terraform, etc.)   │
├─────────────────────────────────────────────────────────┤
│ 3. run: / run-test:                                     │  ← LAST RESORT
│    (only custom build/test/lint with no native equiv)   │
└─────────────────────────────────────────────────────────┘
```

### Never Use `run:` For

- Docker build/push → `template: uses: buildAndPushToDocker` / `buildAndPushToECR` / `buildAndPushToGAR`
- K8s deploy → `action: uses: kubernetes-rolling-deploy` or `template: uses: k8sRollingDeployStep`
- Helm deploy → `action: uses: helm-deploy` or `template: uses: helmDeployBasicStep`
- ECS deploy → `template: uses: ecsBluegreenDeployStep`
- Terraform → `template: uses: terraformStep`
- Security scanning → `template: uses: gitleaksStep` / `banditStep` / `sbomOrchestrationStep`
- Uploads → `template: uses: uploadArtifactsToS3` / `uploadArtifactsToGCS`
- Approvals → `approval: uses: harness` or `approval: uses: jira`
- Ticketing → `action: uses: jira-create` / `snow-create`
- HTTP requests → `action: uses: http` or `template: uses: httpStep`

## Common Rationalizations

Agents under pressure rationalize skipping the template-first workflow. These excuses are all invalid:

| Excuse | Reality |
|--------|---------|
| "Template discovery is slow" | 30 seconds now saves hours debugging invalid YAML. Always worth it. |
| "I already know the templates" | Templates change. New ones are added. You must verify with `harness_list`. |
| "This pipeline is too simple for templates" | Simple pipelines still use templates. Complexity is irrelevant. Always discover. |
| "No templates exist for this task" | You can't know until you call `harness_list`. Never assume. |
| "run: is more flexible" | Templates provide better error handling, UI integration, and rollback. Not worth flexibility trade. |
| "I'll discover templates later" | Later = after you've written invalid YAML. Discovery must come first. |
| "Custom build steps don't need templates" | Check spec-defined actions first. `run:` is last resort, not first instinct. |
| "I can invent a template identifier" | Invented identifiers = runtime failures. Only use identifiers returned by `harness_list`. |
| "I'll guess the template inputs" | Guessing = pipeline breaks at runtime. Always call `harness_get` to confirm inputs. |
| "User wants this done fast" | Fast wrong is slower than correct. Template discovery is the fast path. |

## Red Flags - STOP and Discover Templates

These thoughts mean you're about to violate template-first discipline:

- "I'll just use run: for this"
- "Templates probably don't exist for this"
- "No need to call harness_list/harness_get"
- "I can invent a template identifier"
- "Custom run: is simpler than templates"
- "This is too simple for template discovery"
- "I know which template to use"
- "Template discovery wastes time"
- "I'll guess the inputs"
- "User wants this done quickly"

**All of these mean: Go back to step 3 (Discover available templates).**

## v1 Key Differences from v0

| v0 Syntax | v1 Syntax |
|-----------|-----------|
| `<+variable>` expressions | `${{ variable }}` expressions |
| `type: CI` / `type: Deployment` stage types | Flat stages -- no `type` field |
| `command:` field in Run steps | `script:` field in `run:` steps |
| Native steps (`K8sRollingDeploy`, `HelmDeploy`) | Action steps (`action: uses: kubernetes-rolling-deploy`) |
| `failureStrategies:` | `on-failure:` |
| `HarnessApproval` step type | `approval: uses: harness` (stage-level or inline) |
| Deep nesting (`spec: execution: steps:`) | Flat structure (`steps:`) |
| `strategy: matrix:` under stage `spec` | `strategy: matrix:` directly on stage or step |

## Pipeline Structure

```yaml
pipeline:
  name: My Pipeline
  repo:                          # optional: repository config
    connector: account.github
    name: myorg/my-repo
  clone:                         # optional: clone config
    depth: 1
  on:                            # optional: event triggers
  - push:
      branches: [main]
  env:                           # optional: global env vars
    NODE_ENV: production
  inputs:                        # optional: pipeline inputs
    branch:
      type: string
      default: main
  stages:
  - name: build
    steps:
    - run:
        script: go build
```

No `version:`, `kind:`, or `spec:` wrapper -- `pipeline:` is the root key.

## Stages

Stages have no `type` field. Their purpose is determined by their keys.

### CI Stage

```yaml
- name: build
  runtime: cloud
  platform:
    os: linux
    arch: arm
  cache:
    path: node_modules
    key: npm.${{ branch }}
  steps:
  - run:
      script: npm ci
```

### Deployment Stage

```yaml
- name: deploy
  service: my-service
  environment: staging
  steps:
  - action:
      uses: kubernetes-rolling-deploy
      with:
        dry-run: false
```

### Approval (stage-level)

```yaml
- approval:
    uses: harness
    with:
      timeout: 30m
      message: "Approve deployment?"
      groups: [admins, ops]
      min-approvers: 1
```

## Step Types

### Run Step

Uses `script:` field (not `command:` or `run:`).

```yaml
# long syntax
- run:
    script: npm test

# short syntax
- run: npm test

# with container
- run:
    container: node:18
    script: npm test

# with shell and env
- run:
    shell: bash
    script: |
      npm ci
      npm test
    env:
      NODE_ENV: test

# with output variables
- id: build
  run:
    script: echo "TAG=v1" >> $HARNESS_OUTPUT
    output: [TAG]
```

### Run Test Step

```yaml
- run-test:
    container: maven
    script: mvn test
    report:
      type: junit
      path: target/surefire-reports/*.xml
    splitting:
      concurrency: 4
```

### Action Step

Actions replace v0 native steps. See `references/v1-spec-schema.md` for the full action catalog.

```yaml
# Kubernetes deploy
- action:
    uses: kubernetes-rolling-deploy
    with:
      dry-run: false

# Helm deploy
- action:
    uses: helm-deploy
    with:
      timeout: 10m

# Terraform plan
- action:
    uses: terraform-plan
    with:
      command: apply
      aws-provider: account.aws_connector

# HTTP request
- action:
    uses: http
    with:
      method: GET
      endpoint: https://acme.com
```

### Background Step

```yaml
- background:
    container: redis
- run:
    script: npm test
```

### Template Step

```yaml
- template:
    uses: account.docker
    with:
      push: true
      tags: latest
```

## AI Agent Steps

AI agents are templates. Reference them with `uses:` and pass custom inputs via `with:`:

```yaml
- template:
    uses: agent_uid@version
    with:
      custom_input: ${{ inputs.value }}
```

`llmConnector` and `mcpConnectors` are configured at agent level. Override if needed:

```yaml
- template:
    uses: code_review_agent@1.0.0
    with:
      llmConnector: custom_connector_id
      modelName: custom_model_arn
      repo_name: ${{ inputs.repo_name }}
```

### Approval Step (inline)

```yaml
- approval:
    uses: jira
    with:
      connector: account.jira
      project: PROJ
```

## Parallel and Group

```yaml
# parallel steps
- parallel:
    steps:
    - run:
        script: npm run lint
    - run:
        script: npm test

# parallel stages
- parallel:
    stages:
    - steps:
      - run: go test
    - steps:
      - run: npm test

# step group
- group:
    steps:
    - run:
        script: go build
    - run:
        script: go test
```

## Strategy

```yaml
# matrix (stage-level)
- strategy:
    matrix:
      node: [16, 18, 20]
      os: [linux, macos]
    max-parallel: 3
  steps:
  - run:
      container: node:${{ matrix.node }}
      script: npm test

# matrix (step-level)
- strategy:
    matrix:
      go: [1.19, 1.20, 1.21]
  run:
    container: golang:${{ matrix.go }}
    script: go test
```

## Failure Strategy

```yaml
# step-level
- run:
    script: go test
  on-failure:
    errors: all
    action: ignore       # abort, ignore, retry, fail, success

# retry with attempts
- run:
    script: go test
  on-failure:
    errors: [unknown]
    action:
      retry:
        attempts: 5
        interval: 10s
        failure-action: fail

# stage-level
- steps:
  - run:
      script: go test
  on-failure:
    errors: all
    action: abort
```

## Conditional Execution

```yaml
# stage conditional
- if: ${{ branch == "main" }}
  steps:
  - run:
      script: deploy.sh

# step conditional
- if: ${{ branch == "main" }}
  run:
    script: deploy.sh
```

## Template Discovery & Usage

This is the core of the template-first workflow. **Every pipeline starts here** — discover what already exists before writing anything.

### Discovery Strategy

Run these searches to build your template palette:

```
# 1. Global templates (Harness-maintained, always available)
harness_list(resource_type='template', params={"global": "true"})

# 2. Filtered global search by domain
harness_list(resource_type='template', params={"global": "true"}, search_term='docker')
harness_list(resource_type='template', params={"global": "true"}, search_term='kubernetes')

# 3. Account/org templates (user-created, may have org-specific logic)
harness_list(resource_type='template', org_id='<org>')
harness_list(resource_type='template', org_id='<org>', project_id='<project>')
```

| Parameter | Required | Description |
|---|---|---|
| `params` | for global | Pass `{"global": "true"}` to discover global (Harness-maintained) templates |
| `org_id` | for account/org | Required when discovering account or org-level templates |
| `search_term` | no | Keyword to filter (e.g., `"docker"`, `"helm"`, `"terraform"`, `"security"`) |
| `template_type` | no | Filter: `Pipeline`, `Stage`, `Step` |
| `size` | no | Number of results to return |

Each result contains:
- `identifier` — use this in the `uses:` field
- `name` — human-readable template name
- `templateEntityType` — `Pipeline`, `Stage`, or `Step`
- `versionLabel` — pass to `harness_get` in the next step

### Template Preference Order

When multiple templates could serve the same purpose:

1. **Account/org templates** — prefer these if they exist (they encode org-specific conventions, connectors, and policies)
2. **Global templates** — use Harness-maintained templates as the standard fallback
3. **Spec actions** — use `action: uses:` only when no template covers the task

### Fetching Template Inputs

For **every** template you plan to reference, fetch its input schema before writing YAML:

```
# Global template
harness_get(resource_type='template', template_id='<identifier>', version_label='<versionLabel>', params={"global": "true"})

# Account/org template
harness_get(resource_type='template', template_id='<identifier>', version_label='<versionLabel>', org_id='<org>')
```

Parse the response to determine:
- **Required inputs** (no default) — must be supplied in the `with:` block
- **Optional inputs** (have a `default`) — omit from `with:` to accept defaults
- **Default expressions** like `${{infra.namespace}}` — leave as-is; they resolve at runtime

Common default patterns:

| Input | Typical Default | Source |
|-------|-----------------|--------|
| `namespace` | `${{infra.namespace}}` | Infrastructure definition |
| `kubeconfig` | `${{infra.kube_config_path}}` | Infrastructure definition |
| `release` | `${{infra.releaseName}}` | Infrastructure definition |
| `manifests` | `${{runtime.manifestPath}}` | Runtime context |

### Referencing Templates in v1 YAML

```yaml
# Account/org template (scoped with account. or org. prefix)
- template:
    uses: account.my_docker_build
    with:
      repo: myorg/myapp
      tags: [${{ pipeline.sequenceId }}, latest]

# Global template (no prefix needed)
- template:
    uses: buildAndPushToDocker
    with:
      connector: dockerhub
      repo: myorg/myapp

# Pinned version (only when user explicitly requests)
- template:
    uses: account.my_docker_build@2.0.0
    with:
      repo: myorg/myapp
```

**Rules:**
- Write `uses: templateName`, not `uses: templateName@1.0.0` — only add `@version` when the user explicitly requests a pinned version
- Never invent a template identifier — it must be returned by `harness_list`
- Provide only required inputs in `with:` — omit optional inputs to accept their defaults
- Wire pipeline-level `inputs:` for values the user must supply at runtime

## Template-First Validation Checklist

Before finalizing the pipeline, verify you followed template-first discipline:

- [ ] `harness_list` was called to discover templates before writing steps
- [ ] Every `uses:` value was returned by `harness_list` (never invented)
- [ ] `harness_get` was called for every referenced template to confirm its inputs
- [ ] All required inputs (no defaults) are provided in the `with:` block
- [ ] Optional inputs with defaults are **omitted** from `with:`
- [ ] No `@version` suffix on `uses:` unless the user explicitly requested pinning
- [ ] Pipeline-level `inputs:` defined for all values the user must supply at runtime
- [ ] `run:` steps are used ONLY where no template or action exists for the task

## Complete CI Example (Template-First)

This example shows a pipeline composed primarily from discovered templates. The agent would have:
1. Run `harness_list` to discover `buildAndPushToDocker` and `gitleaksStep` templates
2. Run `harness_get` for each to confirm required inputs
3. Used `run:` only for the custom `npm ci` / `npm test` commands (no template equivalent)

```yaml
pipeline:
  name: My App CI
  identifier: my_app_ci
  tags:
    ai_generated: ""
  repo:
    connector: account.github
    name: myorg/my-app
  clone:
    depth: 1
  on:
  - push:
      branches: [main]
  - pull_request:
      branches: [main]
  stages:
  - name: build-and-test
    runtime: cloud
    platform:
      os: linux
      arch: arm
    cache:
      path: node_modules
      key: npm.${{ branch }}
    steps:
    - run:
        script: npm ci
    - parallel:
        steps:
        - run:
            script: npm run lint
        - run-test:
            script: npm test
            report:
              type: junit
              path: junit.xml
    - template:
        uses: gitleaksStep
    - template:
        uses: buildAndPushToDocker
        with:
          connector: dockerhub
          repo: myorg/my-app
          tags: [${{ pipeline.sequenceId }}, latest]
```

## Complete CD Example (Template-First)

This example shows a deployment pipeline where the agent:
1. Discovered `k8sRollingDeployStep` via `harness_list`
2. Fetched its inputs via `harness_get` — confirmed `skip_dry_run` is optional (default: false)
3. Used spec actions for manifest-download/bake (no template equivalent needed)

```yaml
pipeline:
  name: Petstore Deploy
  identifier: petstore_deploy
  tags:
    ai_generated: ""
  inputs:
    skip_dry_run:
      type: boolean
      default: false
  stages:
  - name: deploy-staging
    service: petstore
    environment: staging
    steps:
    - action:
        uses: manifest-download
    - action:
        uses: manifest-bake
    - template:
        uses: k8sRollingDeployStep
        with:
          skip_dry_run: ${{ inputs.skip_dry_run }}
  - approval:
      uses: harness
      with:
        timeout: 1d
        message: "Approve production deployment?"
        groups: [prod-approvers]
        min-approvers: 1
  - name: deploy-prod
    service: petstore
    environment: prod
    steps:
    - action:
        uses: manifest-download
    - action:
        uses: manifest-bake
    - template:
        uses: k8sRollingDeployStep
        with:
          skip_dry_run: false
```

## Complete Multi-Template Example

A pipeline that composes multiple templates for a full CI/CD flow:

```yaml
pipeline:
  name: Full Stack Deploy
  identifier: full_stack_deploy
  tags:
    ai_generated: ""
  inputs:
    environment:
      type: string
      enum: [staging, prod]
    docker_tag:
      type: string
      default: latest
  stages:
  - name: build
    runtime: cloud
    platform:
      os: linux
      arch: arm
    steps:
    - run:
        script: npm ci && npm run build
    - template:
        uses: gitleaksStep
    - template:
        uses: buildAndPushToDocker
        with:
          connector: account.dockerhub
          repo: myorg/fullstack-app
          tags: [${{ inputs.docker_tag }}, ${{ pipeline.sequenceId }}]
    - template:
        uses: uploadArtifactsToS3
        with:
          connector: account.aws
          bucket: myorg-artifacts
          source: dist/
          target: fullstack-app/${{ pipeline.sequenceId }}/
  - approval:
      uses: harness
      with:
        timeout: 1h
        message: "Deploy ${{ inputs.docker_tag }} to ${{ inputs.environment }}?"
        groups: [devops]
        min-approvers: 1
  - name: deploy
    service: fullstack-app
    environment: ${{ inputs.environment }}
    steps:
    - action:
        uses: manifest-download
    - action:
        uses: manifest-bake
    - template:
        uses: k8sRollingDeployStep
        with:
          skip_dry_run: false
```

## Creating via MCP

**CRITICAL: Use `resource_type: "pipeline_v1"` — NOT `"pipeline"`.** The `"pipeline"` resource type is the v0 legacy endpoint; it may tolerate v1 YAML on some Harness versions but is not the native v1 path and may fail on future versions.

### Step 1 — Verify the project exists

List projects with `harness_list` (`resource_type: "project"`, `org_id`) to confirm. If the project does not exist, create it first with `harness_create` (`resource_type: "project"`, `body: { identifier, name }`) or ask the user.

### Step 2 — Create the pipeline

Call `harness_create` with:

```
resource_type: "pipeline_v1"
org_id:        "<organization>"
project_id:    "<project>"
body: {
  pipeline_yaml: "<full v1 pipeline YAML string, including 'pipeline:' root key>",
  identifier:    "<unique pipeline identifier>",
  name:          "<pipeline display name>"
}
```

Notes on the body:

- **`pipeline_yaml`** is the required field name (snake_case). Do not use `yamlPipeline` — that's the v0 legacy field.
- **`identifier`** and **`name`** must also be passed as top-level body fields (the MCP uses these for URL routing; they must match the values inside the YAML).
- The `version` field defaults to `"1"` — do not set it explicitly unless the user requests a different version.
- Alternative body shapes accepted by the MCP for `pipeline_v1`:
  - Raw YAML string as body — `identifier` and `name` are extracted from the YAML.
  - `{ pipeline: { ... } }` JSON object — serialized to YAML automatically.
  - `{ yamlPipeline: "..." }` — accepted as backwards-compat alias of `pipeline_yaml`.

Prefer the explicit `{ pipeline_yaml, identifier, name }` shape above for clarity and version safety.

### Step 3 — Report the result

On success, report the pipeline URL. The MCP response contains the pipeline identifier and a UI path — surface both.

## Examples

### Create a v1 CI pipeline

```
/create-pipeline-v1
Create a v1 CI pipeline for a Node.js app with caching, parallel lint and test, and Docker push
```

Agent workflow:
1. `harness_list(resource_type='template', params={"global": "true"}, search_term='docker')` → finds `buildAndPushToDocker`
2. `harness_get(resource_type='template', template_id='buildAndPushToDocker', params={"global": "true"}, ...)` → confirms inputs: connector, repo, tags
3. Generates pipeline using template for Docker push, `run:` only for npm commands

### Create a v1 deployment pipeline

```
/create-pipeline-v1
Create a v1 Kubernetes deployment pipeline with staging approval and production stages
```

Agent workflow:
1. `harness_list(resource_type='template', params={"global": "true"}, search_term='kubernetes')` → finds `k8sRollingDeployStep`
2. `harness_list(resource_type='template', org_id='default')` → checks for org-specific deploy templates
3. Prefers org template if found, otherwise uses global template (`k8sRollingDeployStep`)

### Create a v1 matrix build

```
/create-pipeline-v1
Create a v1 pipeline that tests across Go 1.19, 1.20, and 1.21 using matrix strategy
```

Agent workflow:
1. `harness_list(resource_type='template', params={"global": "true"}, search_term='go')` → checks for Go build templates
2. No matching template → uses `run:` with matrix strategy (custom test command, no template equivalent)

## Performance Notes

- **Template discovery is mandatory** — always run `harness_list` before writing steps. A template may exist that you don't know about.
- **Never skip `harness_get`** — always fetch and confirm template inputs before referencing one. Guessing inputs leads to runtime failures.
- Always check `references/native-actions.md` before falling back to a `run:` step. Native actions provide better error handling, rollback support, and UI integration.
- Always consult `references/v1-spec-schema.md` for the complete v1 spec before generating YAML.
- Use `script:` field in run steps, never `command:` or `run:` as the field name.
- Use `action: uses:` or `template: uses:` for deployments, never v0 native step types like `K8sRollingDeploy`.
- Do not mix v0 and v1 syntax. No `<+...>` expressions, no `type:` on stages, no `spec:` wrapper.
- Validate all expressions use `${{ }}` syntax before presenting.

## Troubleshooting

### Common v1 Syntax Errors

- Using `<+...>` instead of `${{ ... }}` expressions
- Adding `type:` field on stages (v1 stages have no type)
- Using `command:` or `run:` as the field name instead of `script:`
- Wrapping pipeline in `version:`, `kind:`, `spec:` (v1 uses bare `pipeline:`)
- Using v0 step types (`K8sRollingDeploy`) instead of actions (`action: uses: kubernetes-rolling-deploy`)
- Using `failureStrategies:` instead of `on-failure:`

### MCP Errors

- **Using `resource_type: "pipeline"` for a v1 pipeline** — that's the v0 legacy endpoint. Use `resource_type: "pipeline_v1"` so you hit the native v1 API. The v0 endpoint may tolerate v1 YAML on some versions but is fragile and will silently produce unexpected behavior.
- **Project not found** — Verify the project exists with `harness_list` (`resource_type: "project"`, `org_id`). Create it first or confirm `org_id`/`project_id` are correct.
- **Missing required fields for pipeline_v1** — Pass the body as `{ pipeline_yaml: "<YAML string>", identifier: "<id>", name: "<name>" }`. All three fields are required.
- **`DUPLICATE_IDENTIFIER`** — Pipeline exists; use `harness_update` with the same `resource_type: "pipeline_v1"`.
- **`INVALID_REQUEST`** — Check YAML structure matches v1 schema. Consult `references/v1-spec-schema.md`.
