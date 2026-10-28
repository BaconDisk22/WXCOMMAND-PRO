# WXCOMMAND-PRO AutoPilot

AutoPilot runs tests, dependency audits and build checks on pushes and pull requests, and once a week on Mondays. It also prepares standalone macOS Intel app ZIP and drag-and-drop DMG artifacts and a Raspberry Pi source archive. These are **CI artifacts**, not verified production installers.

## Workflow and automation
- `.github/workflows/autopilot.yml`: Python 3.11–3.13 tests, smoke checks, pip-audit, macOS Intel bundle check, Raspberry Pi source archive, aggregate release gate.
- `.github/dependabot.yml`: weekly dependency update pull requests.
- `.github/workflows/validation.yml`: additional test matrix.
- Each job uploads results and logs to the repository's Actions page. Failing checks block the aggregate release gate.

## Important boundaries
- A green CI run **does not** certify real radio connectivity, NWS/IPAWS end-to-end delivery, Pi startup, macOS Tahoe compatibility, or failover without duplicate transmissions.
- AutoPilot does **not** automatically write arbitrary new features or fix failed tests. That requires a separately installed, explicitly authorized coding agent with its own workflow.
- AutoPilot does **not** automatically merge. The separate `Publish successful builds` workflow publishes prereleases only from successful main-branch push runs, after revalidating their provenance. Before enabling auto-merge, configure branch protection on `main` requiring the AutoPilot release gate and review of safety-critical changes. Do not bypass hardware verification for release tags.
- The macOS `.app` bundles Python and dependencies. CI validates Intel native libraries and runs offline HTTP/template/dependency checks from both archives with the checkout hidden and no Python on PATH. The bundle is ad-hoc signed, not Developer ID signed or notarized. The Pi artifact remains a source archive.
- Never run synthetic emergency broadcasts on public channels.

## Initial activation
1. Merge the AutoPilot configuration after reviewing it. GitHub scheduled workflows run from the default branch, not an unmerged feature branch.
2. Ensure repository Actions is enabled and hosted macOS Intel runners are available for your plan.
3. Verify the first run and address failures; do not interpret the existence of a workflow file as a successful execution.
4. Configure `main` branch protection with required checks, and set release approval gates after hardware acceptance tests.
5. For hands-off code generation and fixing, configure a separate coding agent that can open pull requests and observe CI; do not grant it the ability to bypass release gates.

## Remaining stage 1 acceptance
- Verify security and endpoint authorization in deployment conditions.
- Validate NWS/IPAWS duplicate, expiry, update and cancellation behavior.
- Run Meshtastic USB/BLE/TCP and MeshCore hardware tests.
- Verify radio failover with a receiving node and no duplicate sends.
- Restore a SQLite backup offline on Pi and Mac and compare data.
