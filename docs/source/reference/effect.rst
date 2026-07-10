.. _effect-ref:

Effect Helpers
==============

Timing
------

The timing helpers make the chosen time basis explicit and return absolute
millisecond boundaries::

   from pyonfx.effect import retime_line, retime_syllable

   start, end = retime_line(line.start_time, line.end_time, -200, 300)
   syl_start, syl_end = retime_syllable(
       line.start_time,
       syl.start_time,
       syl.end_time,
       -50,
       100,
   )

Results are clamped to non-negative timestamps. ``retime_line`` additionally
ensures that the returned end is not earlier than the returned start.

Deterministic random streams
----------------------------

Python's built-in ``hash()`` is randomized between interpreter processes, so
it must not be used to derive seeds for reproducible effects. ``derive_seed``
uses a versioned BLAKE2b encoding with type and length prefixes::

   from pyonfx.effect import derive_seed, random_for

   seed = derive_seed(2026, line.index, syl.i, namespace="spark")
   rng = random_for(2026, line.index, syl.i, namespace="spark")
   x_offset = rng.uniform(-20, 20)

The result is a stable unsigned 64-bit integer for the same supported inputs.
Namespaces should identify independent effect subsystems so that adding a
random draw in one subsystem does not perturb another. Supported components
are ``str``, ``bytes``, ``int``, and ``bool``.

API reference
-------------

.. automodule:: pyonfx.effect.timing
   :members:

.. automodule:: pyonfx.effect.random
   :members:
