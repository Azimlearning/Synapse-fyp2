"""Shared helpers for the Build Script tests: the Kit manifest, and the five fixture scripts with the Blueprint each one is built from."""

from __future__ import annotations

from pathlib import Path

import pytest

from api import kitmanifest
from api.kit import latest_version

FIXTURES = Path(__file__).parent / "fixtures"
BLUEPRINTS = Path(__file__).resolve().parents[1] / "blueprint" / "fixtures"
PAIRS = {
    "springs_series_planet": "good_hookes_mars_series",
    "pendulum_planet": "good_pendulum_angle",
    "titration_curve": "good_titration_dropper",
    "ramp_friction": "good_ramp_friction",
    "lens_image": "good_lens_image",
}


def script_text(name: str) -> str:
    return (FIXTURES / f"{name}.txt").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def manifest(kit_dist: Path) -> kitmanifest.Manifest:
    return kitmanifest.load(kit_dist, latest_version(kit_dist))
