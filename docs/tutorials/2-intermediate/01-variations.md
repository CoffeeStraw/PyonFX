# Tutorial: Adding Variations to Your Karaoke Effects

Welcome to the intermediate series! :rocket:

You've built a solid foundation with a complete three-line karaoke system, but it can quickly become boring: we should add some variety. Different singers might need different visual styles or special moments in songs (e.g. refrains) might call for dedicated effects.

In this tutorial, you'll learn how to add variations by defining when to do so directly in your .ass file, and then reading them in your code to apply the variations.

## Materials

We'll continue with the same [romaji_kanji_translation.ass](https://github.com/CoffeeStraw/PyonFX/blob/v1.0.0/examples/ass/romaji_kanji_translation.ass) file, but this time we'll leverage some additional data that's been prepared in the file:

- **Actor fields**: Different lines are assigned to "Singer1" and "Singer2" to demonstrate personalized theming
- **Inline effects**: Some syllables are marked with special `inline_fx` (`\-fx`) tags for dramatic moments
- **Color transformations**: The file includes existing color styling that we'll preserve and enhance

## Code Walkthrough

**0. Enhanced Setup with New Imports**

We start with our familiar pattern but import several new PyonFX components:

```python
from pyonfx import Ass, ColorUtility, Convert, Line, Syllable, Utils

io = Ass("romaji_kanji_translation.ass", vertical_kanji=True)
meta, styles, lines = io.get_data()
```

The new imports unlock powerful features:

- **`ColorUtility`**: Preserves and works with existing color transformations in your input file
- **`Convert`**: Provides utilities for converting between different ASS value formats (like alpha values)

**1. Setting Up Color Preservation with ColorUtility**

First, let's set up PyonFX's `ColorUtility` to preserve any existing color styling from our input file:

```python
# Set up ColorUtility to preserve existing color transformations
cu = ColorUtility(lines)
```

`ColorUtility` is a utility that analyzes your entire ASS file and extracts any existing color changes or transformations (like `\1c`, `\3c`, `\t` tags). It then provides methods to recreate those color effects in your output, ensuring that any original styling is maintained while your karaoke effects are applied.

This way you don't need to hardcode color changes in your code: simply use `cu.get_color_change(line, c1=True, c3=True)` to get the color changes for a line, and then apply them to your output. For more information, see the [ColorUtility documentation](../../reference/utils.md#pyonfx.utils.ColorUtility).

**2. Creating Actor-Based Theme System**

Next, let's prepare a dictionary of color themes for different performers:

```python
# Define color themes for different actors
ACTOR_THEMES = {
    "Singer1": {
        "highlight": "&H4B19E6&",  # Purple
        "outline": "&H8B4B9B&",   # Light purple
        "fade": "&HBB6BFF&",      # Very light purple
    },
    "Singer2": {
        "highlight": "&H19E64B&",  # Green
        "outline": "&H4B9B8B&",   # Light green
        "fade": "&H6BFFBB&",      # Very light green
    },
    "": {  # Default (no actor)
        "highlight": "&HFFFFFF&",  # White
        "outline": "&HABABAB&",   # Gray
        "fade": "&HDDDDDD&",      # Light gray
    },
}
```

**3. Enhanced Leadin/Leadout Effect with Theming**

Let's upgrade our leadin effect to use the theme system:

```python
@io.track
def leadin_effect(line: Line, syl: Syllable, l: Line):
    l.layer = 0
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.start_time + syl.start_time

    # Original values
    original_c1 = line.styleref.color1
    original_c3 = line.styleref.color3

    # Configuration
    theme = ACTOR_THEMES.get(line.actor, ACTOR_THEMES[""])

    tags = (
        rf"\an5\pos({syl.center},{syl.middle})"
        rf"\1c{theme['fade']}\3c{theme['outline']}"
        rf"\t(0,{line.leadin // 2},\1c{original_c1}\3c{original_c3})"
        rf"\fad({line.leadin // 2},0)"
    )
    l.text = f"{{{tags}}}{syl.text}"

    io.write_line(l)
```

Notice how we:

- **Extract the theme** using `ACTOR_THEMES.get(line.actor, ACTOR_THEMES[""])` - this gets the actor's theme or falls back to default
- **Start with theme colors** then transition to the original line colors using `\t()` transforms
- **Preserve original styling** by storing and returning to `original_c1` and `original_c3`

We can do something similar for the leadout effect, but we'll leave it to you for exercise! (Or you could check the full source code at the end of this tutorial :wink:)

**4. Enhanced Main Effect with Theming**

Let's also apply the theme to the main effect:

```python
@io.track
def main_effect(line: Line, syl: Syllable, l: Line):
    l.layer = 1
    l.start_time = line.start_time + syl.start_time
    l.end_time = line.start_time + syl.end_time

    # Original values
    c1 = line.styleref.color1
    c3 = line.styleref.color3
    fscx = line.styleref.scale_x
    fscy = line.styleref.scale_y

    # Configuration
    theme = ACTOR_THEMES.get(line.actor, ACTOR_THEMES[""])
    new_fscx = fscx * 1.25
    new_fscy = fscy * 1.25

    tags = (
        rf"\an5\pos({syl.center},{syl.middle})"
        rf"\t(0,{l.duration // 2},\fscx{new_fscx}\fscy{new_fscy}\1c{theme['highlight']}\3c{theme['outline']})"
        rf"\t({l.duration // 2},{syl.duration},\fscx{fscx}\fscy{fscy}\1c{c1}\3c{c3})"
    )
    l.text = f"{{{tags}}}{syl.text}"

    io.write_line(l)
```

**5. Creating Special Effects for Dramatic Moments**

For syllables marked with special effects, we'll create a dramatic echo effect:

```python
@io.track
def main_echo_effect(line: Line, syl: Syllable, l: Line):
    l.layer = 1
    l.start_time = line.start_time + syl.start_time
    l.end_time = line.start_time + syl.end_time

    # Get original color values
    c1 = line.styleref.color1
    fscx = line.styleref.scale_x
    fscy = line.styleref.scale_y

    # Configuration
    theme = ACTOR_THEMES.get(line.actor, ACTOR_THEMES[""])
    n_echo_layers = 8
    target_fscx = fscx * 1.6
    target_fscy = fscy * 1.6
    base_alpha = 130
    target_alpha = 230

    # Base layer
    tags = (
        rf"\an5\pos({syl.center},{syl.middle})"
        rf"\alpha&H00&"
        rf"\t(0,{syl.duration // 2},\1c{theme['highlight']})"
        rf"\t({syl.duration // 2},{syl.duration},\1c{c1})"
    )
    l.text = f"{{{tags}}}{syl.text}"
    io.write_line(l)

    # Echo layers
    for i in range(1, n_echo_layers + 1):
        l.layer = 1 + i

        # Target scale increases with each layer
        current_fscx = fscx + (target_fscx - fscx) * (i / n_echo_layers)
        current_fscy = fscy + (target_fscy - fscy) * (i / n_echo_layers)
        # Alpha decreases with each layer (from base_alpha to target_alpha)
        current_alpha = Convert.alpha_dec_to_ass(
            base_alpha + (target_alpha - base_alpha) * (i / n_echo_layers)
        )

        tags = (
            rf"\an5\pos({syl.center},{syl.middle})"
            rf"\alpha{current_alpha}"
            rf"\t(0,{syl.duration // 2},\1c{theme['highlight']}\fscx{current_fscx}\fscy{current_fscy})"
            rf"\t({syl.duration // 2},{syl.duration},\1c{c1}\fscx{fscx}\fscy{fscy})"
            rf"\fad({syl.duration // 4},{syl.duration // 4})"
        )

        l.text = f"{{{tags}}}{syl.text}"
        io.write_line(l)
```

This creates a multi-layered echo effect where:

- **Base layer**: Normal syllable with color transitions
- **Echo layers**: 8 additional layers with progressively larger scale and increasing transparency
- **Mathematical progression**: Each layer scales and fades according to its position in the sequence
- **Convert utility**: `Convert.alpha_dec_to_ass()` converts decimal alpha values (0-255) to ASS hex format

**6. Upgrading Effect Dispatch**

Now we enhance our handler functions to automatically choose effects based on syllable properties:

```python
@io.track
def romaji(line: Line, l: Line):
    for syl in Utils.all_non_empty(line.syls):
        leadin_effect(line, syl, l)
        if syl.inline_fx == "echo":
            main_echo_effect(line, syl, l)
        else:
            main_effect(line, syl, l)
        leadout_effect(line, syl, l)
```

The `syl.inline_fx` property contains any special effect tags from your ASS file. When PyonFX finds `{\fx}echo{\fxend}` tags around a syllable, it automatically sets `syl.inline_fx = "echo"`, triggering our special effect.

We'll leave up to you to upgrade the kanji dispatcher as well!

**7. Making use of ColorUtility in the translation lines**

For translation lines, we'll use `ColorUtility` to preserve any existing color styling:

```python
@io.track
def translation(line: Line, l: Line):
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.end_time + line.leadout // 2

    tags = (
        rf"\fad({line.leadin // 2}, {line.leadout // 2})"
        f"{cu.get_color_change(l, c1=True, c3=True)}"
    )

    l.text = f"{{{tags}}}{line.text}"

    io.write_line(l)
```

`ColorUtility.get_color_change()` uses the timing of your line (`l.start_time` and `l.end_time`) to determine which color transformations from the original ASS file should be applied during that time range. It generates the appropriate ASS tags to recreate those color effects at the correct timing. This means if your input file has color transformations that overlap with your line's timing, those colors will be accurately reproduced in the output.

**8. Final Result**

Save and preview your effect:

```python
io.save()
io.open_aegisub()
```

You'll now see a sophisticated karaoke experience with:

- **Color-coded singers**: Different performers get distinct visual themes
- **Special effects**: Syllables marked for emphasis get dramatic echo effects
- **Preserved styling**: Existing colors and transformations from the input file remain intact
- **Smart automation**: All variations happen automatically based on input file metadata

## Conclusion

Outstanding work! :tada: You've transformed your basic karaoke system into a varied effect system. You've learned to leverage PyonFX's advanced features like actor-based theming, inline effect detection, and color preservation utilities.

In the next tutorial, we'll explore one of the PyonFX most powerful classes: the `Shape` class.

## Full Source Code
??? abstract "Show full source code"
    ```python
    --8<-- "examples/tutorials/2_intermediate/01_variations.py"
    ```