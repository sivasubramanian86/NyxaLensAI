# Phase 5 — AgentCore Memory & Observability: Design

## Status: PENDING

Key decisions (locked):
- Inspect boto3 service model at import time: if `bedrock-agentcore` unavailable, silently fall back to DynamoDB `NyxaSessionMemory` table — Phase 5 must never block the build
- EMF log format: `{"_aws": {"Timestamp": ..., "CloudWatchMetrics": [...]}, "subagent": ..., "duration_ms": ...}`
- X-Ray: use `aws_xray_sdk.core.xray_recorder.begin_subsegment(subagent_name)`
- AgentCore Memory key: `session_id = sha256(user_identifier + project_name)`
