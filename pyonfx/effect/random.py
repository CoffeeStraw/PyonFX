"""Stable random-seed derivation for reproducible effects."""

from __future__ import annotations

import hashlib
import random
from typing import TypeAlias


SeedComponent: TypeAlias = str | bytes | int
_PERSONALIZATION = b"PyonFXSeedV1"


def _encode_component(component: SeedComponent) -> bytes:
    if isinstance(component, bool):
        payload = b"1" if component else b"0"
        type_tag = b"t"
    elif isinstance(component, int):
        payload = str(component).encode("ascii")
        type_tag = b"i"
    elif isinstance(component, str):
        payload = component.encode("utf-8")
        type_tag = b"s"
    elif isinstance(component, bytes):
        payload = component
        type_tag = b"b"
    else:
        raise TypeError(
            "seed components must be str, bytes, int, or bool; "
            f"got {type(component).__name__}"
        )
    return type_tag + len(payload).to_bytes(8, "big") + payload


def derive_seed(
    base_seed: int,
    *components: SeedComponent,
    namespace: str = "",
) -> int:
    """Derive a stable unsigned 64-bit seed from explicit effect components.

    The result does not use Python's randomized ``hash()`` and therefore stays
    stable across processes. Component type and length prefixes prevent values
    such as ``("ab", "c")`` and ``("a", "bc")`` from colliding by simple
    concatenation. The algorithm is versioned by its BLAKE2 personalization.
    """

    if isinstance(base_seed, bool) or not isinstance(base_seed, int):
        raise TypeError("base_seed must be an int")
    hasher = hashlib.blake2b(digest_size=8, person=_PERSONALIZATION)
    hasher.update(_encode_component(base_seed))
    hasher.update(_encode_component(namespace))
    for component in components:
        hasher.update(_encode_component(component))
    return int.from_bytes(hasher.digest(), "big", signed=False)


def random_for(
    base_seed: int,
    *components: SeedComponent,
    namespace: str = "",
) -> random.Random:
    """Return an independent Random instance initialized by :func:`derive_seed`."""

    return random.Random(derive_seed(base_seed, *components, namespace=namespace))
