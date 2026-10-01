# Security policy

## Supported version

The latest released version receives security fixes.

## Reporting

Report suspected vulnerabilities privately to the repository owner before public disclosure. Do not include exported shortlists or personal data in a report.

## Deployment note

The app has no authentication layer and is meant to run on your own computer (`127.0.0.1`). A shared or public deployment needs access control, TLS, logging and retention policy, dependency updates, and a decision about who may see shortlists and notes. The only outbound connections go to `data.brreg.no`, on request; TLS certificates are verified against the operating system's trust store and verification is never disabled.
