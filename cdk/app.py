#!/usr/bin/env python3
"""NyxaLensAI CDK App entrypoint."""
import aws_cdk as cdk
from stacks.nyxalens_stack import NyxaLensStack

app = cdk.App()
NyxaLensStack(app, "NyxaLensAI",
    env=cdk.Environment(region="us-east-1"),
    description="NyxaLensAI — Repo Architectural Amplifier (Bedrock + Step Functions + OpenSearch Serverless)",
)
app.synth()
