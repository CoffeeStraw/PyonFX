# PyonFX: An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).
# Copyright (C) 2019-2025 Antonio Strippoli (CoffeeStraw/YellowFlash)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations

import pytest

from pyonfx.effect import derive_seed, random_for


def test_derive_seed_has_versioned_golden_values() -> None:
    assert (
        derive_seed(123, "line", 5, "syl", 2, namespace="spark") == 3591443096792222611
    )
    assert derive_seed(-1, b"abc", True, namespace="test") == 10078699247941838880


def test_derive_seed_distinguishes_component_boundaries_and_types() -> None:
    assert derive_seed(1, "ab", "c") != derive_seed(1, "a", "bc")
    assert derive_seed(1, "1") != derive_seed(1, 1)
    assert derive_seed(1, True) != derive_seed(1, 1)


def test_namespace_isolated_random_streams() -> None:
    sparks = random_for(42, 3, namespace="sparks")
    particles = random_for(42, 3, namespace="particles")
    repeated = random_for(42, 3, namespace="sparks")

    spark_values = [sparks.random() for _ in range(5)]
    assert spark_values == [repeated.random() for _ in range(5)]
    assert spark_values != [particles.random() for _ in range(5)]


@pytest.mark.parametrize("component", [1.5, object(), None])
def test_derive_seed_rejects_unstable_component_types(component: object) -> None:
    with pytest.raises(TypeError, match="seed components"):
        derive_seed(1, component)  # type: ignore[arg-type]


def test_derive_seed_rejects_boolean_base_seed() -> None:
    with pytest.raises(TypeError, match="base_seed"):
        derive_seed(True)
