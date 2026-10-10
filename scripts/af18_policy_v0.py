#!/usr/bin/env python3
"""Compatibility entry point for the historical AF18 policy-v0 source."""

from pathlib import Path

from af18_policy import *
from af18_policy import main as policy_main

DEFAULT_POLICY = Path(__file__).resolve().parents[1] / "policies" / "af18-policy-v0.yaml"


def main() -> int:
    return policy_main(DEFAULT_POLICY)


if __name__ == "__main__":
    raise SystemExit(main())
