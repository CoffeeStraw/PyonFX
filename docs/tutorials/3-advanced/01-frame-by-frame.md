# Tutorial: Frame-by-Frame Animations

Welcome to the advanced series.

So far, you’ve built rich effects using ASS tags and time-based transforms. That model goes a long way—but there are moments when you want finer, per-frame control than a single `\t(...)` can express cleanly. Typical cases include: position transformations that are not as simple as moving a syllable from one point to another (i.e. `\move`), non-linear tags transformations, particle effects, and more.

That’s where frame‑by‑frame comes in. Instead of asking the renderer to animate inside one long subtitle line, you generate one output line per video frame over a time span. Each frame has its own start/end time, and you decide exactly what tags to render for that slice.

In this tutorial, you’ll practice the main workflow: iterate frames and compute all the necessary values for each frame.

## Materials

We'll continue with the same [romaji_kanji_translation.ass](https://github.com/CoffeeStraw/PyonFX/blob/v1.0.0/examples/ass/romaji_kanji_translation.ass) file, building upon the foundation from previous tutorials.

## Code Walkthrough

### 0. Setup

We'll import what we need and prepare our usual I/O.

```python
from pyonfx import Ass, FrameUtility, Line, Syllable, Utils
import random

io = Ass("romaji_kanji_translation.ass", vertical_kanji=True)
meta, styles, lines = io.get_data()
```

### 1. Start simple: per-frame jitter for the highlight

We'll start by building the highlight effect. The idea: iterate each syllable's singing window frame-by-frame and nudge the rendered position slightly each frame.

```python
@io.track
def highlight_effect(line: Line, syl: Syllable, l: Line):
    fu = FrameUtility(
        line.start_time + syl.start_time,
        line.start_time + syl.end_time,
        meta.timestamps,
    )
    for s, e, i, n in fu:
        l.layer = 1
        l.start_time = s
        l.end_time = e

        # Constant jitter amplitude: ±5 px
        pos_x = syl.center + random.uniform(-5, 5)
        pos_y = syl.middle + random.uniform(-5, 5)

        tags = rf"\an5\pos({pos_x:.3f},{pos_y:.3f})"
        l.text = f"{{{tags}}}{syl.text}"
        io.write_line(l)
```

This already produces a lively highlight with subtle randomness.

What powers the loop above is `FrameUtility`, constructed with a start time, an end time, and the video timestamps from `meta`. Iterating it yields, for each frame: `(s, e, i, n)` where `s`/`e` are the current frame’s start/end in milliseconds and `i/n` is normalized progress from 0 to 1 across the span. It also exposes `duration` (the total span length) and helpers we’ll use shortly. See the reference for details: [`FrameUtility`](../../reference/utils.md#pyonfx.utils.FrameUtility).

### 2. Improve motion: dynamic amplitude with `fu.add(...)`

`FrameUtility.add(start, end, value)` returns a frame-local ramp based on the current frame's midpoint, measured within the iterator's time span:

- Before `start`: returns `0`
- Between `start` and `end`: linearly interpolates from `0` to `value`
- After `end`: returns `value`

Because it returns just “the contribution for this frame,” you can add multiple `fu.add(...)` calls together to build envelopes. For example, over a 0→duration window:

- `fu.add(0, duration/2,  +A)` grows from 0 to +A in the first half
- `fu.add(duration/2, duration,  -A)` grows from 0 to -A in the second half

Adding them yields a triangular envelope: 0 → +A → 0. We’ll use that as the jitter amplitude:

```python
@io.track
def highlight_effect(line: Line, syl: Syllable, l: Line):
    # Max amplitude
    max_amp = 5.0

    fu = FrameUtility(
        line.start_time + syl.start_time,
        line.start_time + syl.end_time,
        meta.timestamps,
    )
    for s, e, i, n in fu:
        l.layer = 1
        l.start_time = s
        l.end_time = e

        # Grow amplitude in first half, shrink in second half
        amp = fu.add(0, fu.duration / 2, max_amp)
        amp += fu.add(fu.duration / 2, fu.duration, -max_amp)

        pos_x = syl.center + random.uniform(-amp, amp)
        pos_y = syl.middle + random.uniform(-amp, amp)

        tags = rf"\an5\pos({pos_x:.3f},{pos_y:.3f})"
        l.text = f"{{{tags}}}{syl.text}"
        io.write_line(l)
```

Now the jitter ramps up and back down within the highlight window.

### 3. Add color transitions with interpolation

In the beginner series, you drove the highlight’s color change using ASS `\t(...)` transforms inside the tag string (see the earlier tutorials in `1-beginner/`, e.g. [Your First KFX](../1-beginner/01-first-kfx.md)). That approach tells the renderer how to animate between two colors over a time span.

Here, because we’re emitting one subtitle line per frame, we need the exact color for each frame. That’s what interpolation gives us: given a start time/value and an end time/value, compute the in‑between value for the current frame. Using `fu.interpolate(...)` ties the timing directly to the frame iterator, so each `(s, e)` window gets the correct color. If you ever need a value from a plain percentage instead of times, [`Utils.interpolate(...)`](../../reference/utils.md#pyonfx.utils.Utils.interpolate) does the same math from a 0..1 progress. Both variants support easing as a final parameter when you want non‑linear transitions.

```python
@io.track
def highlight_effect(line: Line, syl: Syllable, l: Line):
    # Max amplitude
    max_amp = 5.0

    # Original style values
    style_c1 = line.styleref.color1
    style_c3 = line.styleref.color3

    # Target values
    target_c1 = "&HFFFFFF&"
    target_c3 = "&HABABAB&"

    fu = FrameUtility(
        line.start_time + syl.start_time,
        line.start_time + syl.end_time,
        meta.timestamps,
    )
    for s, e, i, n in fu:
        l.layer = 1
        l.start_time = s
        l.end_time = e

        # Position (jitter)
        amp = fu.add(0, fu.duration / 2, max_amp)
        amp += fu.add(fu.duration / 2, fu.duration, -max_amp)
        pos_x = syl.center + random.uniform(-amp, amp)
        pos_y = syl.middle + random.uniform(-amp, amp)

        # Color
        t1_c1 = fu.interpolate(0, fu.duration / 2, style_c1, target_c1)
        t1_c3 = fu.interpolate(0, fu.duration / 2, style_c3, target_c3)
        t2_c1 = fu.interpolate(fu.duration / 2, fu.duration, t1_c1, style_c1)
        t2_c3 = fu.interpolate(fu.duration / 2, fu.duration, t1_c3, style_c3)

        tags = rf"\an5\pos({pos_x:.3f},{pos_y:.3f})\1c{t2_c1}\3c{t2_c3}"
        l.text = f"{{{tags}}}{syl.text}"

        io.write_line(l)
```

### 4. Lead-in and lead-out with Bezier motion and easing

For the lead-in/lead-out, we will move the text along a smooth Bezier curve before and after the main highlight. We’ll use the third‑party `bezier` package to define quadratic curves and evaluate points along them per frame. Install with `pip install bezier` if needed.

For the lead-in, we will have:

```python
import bezier

@io.track
def leadin_effect(line: Line, syl: Syllable, l: Line):
    # Control points (start above-left, curve, end at syllable center)
    x0, y0 = syl.center - 60.0, syl.middle - 20.0
    x1, y1 = syl.center - 20.0, syl.middle - 50.0
    x2, y2 = syl.center, syl.middle
    curve = bezier.Curve([[x0, x1, x2], [y0, y1, y2]], degree=2)

    # Frame-by-frame movement
    fu = FrameUtility(line.start_time - line.leadin // 2, line.start_time, meta.timestamps)
    for s, e, i, n in fu:
        l.layer = 0
        l.start_time = s
        l.end_time = e

        # Position (evaluate Bezier curve)
        pct = Utils.accelerate(i/n, "out_quart")
        curve_point = curve.evaluate(pct)
        x, y = float(curve_point[0][0]), float(curve_point[1][0])

        # Alpha (fade-in)
        alpha = fu.interpolate(0, fu.duration, "&HFF&", "&H00&", "out_quart")

        tags = rf"\an5\pos({x:.3f},{y:.3f})\alpha{alpha}"
        l.text = f"{{{tags}}}{syl.text}"

        io.write_line(l)

    # Static until syllable start
    l.layer = 0
    l.start_time = line.start_time
    l.end_time = line.start_time + syl.start_time
    
    tags = rf"\an5\pos({syl.center:.3f},{syl.middle:.3f})"
    l.text = f"{{{tags}}}{syl.text}"
    io.write_line(l)
```

!!! note "A quick note on easing"

    Easing controls how fast progress moves from start to end. With ASS `\t(...)`, you can only supply a single acceleration exponent per segment (or keep it linear), and you must bake all timing into tags. In frame‑by‑frame you have more control:

    - `fu.interpolate(...)` and `Utils.interpolate(...)` accept:
        - a float exponent (classic ASS‑style acceleration)
        - a named preset (e.g., `"out_quart"`, `"in_back"`, `"in_out_sine"`)
        - a custom Python callable for fully bespoke curves
    - `Utils.accelerate(...)` is the low-level function that applies a given easing to a progress percentage. In this case, we use it to change the progress along the Bezier curve. See [`Utils.accelerate`](../../reference/utils.md#pyonfx.utils.Utils.accelerate).

    For a visual gallery of common presets and their shapes, see [easings.net](https://easings.net/). In PyonFX, use their snake_case variants (e.g., `easeOutQuart` → `"out_quart"`).

Leadout mirrors the idea (different control points, reverse easing, and fading out toward the end). See the full source at the end for the complete implementation.

### 5. Putting it together

As in earlier tutorials, we keep effects modular (`leadin_effect`, `highlight_effect`, `leadout_effect`) and call them from a romaji processor using `Utils.all_non_empty(...)`. Save and preview as usual:

```python
io.save()
io.open_aegisub()
```

## Conclusion

You've built a frame-by-frame highlight with controlled jitter and colour transitions, then wrapped it with Bezier-based lead-in/out for a smooth entrance and exit. You now know how to:

- Iterate and render per frame with `FrameUtility`
- Shape progress with `Utils.accelerate`
- Interpolate colours/alpha with `FrameUtility.interpolate` (or `Utils.interpolate`)
- Use quadratic Beziers for smooth spatial motion

In the next tutorial we'll get back to the Shape realm, but this time we'll use the text as a shape.

## Full Source Code

??? abstract "Show full source code"
    ```python
    --8<-- "examples/tutorials/3_advanced/01_frame_by_frame.py"
    ```


