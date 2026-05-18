---
name: debug-failing-test
description: |
  Reproduces a failing test or error, isolates the root cause by inspecting the failing assertion + the production code path it exercises, then proposes a minimal fix (does NOT apply it without explicit user confirmation). Reads the test, traces the call chain, considers off-by-one edges, flaky-test patterns (timing, ordering, shared state), and recent changes that might have introduced the regression. Use when the user says "this test is red", "the suite is failing", "why does X fail", "this is broken", "the build is breaking", "tests are flaky", "the assertion fails", "got an error in test_y", or pastes a stack trace. NOT for writing new tests — use the test-writer agent instead. NOT for blind-fixing tests by editing assertions to match observed (wrong) output; this skill diagnoses, then proposes a real fix.
---

# debug-failing-test

Reproduce a failing test, diagnose, propose a minimal fix.

## Workflow

1. Identify the failing test from user input. If unclear, run the project's test command to see which fail.
2. Run only the failing test (e.g., `pytest tests/test_x.py::test_y -x -v`).
3. Read the test file in full; read the production module(s) it exercises.
4. Form a hypothesis:
   - Edge case in input?
   - Recent commit changed behavior?
   - Test depends on environment state (time, working dir, env var)?
   - Flaky (timing, ordering, shared mutable state)?
5. Verify by inspecting `git log -p <relevant files>` for recent changes.
6. Propose the smallest possible fix:
   - If the production code is wrong → fix the production code.
   - If the test was asserting the wrong invariant → fix the test (AND state explicitly that the test was wrong, with the new correct invariant).
   - If flaky → propose a test isolation fix (seed, freeze time, deterministic ordering).
7. Surface the proposed diff for confirmation. DO NOT apply without explicit "yes, apply" from the user.

## Constraints

- Never makes the test pass by deleting assertions.
- Never edits the test to match buggy production output.
- If the fix touches >2 files, stop and ask.
