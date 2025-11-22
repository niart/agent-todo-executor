#!/usr/bin/env python
import argparse
from todo_agent.config import Settings
from todo_agent.models import SessionState, TaskStatus
from todo_agent.planner import propose_todo_list, edit_tasks_interactively
from todo_agent.executor import run_execution_loop, save_session_to_file


def ask_goal_from_user() -> str:
    print("=== Agent-Driven TODO Executor ===")
    print("Describe your high-level goal in one or more sentences.")
    print("Example: 'Build a basic coupon marketplace with a landing page and CRUD listings.'")
    goal = input("\nYour goal: ").strip()
    while not goal:
        goal = input("Goal cannot be empty. Please enter again: ").strip()
    return goal


def ask_mode_from_user(default_mode: str = "confirm") -> str:
    print("\nChoose run mode:")
    print("  [c] confirm   – propose TODO list, then ask for approval before execution")
    print("  [a] auto      – propose TODO list and immediately execute")
    choice = input(f"Mode [c/a] (default {default_mode[0]}): ").strip().lower()

    if choice == "a":
        return "auto"
    return "confirm"


def confirm_todo_list(state: SessionState) -> bool:
    """
    Implements the 'confirm' mode interaction:
      - approve
      - edit
      - regenerate
      - cancel
    """
    while True:
        print("\n=== Proposed TODO List ===")
        for task in state.tasks:
            print(f"[{task.id}] {task.title}")
            print(f"    {task.description}\n")

        print("What would you like to do?")
        print("  [a] approve and execute")
        print("  [e] edit tasks manually")
        print("  [r] regenerate TODO list")
        print("  [c] cancel and exit")
        choice = input("Choice [a/e/r/c]: ").strip().lower()

        if choice == "a":
            return True
        elif choice == "e":
            edit_tasks_interactively(state)
        elif choice == "r":
            state.tasks = propose_todo_list(state.goal, state.settings)
        elif choice == "c":
            print("Session cancelled.")
            return False
        else:
            print("Invalid choice, please pick one of a/e/r/c.")


def main():
    parser = argparse.ArgumentParser(description="Agent-Driven TODO Executor")
    parser.add_argument(
        "--mode",
        choices=["confirm", "auto"],
        default="confirm",
        help="Run in 'confirm' or 'auto' mode.",
    )
    parser.add_argument(
        "--goal",
        type=str,
        default=None,
        help="Optional: provide the high-level goal via CLI instead of interactive input.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override default LLM model for both planning and execution.",
    )
    parser.add_argument(
        "--session-file",
        type=str,
        default=None,
        help="Optional path to save session JSON (defaults to session-<timestamp>.json).",
    )
    args = parser.parse_args()

    settings = Settings()
    if args.model:
        settings.model = args.model

    # 1. Goal
    goal = args.goal or ask_goal_from_user()

    # 2. Mode
    mode = args.mode or ask_mode_from_user()
    print(f"\nUsing mode: {mode}")

    # 3. Planning (chat → TODO list)
    state = SessionState(goal=goal, mode=mode, settings=settings)
    print("\nPlanning TODO list with the LLM...")
    state.tasks = propose_todo_list(goal, settings)

    # 4. Confirm mode handling
    if mode == "confirm":
        approved = confirm_todo_list(state)
        if not approved:
            return
    else:
        # Auto mode: just show the list and proceed
        print("\n=== Proposed TODO List (auto mode) ===")
        for task in state.tasks:
            print(f"[{task.id}] {task.title}")
            print(f"    {task.description}\n")

    # 5. Execution loop
    print("\n=== Starting execution loop ===")
    run_execution_loop(state)

    # 6. Final summary
    print("\n=== Final Task Statuses ===")
    for task in state.tasks:
        print(f"[{task.id}] {task.title} -> {task.status}")
        if task.result:
            print("  Result (truncated):", task.result[:200].replace("\n", " "), "...")
        if task.reflection:
            print("  Reflection:", task.reflection.replace("\n", " "))
        print()

    # 7. Save session to JSON
    path = save_session_to_file(state, args.session_file)
    print(f"Session saved to: {path}")


if __name__ == "__main__":
    main()
