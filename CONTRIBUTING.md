# Contributing

Repository access is invitation-only. Ask the owner for access before preparing
a contribution. Discuss larger changes in a private issue first.

## Before opening a pull request

1. Keep the change focused and update documentation when behavior changes.
2. Never include credentials, private repository contents, or customer scan data.
3. Run `make lint`, `make test`, and `make test-integration` for Python changes.
4. For frontend changes, run `cd frontend && npm test && npm run build`.
5. For infrastructure changes, run `cd cdk && cdk synth --app "python app.py"`.
6. Describe behavior, verification, and any AWS cost or security impact in the PR.

Submitting a contribution does not grant a license to the project or grant the
project owner rights to use the contribution. Agree on contribution terms with
the owner before submitting substantive code.
