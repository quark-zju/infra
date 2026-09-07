#!/usr/bin/env python3
"""Run pyinfra CLI while reporting wall time spent in each StateStage."""

from __future__ import annotations

import atexit
import time

from gevent import monkey

monkey.patch_all()

from pyinfra.api.state import State, StateStage

START = time.monotonic()
transitions: list[tuple[StateStage, float]] = []
original_set_stage = State.set_stage


def timed_set_stage(self: State, stage: StateStage) -> None:
    transitions.append((stage, time.monotonic()))
    original_set_stage(self, stage)


State.set_stage = timed_set_stage


def report() -> None:
    end = time.monotonic()
    points = [(StateStage.Setup, START), *transitions]
    if not transitions or transitions[-1][0] != StateStage.Disconnect:
        points.append((StateStage.Disconnect, end))
    print("\npyinfra stage timing (wall seconds):")
    for (stage, began), (_, finished) in zip(points, points[1:]):
        print(f"  {stage.name.lower():<10} {finished - began:8.3f}")
    print(f"  {'total':<10} {end - START:8.3f}")


atexit.register(report)

from pyinfra_cli.main import main

if __name__ == "__main__":
    main()
