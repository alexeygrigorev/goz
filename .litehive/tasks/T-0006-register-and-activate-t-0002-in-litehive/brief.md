# T-0006 Register and activate T-0002 in Litehive

- Mode: tasks
- Task type: process
- PM complexity: -
- Planned effort: -

## Goal
Create the missing Litehive task record for T-0002 and make it the active grooming task in this workspace.

## Acceptance Criteria
- `litehive status` shows `active_task_id: T-0002` or the workspace is otherwise explicitly routed to this task.
- A `.litehive/tasks/...` record exists for T-0002 with goal, acceptance criteria, PM sizing, and stage metadata.
- `litehive report --task-id T-0002 ...` succeeds from this workspace.

## Constraints
- Keep changes scoped to the task.

## Plan
- No plan defined.

## PM Sizing
- Complexity: Not estimated.
- Planned effort: Not sized.
