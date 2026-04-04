# T-0001 Search/Read/Repo tool wrappers for API clients

- Mode: tasks
- Task type: adapter
- PM complexity: moderate
- Planned effort: m

## Goal
Implement tool wrappers for existing API clients: SearchTool, ReadTool, RepoSearchTool, RepoTreeTool, RepoReadTool

## Acceptance Criteria
- SearchTool wraps SearchClient with query, count, domain params
- ReadTool wraps ReaderClient with url param returning markdown
- RepoSearchTool wraps RepoClient for GitHub code search
- RepoTreeTool wraps RepoClient for directory structure viewing
- RepoReadTool wraps RepoClient for file reading from repos
- All tools have input validation and error handling
- All tools return formatted output

## Constraints
- Keep provider-specific behavior isolated to the adapter boundary.
- Preserve deterministic workspace state and execution flow.

## Plan
- Inspect the existing adapter interface, config wiring, and invocation flow.
- Implement the adapter change close to the integration seam.
- Verify the adapter path with a focused test or representative run.

## PM Sizing
- Complexity: moderate
- Planned effort: m

## Template Guidance
- State the target adapter seam, external dependency, and expected contract up front.
- Call out config, invocation, and failure-path changes explicitly.
- Prefer verification that exercises the adapter boundary rather than unrelated paths.

## Intake Notes

### Adapter Surface
- Identify the entrypoint, inputs, outputs, and external system involved.

_TBD_

### Config and Execution Path
- Note which settings, command wiring, or failure handling must change.

_TBD_

### Verification Evidence
- Capture the focused run or test that proves the adapter path works.

_TBD_
