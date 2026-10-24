# Phase 4 log: DANSWER_* / ONYX_* names

## Finding that shaped the phase
Of the 19 distinct names, only 4 are real environment variables, and none is read by the deployed backend or set in any
compose, helm or local .env file (checked deployment/docker_compose/.env, web/.env*, backend/.env*, .vscode/.env*). The rest are
Python constant names. So there is no deployment impact and no fallback shim was added (a shim would keep the old name in code).

## A. Python constants (names only; every VALUE unchanged)
| Old | New | Value kept | Reason value is kept |
|---|---|---|---|
| `DANSWER_REDIS_FUNCTION_LOCK_PREFIX` | `OM_REDIS_FUNCTION_LOCK_PREFIX` | `"da_function_lock:"` | Redis key namespace (Phase 5) |
| `DANSWER_API_KEY_PREFIX` | `OM_API_KEY_USER_PREFIX` | `"API_KEY__"` | stored in user names (Phase 5) |
| `DANSWER_API_KEY_DUMMY_EMAIL_DOMAIN` | `OM_API_KEY_DUMMY_EMAIL_DOMAIN` | `"onyxapikey.ai"` | stored in user.email; live count 0 (Phase 5) |
| `DANSWER_TRACEMALLOC_FRAMES` | `OM_TRACEMALLOC_FRAMES` | `10` | n/a |
| `DANSWER_TOOL_NAME`, `DANSWER_TOOL_DESCRIPTION` | deleted | n/a | dead code: defined in `prompts/chat_tools.py`, referenced nowhere |

Touched: constants.py, auth/users.py, db/api_key.py, db/users.py, db/release_notes.py, 4 celery task modules, memory_tracer.py,
one external-dependency test.

## B. Real environment variables (4)
| Old | New | Where |
|---|---|---|
| `DANSWER_POSTGRES_DATA_DIR` | `OM_POSTGRES_DATA_DIR` | docker-compose.search-testing.yml, tests/regression/answer_quality/cli_utils.py |
| `DANSWER_OPENSEARCH_DATA_DIR` | `OM_OPENSEARCH_DATA_DIR` | docker-compose.search-testing.yml |
| `DANSWER_API_KEY` | `OM_API_KEY` (already the convention in tests/regression/search_quality and tests/agents_creator) | scripts/api_inference_sample.py, examples/assistants-api/topics_analyzer.py (also local variable and placeholder text) |
| `NEXT_PUBLIC_ONYX_BACKEND_URL` | `NEXT_PUBLIC_OM_BACKEND_URL` | web MCP OAuth callback route; not set anywhere, so the empty-string fallback applies before and after |

## C. Comment-only mentions
`ONYX_CELERY_BEAT_HEARTBEAT_KEY` in supervisord.conf -> `OM_CELERY_BEAT_HEARTBEAT_KEY` (the constant that already exists);
`ONYX_CLOUD_CELERY_TASK_PREFIX` comment in beat_schedule.py reworded to say the name must start with "cloud".

## D. Recorded, intentionally NOT renamed here
| Name | Reason | Phase |
|---|---|---|
| `ONYX_METADATA` | marker inside user-authored files and regexes | 5 |
| `ONYX_APP_LOADED`, `ONYX_DOMAIN` | browser extension / iframe message protocol and extension storage | 7 |
| `ONYX_GITHUB_*` (5 names) | CI secrets; must be renamed in repo settings together with the workflows | 7 |
| CloudFormation parameters `Onyx*` | AWS stack interface | 6 |
| `DANSWER_VESPA_DATA_DIR` | appears only as historical text in a TODO document about the Vespa to OpenSearch move | docs sweep |

## Verification
- After: `git grep` for `DANSWER_` and `ONYX_` outside docs shows only the section D names.
- tests/unit: 19 failed / 1556 passed, failure set identical to baseline. Python compiles. `tsc --noEmit` clean (excluding the
  pre-existing .next and dotenv noise).
- Compose: in a temp copy with an empty `.env_eval`, `docker-compose.search-testing.yml` resolves `OM_POSTGRES_DATA_DIR` and
  `OM_OPENSEARCH_DATA_DIR` when set, and falls back to the old default directories when unset.
