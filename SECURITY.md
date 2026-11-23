# Security Policy

## Reporting a vulnerability

Do not report security vulnerabilities in public issues or discussions. Use
GitHub's **Report a vulnerability** action under the repository's Security tab
to send a private advisory to the maintainers. Include affected versions,
reproduction steps, impact, and any suggested fix. Avoid attaching credentials,
private repository contents, or real customer scan data.

If private vulnerability reporting is unavailable, contact the repository owner
through a private channel already provided to you. Do not publish exploit details
while a report is being reviewed.

## Supported versions

Only the current default branch is supported. This project is under active
development and has not been deployed as a production service.

## Security boundaries

Never commit AWS credentials, GitHub tokens, `.env` files, private source code,
or customer scan data. Treat scan dossiers and model output as untrusted input.
The current CDK AOSS network policy permits public network reachability; review
and restrict it before any production deployment.
