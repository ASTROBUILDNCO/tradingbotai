#!/usr/bin/env python3
from astro_agent.orchestrator import Orchestrator
import sys


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "morning"
    o = Orchestrator()
    if cmd == "morning":
        o.run_morning_routine()
    elif cmd == "midday":
        o.run_midday_routine()
    elif cmd == "evening":
        o.run_evening_routine()
    elif cmd == "approval-queue":
        o.display_approval_queue()
    elif cmd == "approve" and len(sys.argv) > 2:
        print(o.approve_action(sys.argv[2]))
    elif cmd == "skip" and len(sys.argv) > 2:
        print(o.skip_action(sys.argv[2]))
    else:
        print("Usage: python run_agent.py morning|midday|evening|approval-queue|approve <id>|skip <id>")


if __name__ == "__main__":
    main()
