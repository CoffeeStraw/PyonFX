.. _events-ref:

Lightweight Events and Output
=============================

``Event`` is a small, immutable ASS output record. It contains only the
fields required for serialization, so effects that generate many new events
do not need to deep-copy an extended :class:`pyonfx.ass_core.Line` with its
words, syllables, characters, geometry, and style references.

Creating events
---------------

Import ``Event`` from the package root and construct it directly, or use
:meth:`pyonfx.events.Event.from_line` when most serializable fields should be
copied from an input line::

   from pyonfx import Ass, Event

   io = Ass("in.ass", "out.ass", extended_features={"line"})
   _, _, lines = io.get_data()

   event = Event.from_line(
       lines[0],
       text=r"{\an5\pos(640,360)}Generated text",
   )
   io.write_event(event)
   io.save()

``Event`` instances are frozen. Create a new instance when a field changes;
do not treat them as mutable ``Line`` replacements.

Batch and streaming output
--------------------------

Use :meth:`pyonfx.ass_core.Ass.write_events` when the generated events already
fit comfortably in memory. The method reuses formatted timestamps within the
batch::

   io.write_events(
       Event.from_line(line, text=f"{{\\alpha&H80&}}{i}")
       for i in range(1000)
   )
   io.save()

Use :meth:`pyonfx.ass_core.Ass.save_events` for very large generators. It
writes bounded batches directly to the output file instead of retaining every
serialized event::

   def generated_events(line):
       for i in range(100_000):
           yield Event.from_line(line, text=str(i))

   io.save_events(generated_events(lines[0]), batch_size=4096, quiet=True)

``save_events`` is a terminal write operation: it writes the header, styles,
original lines, any previously buffered output, the streamed events, and
Extradata. Do not call ``save()`` afterward for the same output.

Selective extended processing
-----------------------------

The optional ``extended_features`` argument avoids building data an effect
does not use::

   Ass("in.ass", extended_features={"line"})
   Ass("in.ass", extended_features={"words"})
   Ass("in.ass", extended_features={"syllables"})
   Ass("in.ass", extended_features={"chars"})

Dependencies are added automatically in this order:
``line -> words -> syllables -> chars``. Passing ``None`` preserves the
historical full extended behavior. ``extended=False`` still performs base ASS
parsing only, and cannot be combined with ``extended_features``. Vertical
kanji processing currently requires character data.

API reference
-------------

.. automodule:: pyonfx.events
   :members:
