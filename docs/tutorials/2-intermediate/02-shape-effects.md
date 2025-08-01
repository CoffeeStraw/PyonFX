# Tutorial: Shape Effects with PyonFX

Welcome to the second tutorial of the intermediate series.

You've built a solid karaoke system with variations and theming. In this tutorial, you'll learn how to use PyonFX's `Shape` module to integrate geometric shapes into your karaoke effects. You'll create moving, rotating, and animated shapes that add visual interest to complement your syllable highlighting.

## Materials

We'll continue with the same [romaji_kanji_translation.ass](https://github.com/CoffeeStraw/PyonFX/blob/v1.0.0/examples/ass/romaji_kanji_translation.ass) file, building upon the foundation from previous tutorials.

## Understanding PyonFX Shapes

PyonFX's `Shape` class is a powerful tool for creating and manipulating vector graphics programmatically. It provides methods to:

- **Generate new shapes**: like rectangles, circles, stars and more
- **Integrate with ASS**: automatic conversion to and from ASS drawing commands
- **Manipulate shapes**: geometric transformations (e.g., move, scale, rotate, shear), analysis (e.g., bounding box computation), and more

For more information, please refer to the [reference documentation](../../reference/shape.md#pyonfx.shape.Shape).

Shapes are perfect for creating backgrounds, decorative elements, particle effects and more to enhance the visual appeal of your karaoke.

## Code Walkthrough

**0. Familiar Setup with New Imports**

We start with our familiar pattern but add the `Shape` module and the built-in `random` module:

```python
from pyonfx import Ass, Convert, Line, Shape, Syllable, Utils
import random

io = Ass("../../ass/romaji_kanji_translation.ass", vertical_kanji=True)
meta, styles, lines = io.get_data()
```

**1. Creating Utility Functions for Complex Animations**

Let's start by building a utility function for creating oscillating animations:

```python
def generate_oscillating_transforms(
    start_time: int, end_time: int, cycle_duration: int, tags1: str, tags2: str
) -> str:
    """Generate a string of oscillating \\t transformations between two sets of tags.

    Alternates tags1/tags2 every half of cycle_duration, from start_time to end_time.
    """
    duration = end_time - start_time
    if duration <= 0 or cycle_duration <= 0:
        return ""

    half_cycle = cycle_duration // 2
    transforms = []

    # We step through each full cycle
    for current_time in range(0, duration, cycle_duration):
        first_half_end = min(current_time + half_cycle, duration)
        second_half_end = min(current_time + cycle_duration, duration)

        # First half: to tags1
        if first_half_end > current_time:
            transforms.append(
                f"\\t({start_time + current_time},{start_time + first_half_end},{tags1})"
            )
        # Second half: to tags2
        if second_half_end > first_half_end:
            transforms.append(
                f"\\t({start_time + first_half_end},{start_time + second_half_end},{tags2})"
            )

    return "".join(transforms)
```

This function creates smooth oscillating animations by generating a series of transform (`\t`) tags that alternate between two states. We'll make use of this function in the next section.

**2. Creating Pulsing Heart Decorations**

Let's use our utility function to create pulsing heart shapes that appear on both sides of each line:

```python
@io.track
def heartbeat_effect(line: Line, l: Line):
    """Creates pulsing hearts on the left and right sides of each line"""
    l.layer = 0
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.end_time + line.leadout // 2

    # Configuration
    HEART_SHAPE = Shape.heart(30)
    HEARTBEAT_PERIOD = 800  # milliseconds for one heartbeat cycle
    HEART_SCALE_MIN = 80  # minimum scale percentage
    HEART_SCALE_MAX = 120  # maximum scale percentage
    HEART_OFFSET = 30  # pixels spacing from text

    # Generate oscillating scale transforms
    scale_max = rf"\fscx{HEART_SCALE_MAX}\fscy{HEART_SCALE_MAX}"
    scale_min = rf"\fscx{HEART_SCALE_MIN}\fscy{HEART_SCALE_MIN}"
    oscillating_transforms = generate_oscillating_transforms(
        0, l.duration, HEARTBEAT_PERIOD, scale_max, scale_min
    )

    # Prepare common tags for both hearts
    common_tags = (
        rf"\fad({line.leadin // 4},{line.leadin // 4})"
        rf"{oscillating_transforms}"
        rf"\1c&HEAE3FF&\3c&HCBBBFF&\bord2\shad0\p1"
    )

    # Left heart
    position_tags = rf"\an5\pos({line.left - HEART_OFFSET},{line.middle})"
    l.text = f"{{{position_tags}{common_tags}}}{HEART_SHAPE}"
    io.write_line(l)

    # Right heart
    position_tags = rf"\an5\pos({line.right + HEART_OFFSET},{line.middle})"
    l.text = f"{{{position_tags}{common_tags}}}{HEART_SHAPE}"
    io.write_line(l)
```

This creates heart shapes that pulse in sync on both sides of each line.

**3. Creating Dynamic Shape Effects**

Now let's create random moving shapes that appear behind syllables:

```python
@io.track
def main_effect_shapes(line: Line, syl: Syllable, l: Line):
    """Creates random moving and rotating shapes behind syllables"""
    l.layer = 0
    l.start_time = line.start_time + syl.start_time
    l.end_time = line.start_time + syl.end_time

    # Configuration
    SHAPE_SIZE = 20  # pixels
    HIGHLIGHT_SHAPES: list[Shape] = [
        Shape.triangle(SHAPE_SIZE, SHAPE_SIZE),
        Shape.rectangle(SHAPE_SIZE, SHAPE_SIZE),
        Shape.polygon(5, SHAPE_SIZE),  # pentagon
        Shape.polygon(6, SHAPE_SIZE),  # hexagon
        Shape.ellipse(SHAPE_SIZE, SHAPE_SIZE),
        Shape.circle(SHAPE_SIZE),
        Shape.ring(SHAPE_SIZE, SHAPE_SIZE // 2),
        Shape.star(5, SHAPE_SIZE // 2, SHAPE_SIZE),
        Shape.glance(4, SHAPE_SIZE // 2, SHAPE_SIZE),
    ]
    SHAPES_NUMBER = 10
```

We define a collection of shapes and then generate multiple instances with random properties:

```python
    for _ in range(SHAPES_NUMBER):
        # Generate random shape
        shape = random.choice(HIGHLIGHT_SHAPES)

        # Random movement parameters
        start_x = syl.center
        start_y = syl.middle
        end_x = start_x + random.randint(-int(syl.width * 0.7), int(syl.width * 0.7))
        end_y = start_y + random.randint(-int(syl.height * 0.7), int(syl.height * 0.7))

        # Random rotation
        rotation = random.randint(90, 270) * (1 if random.random() > 0.5 else -1)

        # Random color (bright colors)
        r = random.randint(127, 255)
        g = random.randint(127, 255)
        b = random.randint(127, 255)
        color = Convert.color_rgb_to_ass((r, g, b))

        # Fade out duration
        fade_duration = syl.duration // 4
```

Notice how we generate random colors: we create RGB values (each component from 127-255 to ensure bright colors) and then use `Convert.color_rgb_to_ass()` to convert the RGB tuple into ASS color format.

Finally, we create the ASS drawing and animate it:

```python
        tags = (
            rf"\an5\move({start_x},{start_y},{end_x},{end_y})"
            rf"\fad({fade_duration},{fade_duration})"
            rf"\t(\frz{rotation})"
            rf"\fscx{syl.height}\fscy{syl.height}"
            rf"\bord1\1c{color}\3c&H000000&\p1"
        )
        l.text = f"{{{tags}}}{shape}"
        io.write_line(l)
```

Each shape starts at the syllable's center, moves to a random nearby position, rotates, and fades in/out.

**4. Reusing Previous Leadin/Main/Leadout Effects**

Since they are not the focus of this tutorial, let's reuse the same `leadin_effect()`, `main_effect()`, and `leadout_effect()` functions from the [previous tutorial](../1-beginner/03-romaji-kanji-translation.md). Simply copy and paste them into your code.

**5. Enhanced Line Processors with the new effects**

We integrate our shape effects into the line processing workflow:

```python
@io.track
def romaji(line: Line, l: Line):
    heartbeat_effect(line, l)
    for syl in Utils.all_non_empty(line.syls):
        leadin_effect(line, syl, l)
        main_effect(line, syl, l)
        main_effect_shapes(line, syl, l)
        leadout_effect(line, syl, l)


# Process all lines
for line in Utils.all_non_empty(lines):
    l = line.copy()
    if line.styleref.alignment >= 7:
        romaji(line, l)
```

Notice that for this effect we focus on romaji lines only.

**6. Saving and Previewing Your Masterpiece**

Save and preview your enhanced karaoke system:

```python
io.save()
io.open_aegisub()
```

You'll now see an enhanced karaoke experience with:

- **Pulsing heart decorations** that appear on both sides of lines
- **Dynamic shape particles** that move around syllables during highlighting

## Conclusion

Great job. You've now learned the fundamentals of PyonFX's shape system. You've discovered how to create geometric animations and build utility functions for reusable animation patterns. Your karaoke effects now include heart decorations with pulsing animations and dynamic particle effects.

You've built a solid foundation covering text segmentation, timing, positioning, theming, variations, and shape integration. This gives you the tools needed to create engaging karaoke effects for a variety of projects.

And thus, this concludes the intermediate series. The advanced series will cover even more sophisticated techniques and workflows.

## Full Source Code
??? abstract "Show full source code"
    ```python
    --8<-- "examples/tutorials/2_intermediate/02_shape_effects.py"
    ```