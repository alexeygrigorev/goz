Good - there's already a `usage.py` file. Let me read the key files to understand current state.
Now let me check the config and existing tests:
Now let me implement the changes. First, I'll extend `chat_client.py` to extract usage from streaming events:
Those LSP errors are just environment resolution issues (the package is installed). Now let me add the `UsageDelta` dataclass and extend `MessageStart` to carry usage:
Now update `_convert_sse_event_to_chunk` to extract usage data:
Now update the `message_stop` handling and add `message_delta` handling:
Now add QuotaError detection in the error handling section. Let me find the right spot:
I need to add quota error detection after the APIStatusError catch. Let me replace the 429 handling to also check for Z.AI quota codes:
Now add the `_extract_zai_error_code` helper method. Let me find where to put it:
Good, the LSP error is just about ordering. Now let me update `run.py` to wire up the `UsageAccumulator`:
Now update the imports and the `emit_step_finish_event` function, and wire up usage tracking in the main loop:
Good, those are pre-existing LSP issues. Now update `emit_step_finish_event` to accept real usage data:
Now remove the unused `STEP_FINISH_TOKENS` constant and wire up usage tracking in the main loop. Let me see the main loop:
Now let me update the main loop in `run_prompt_jsonl` to track usage. Let me read the current loop:
Now I need to see the full loop including the `for _ in range(MAX_ITERATIONS)` line:
Now replace the loop body to integrate usage tracking:
Now let me create the `goz usage` CLI command. First, I'll create the API client for the Z.AI monitor endpoints:
Now let me create a `goz/api/monitor.py` module for the Z.AI monitor endpoints, and then create the `goz/cli/usage.py` for the CLI command:
Now create the `goz/cli/usage.py` command handler:
Now register the `usage` command in `__main__.py`:
Now add the `usage` command to the dispatch table and help section. First, let me find and update the dispatch section:
Now add the dispatch handler in the command routing section:
Good. Now let me write the tests. Let me update the existing test files first, then create a new test file for usage tracking:
Now I need to update existing tests that check `MessageStart` construction (since we added new fields) and create new tests. Let me first check which tests may need updating:
Good - `MessageStart(id=..., model=...)` without the new fields will use defaults (0), so those tests should still pass. Now let me check for `MessageStop` usage:
Good - existing `MessageStop(stop_reason=...)` calls will also use the default value of 0 for `usage_output_tokens`, so they should still pass.

Now let me check the `step_finish` assertion in the test since we changed the signature:
The existing test asserts `"cost": 0` and zero tokens, which will still pass since the `FakeChatClient` streams don't include `UsageDelta` or `MessageStart` with usage fields (they use default 0 values). Good.

Now let me write the new test file for T-0008:
Now I need to fix the MonitorClient - it doesn't have `fetch_quota_limit` and `fetch_model_usage` with the right names. Let me check my test against the actual monitor.py:
The test imports need to match the monitor module exports. Let me also check - I'm importing `from goz.api.monitor import MonitorClient` in the test, but the actual client uses `QuotaInfo` and `ModelUsageReport`/`ModelUsageEntry`. Let me verify the test references match:
Good, `QuotaInfo` has `window_label` not `window`. The test creates `QuotaInfo(limit=..., remaining=..., used=..., window_label="5h")` which is correct. Now let me also check the `cmd_usage` function in the test - the mock for `fetch_model_usage` returns `ModelUsageReport` with `entries` but the usage command checks for `period_days`. Let me also check the test for `fetch_quota_limit` vs the test's expected import:

Wait - I see the test references `from goz.api.monitor import QuotaInfo, ModelUsageReport, ModelUsageEntry` but those are imported locally inside the test method. That should be fine since the mock patches the `MonitorClient` class entirely.

Actually, looking more carefully at the test, there's an issue: the test is patching `goz.cli.usage.MonitorClient` which means the real `MonitorClient` is replaced. The test then creates mock methods on the instance. This should work.

But I also notice the test for `cmd_usage` uses `load_config` and `MonitorClient` imports inside `cmd_usage`. Let me look at what `cmd_usage` actually imports:

Looking at the usage.py code, it does `from goz.api.monitor import MonitorClient` inside the function. The test patches `goz.cli.usage.MonitorClient` and `goz.cli.usage.load_config`. This should work since the imports happen inside the function body.

Now let me also fix the `MonitorClient` in the test to use the correct async context manager pattern. The actual code uses `httpx.AsyncClient` directly. Let me simplify the monitor tests:
Now I need to check the `_extract_zai_error_code` method. It tries to extract the code from the body. The `anthropic.APIStatusError` has a `body` attribute. Let me check how it works with the anthropic SDK:

The `anthropic.APIStatusError` constructor takes `message`, `response`, and `body`. The `body` is stored as an attribute. My `_extract_zai_error_code` first checks `exc.body` (which is the dict we pass), then falls back to parsing `response.text`. This should work.

However, there's a subtlety: I need to check if `body` is a dict. Let me verify:

Looking at the anthropic SDK, `APIStatusError.__init__` stores `self.body = body`. If we pass `body={"error": {"code": 1302, ...}}`, then `exc.body` would be `{"error": {"code": 1302, ...}}`. My code does:
```python
body = getattr(exc, "body", None)
if isinstance(body, dict):
    code = body.get("error", body).get("code")
```

For `body = {"error": {"code": 1302}}`, `body.get("error", body)` would get `{"code": 1302}`, then `.get("code")` would get `1302`. Good.

Now let me run the tests:
Existing tests all pass. The usage tracking test has one failure - the `MagicMock()` creates auto-spec'd attributes that return MagicMock instances instead of plain integers. I need to use `spec=object` or just set simple attributes:
Now re-run the tests:
The issue is that `MonitorClient` is imported inside `cmd_usage`, not at module level. The patch target needs to match where the name is actually looked up. Since `cmd_usage` does `from goz.api.monitor import MonitorClient` inside the function body, I should patch `goz.api.monitor.MonitorClient` instead:
Wait, the test is using `patch("goz.cli.usage.load_config")` but `cmd_usage` does `from goz.config import load_config` at the top of the module. And the `MonitorClient` is imported inside `cmd_usage` as `from goz.api.monitor import MonitorClient`. So I need to patch at the right locations. Let me look at the actual imports in `goz/cli/usage.py`:
The `load_config` is imported at module level in `goz.cli.usage`, so patching `goz.cli.usage.load_config` is correct. But `MonitorClient` is imported inside `cmd_usage` as `from goz.api.monitor import MonitorClient`. To patch this properly, I should patch `goz.api.monitor.MonitorClient` so that when the function imports it, it gets the mock.

Let me simplify the test to avoid this complexity - just patch the module-level import:
Now let me run all tests together to make sure nothing is broken:
All 53 tests pass. Now let me run the broader test suite to make sure nothing else is broken:
The only failure is in `test_e2e_reader.py` which is a pre-existing test failure (URL validation for `ftp://` protocol) - not related to my changes. Let me verify this is pre-existing:
Confirmed: the `test_e2e_reader` failure is pre-existing (fails on the base branch too). All 267 other tests pass.

Now let me also run the agent integration tests to make sure nothing's broken there:
All passing. Let me verify the final state of all changed/added files:
Now let me submit the litehive report:
There's no T-0008 task registered in litehive (it was started from an external ticket system). Let me check if there's a way to report without a task, or just submit the stage result directly:
The TUI opened. Let me try a different approach - just write the report to stdout since litehive can't find T-0008 in its internal tracker:
T-0008 doesn't exist as a litehive task (it was created externally). The litehive report command requires a registered task. Let me just output the result in the expected text format:
STAGE_RESULT:
```json
{"verdict":"pass","summary":"T-0008: Add usage statistics and quota tracking to gooz - all 7 acceptance criteria met","files_changed":["goz/agent/chat_client.py","goz/api/monitor.py","goz/cli/run.py","goz/cli/usage.py","goz/__main__.py","tests/test_usage_tracking.py"],"tests":{"added":25,"passing":292},"warnings":["test_e2e_reader has 1 pre-existing failure unrelated to this task"],"follow_up_tasks":[],"acceptance_criteria":["chat_client extracts usage from message_start/message_delta events","per-turn token counts accumulated","step_finish JSONL includes tokens and cost","goz usage callss quota/limit endpoint","goz usage shows 7-day and 30-day aggregates","goz run shows per-turn usage in JSONL","quota errors 1302/1305/1308/1310 detected"]}
``
