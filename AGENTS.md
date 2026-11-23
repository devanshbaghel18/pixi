# Agy Team — Multi-Agent Engineering Rules & Protocol

This project is developed by a 4-agent persistent AI engineering team managed by **Agy Team**.
Every agent operating in this repository must strictly adhere to these rules.

---

## 1. Team Roster & Roles

| Pane | Agent Name | Role | Working Tree | Git Branch | Access Mode |
|---|---|---|---|---|---|
| **T1** | `main` | Lead Orchestrator & Integrator | `.` | `main` | Read/Write (Integration & Coordination) |
| **T2** | `backend` | APIs, Business Logic, Auth & Server Tests | `.worktrees/backend` | `agent/backend` | Read/Write |
| **T3** | `frontend` | UI/UX, Components, Layouts & State | `.worktrees/frontend` | `agent/frontend` | Read/Write |
| **T4** | `database` | Schema, Migrations, Optimization & Integrity | `.worktrees/database` | `agent/database` | Read/Write |

---

## 2. Core Operational Rules

1. **Inspect Before Action**: Always inspect the existing code, architecture, and tests before making modifications or proposing interfaces.
2. **Strict Worktree Isolation**:
   - Each worker must operate exclusively inside its designated working directory (`.worktrees/<role>/`).
   - Never write to or modify another worker's directory or Git branch directly.
   - Only `main` modifies files in the repository root or integrates approved branches into `main`.
3. **Never Invent Interfaces**:
   - Backend and Frontend must coordinate API contracts before implementation.
   - Database schemas must be stabilized before Backend builds schema-dependent endpoints.
4. **No Destructive Operations Without Permission**:
   - Never use `git push --force` or discard unstaged user work.
   - Production configuration, secret credentials, and critical deployment files must not be tampered with.
5. **No Secret Exposure**:
   - Never log, message, or commit API keys, tokens, passwords, or personal credentials.
6. **Rigorous Verification**:
   - Never claim tests passed without actually running them and inspecting the exit code and output.
   - All completed tasks must reference exact files modified, commit hashes, and test results.
7. **Main Verifies Independently**:
   - `main` must inspect the actual Git diff (`agy-team diff <worker>`) and receive review approval from `reviewer` before integrating any branch.

---

## 3. Communication & Task Coordination Protocol

All agent coordination is driven by the local `agy-team` CLI:

- **Check Inbox**:
  `agy-team check-inbox`
- **Claim & Start Task**:
  `agy-team task start <TASK_ID>`
- **Report Blocker**:
  `agy-team task block <TASK_ID> --reason "<description of blocker>"`
- **Send Inter-Agent Message**:
  `agy-team message <sender> <recipient> "<message>" [--task-id <id>]`
- **Complete Task**:
  `agy-team task complete <TASK_ID> --summary "<summary>" --tests "<PASSED/test details>"`
- **Inspect Status**:
  `agy-team status`

---

## 4. Git Integration Workflow

```
[Main] Creates & Assigns Task (e.g. TASK-001 -> backend)
  │
  ▼
[Worker] Receives task in inbox, claims lock: agy-team task start TASK-001
  │
  ▼
[Worker] Implements code in .worktrees/<role>, runs local tests, commits to agent/<role>
  │
  ▼
[Worker] Submits report: agy-team task complete TASK-001 --summary "..." --tests "..."
  │
  ▼
[Main] Inspects diff: agy-team diff backend
  │
  ▼
[Reviewer] Inspects diff, audits security/quality: agy-team message reviewer main "Approved"
  │
  ▼
[QA] Runs integration tests or validates behavior: agy-team message testing main "Verified"
  │
  ▼
[Main] Integrates into main: agy-team integrate backend --task TASK-001
```

Workers NEVER merge directly into main. Integration is the exclusive privilege and responsibility of Main.
