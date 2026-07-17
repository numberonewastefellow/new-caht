# Fork setup — GitHub Actions variables & secrets

The 26 workflows in `.github/workflows/` were inherited from upstream Onyx and originally
targeted Onyx's own infrastructure (their Docker Hub org, self-hosted RunsOn AWS runners,
their Linear, their team). The Onyx couplings have been neutralized:

- Self-hosted RunsOn runners → `ubuntu-latest`; `runs-on.yml` (which `_extend`ed a private
  Onyx repo) deleted.
- `onyxdotapp/onyx-*` image names → `${{ vars.IMAGE_REGISTRY }}/om-*` (see below).
- `CODEOWNERS` Onyx owners commented out; the Linear-link PR gate disabled (`if: false`).
- Onyx public Helm charts (`onyx-dot-app.github.io/...`) kept — functional public deps.

To actually **run** these workflows on your fork you must set the following. Until you do,
the affected workflows will fail or no-op on missing values — that's expected, not a
regression. Set repository **Variables** and **Secrets** under
`Settings → Secrets and variables → Actions`.

> Image tags and model repo ids must NOT be renamed casually — see [`../DO_NOT_RENAME.md`](../DO_NOT_RENAME.md).

---

## Required repository VARIABLE

| Variable | Used by | Set to |
|---|---|---|
| `IMAGE_REGISTRY` | `deployment.yml`, `docker-tag-latest.yml`, `docker-tag-beta.yml`, `sandbox-deployment.yml`, `pr-integration-tests.yml`, `pr-playwright-tests.yml`, `pr-python-model-tests.yml`, `pr-helm-chart-testing.yml` | your container-registry namespace, e.g. `myorg` or `ghcr.io/myorg`. Images publish as `${IMAGE_REGISTRY}/om-backend`, `om-web-server`, `om-model-server`, `om-sandbox`. |

Other `vars.*` referenced by connector tests (optional — only if you run those suites):
`AWS_REGION_NAME`, `AZURE_API_URL`, `VERTEX_LOCATION`, `CONFLUENCE_TEST_SPACE`,
`CONFLUENCE_TEST_SPACE_URL`, `CONFLUENCE_USER_NAME`, `AIRTABLE_TEST_BASE_ID`,
`AIRTABLE_TEST_TABLE_ID`, `AIRTABLE_TEST_TABLE_NAME`, `SF_USERNAME`, `SHAREPOINT_SITE`,
`SHAREPOINT_CLIENT_ID`, `SHAREPOINT_CLIENT_DIRECTORY_ID`, `IMAP_HOST`, `IMAP_USERNAME`,
`IMAP_MAILBOXES`, `BITBUCKET_EMAIL`, `MCP_OAUTH_USERNAME`, `R2_ACCOUNT_ID_DAILY_CONNECTOR_TESTS`,
`NEXT_PUBLIC_RECAPTCHA_SITE_KEY`, `DISABLE_MYPY_CACHE`, `DOCKER_DEBUG`, `DOCKER_NO_CACHE`,
`MODEL_SERVER_NO_CACHE`.

---

## Secrets by purpose

### Image publish / deploy (needed for `deployment.yml`, `docker-tag-*.yml`, `sandbox-deployment.yml`)
`DOCKER_USERNAME`, `DOCKER_TOKEN` (registry login), `AWS_OIDC_ROLE_ARN`, `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `DEPLOY_KEY`, `ACCESS_TOKEN_GITHUB`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`,
`VERCEL_PROJECT_ID`, `MONITOR_DEPLOYMENTS_WEBHOOK`, `SENTRY_DSN`, `POSTHOG_KEY`, `POSTHOG_HOST`.

### LLM / inference (integration & model tests)
`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `AZURE_API_KEY`, `COHERE_API_KEY`, `LITELLM_API_KEY`,
`LITELLM_API_URL`, `VERTEX_CREDENTIALS`, `EXA_API_KEY`, `FIRECRAWL_API_KEY`,
`GOOGLE_PSE_API_KEY`, `GOOGLE_PSE_SEARCH_ENGINE_ID`.

### Connector daily/integration tests (only if you run `pr-python-connector-tests.yml` / external-dep tests)
Confluence: `CONFLUENCE_ACCESS_TOKEN`, `CONFLUENCE_ACCESS_TOKEN_SCOPED`, `CONFLUENCE_TEST_PAGE_ID`.
Jira: `JIRA_API_TOKEN`, `JIRA_API_TOKEN_SCOPED`, `JIRA_ADMIN_API_TOKEN`, `JIRA_USER_EMAIL`, `JIRA_BASE_URL`.
Google: `GOOGLE_DRIVE_OAUTH_CREDENTIALS_JSON_STR`, `GOOGLE_DRIVE_OAUTH_CREDENTIALS_JSON_STR_TEST_USER_1`,
`GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON_STR`, `GOOGLE_GMAIL_OAUTH_CREDENTIALS_JSON_STR`, `GOOGLE_GMAIL_SERVICE_ACCOUNT_JSON_STR`.
GitHub perm-sync: `ONYX_GITHUB_ADMIN_EMAIL`, `ONYX_GITHUB_PERMISSION_SYNC_TEST_ACCESS_TOKEN`,
`ONYX_GITHUB_PERMISSION_SYNC_TEST_ACCESS_TOKEN_CLASSIC`, `ONYX_GITHUB_TEST_USER_1_EMAIL`, `ONYX_GITHUB_TEST_USER_2_EMAIL`.
SharePoint/Teams: `PERM_SYNC_SHAREPOINT_CLIENT_ID`, `PERM_SYNC_SHAREPOINT_DIRECTORY_ID`,
`PERM_SYNC_SHAREPOINT_PRIVATE_KEY`, `PERM_SYNC_SHAREPOINT_CERTIFICATE_PASSWORD`,
`SHAREPOINT_CLIENT_SECRET`, `TEAMS_APPLICATION_ID`, `TEAMS_DIRECTORY_ID`, `TEAMS_SECRET`.
Salesforce: `SF_PASSWORD`, `SF_SECURITY_TOKEN`. Zendesk: `ZENDESK_EMAIL`, `ZENDESK_TOKEN`, `ZENDESK_SUBDOMAIN`.
Others: `SLACK_BOT_TOKEN`, `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_WEBHOOK`,
`DISCORD_CONNECTOR_BOT_TOKEN`, `NOTION_INTEGRATION_TOKEN`, `HUBSPOT_ACCESS_TOKEN`,
`GITLAB_ACCESS_TOKEN`, `BITBUCKET_API_TOKEN`, `BITBUCKET_WORKSPACE`, `BITBUCKET_PROJECTS`,
`BITBUCKET_REPOSITORIES`, `GONG_ACCESS_KEY`, `GONG_ACCESS_KEY_SECRET`, `GITBOOK_API_KEY`,
`GITBOOK_SPACE_ID`, `HIGHSPOT_KEY`, `HIGHSPOT_SECRET`, `AIRTABLE_ACCESS_TOKEN`, `FIREFLIES_API_KEY`,
`SLAB_BOT_TOKEN`, `IMAP_PASSWORD`, `MCP_OAUTH_CLIENT_ID`, `MCP_OAUTH_CLIENT_SECRET`,
`MCP_OAUTH_ISSUER`, `MCP_OAUTH_JWKS_URI`, `MCP_OAUTH_PASSWORD`, `REDIS_CLOUD_PYTEST_PASSWORD`,
`AWS_ACCESS_KEY_ID_DAILY_CONNECTOR_TESTS`, `AWS_SECRET_ACCESS_KEY_DAILY_CONNECTOR_TESTS`,
`GCS_ACCESS_KEY_ID_DAILY_CONNECTOR_TESTS`, `GCS_SECRET_ACCESS_KEY_DAILY_CONNECTOR_TESTS`,
`R2_ACCESS_KEY_ID_DAILY_CONNECTOR_TESTS`, `R2_SECRET_ACCESS_KEY_DAILY_CONNECTOR_TESTS`,
`S3_AWS_ACCESS_KEY_ID`, `S3_AWS_SECRET_ACCESS_KEY`.

> The `ONYX_GITHUB_*` names above are **secret names** (arbitrary labels in workflow YAML), not
> Onyx infrastructure — rename them freely if you like, just keep the workflow reference in sync.

---

## Workflows that need nothing to pass
`pr-python-tests.yml` (unit), `pr-jest-tests.yml`, `pr-quality-checks.yml`, `zizmor.yml`,
`pr-labeler.yml`, `merge-group.yml`, `nightly-close-stale-issues.yml` run on `ubuntu-latest`
with only the built-in `GITHUB_TOKEN`. `pr-linear-check.yml` is disabled (`if: false`).
