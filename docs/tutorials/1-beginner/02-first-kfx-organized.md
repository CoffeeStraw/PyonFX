# Tutorial: Organizing Your First KFX

Welcome back! In the previous tutorial, you created your first KFX, but I bet you noticed something: the code was getting pretty repetitive and hard to manage. When you're building real karaoke effects, you'll often work with dozens of lines and complex timing—having everything in one big loop becomes unwieldy fast.

In this tutorial, we'll refactor that same effect into clean, organized functions that are easier to read, debug, and reuse. You'll also discover some handy PyonFX utilities that make your code more robust.

## Materials

We'll continue working with the same [romaji_kanji_sub.ass](https://github.com/CoffeeStraw/PyonFX/blob/v1.0.0/examples/ass/romaji_kanji_sub.ass) file from the previous tutorial.

## Why Organize Your Code?

We encourage organizing your code because:

- **Clarity**: Giving each effect phase its own function keeps the logic easy to follow.
- **Debugging**: If something doesn't work as expected, you'll know exactly where to look.
- **Reusability**: Well-structured functions can be easily reused in other projects or combined in new ways.
- **Maintenance**: Isolating effects makes it much easier to tweak timing or styling down the road.

## Code Walkthrough

**0. Familiar Setup with New Imports**

We start similarly, but import a few more PyonFX components:

```python
from pyonfx import Ass, Line, Syllable, Utils

io = Ass("../../ass/romaji_kanji_sub.ass")
meta, styles, lines = io.get_data()
```

The new imports are:

- **`Line` and `Syllable`**: Type hints for our functions (makes code clearer)
- **`Utils`**: PyonFX's utility class

**1. Leadin Function**

Let's convert our three-phase effect into separate functions, starting with one for the leadin effect:

```python
def leadin_effect(line: Line, syl: Syllable, l: Line):
    l.layer = 0
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.start_time + syl.start_time

    tags = rf"\an5\pos({syl.center},{syl.middle})\fad({line.leadin // 2},0)"
    l.text = f"{{{tags}}}{syl.text}"

    io.write_line(l)
```

Notice the function signature—it takes the original `line`, current `syl`lable, and the copied line `l` as parameters. This makes the function completely self-contained and reusable.

**2. Enhanced Main Effect**

While moving our main effect to a separate function, let's also make it more robust:

```python
def main_effect(line: Line, syl: Syllable, l: Line):
    l.layer = 1
    l.start_time = line.start_time + syl.start_time
    l.end_time = line.start_time + syl.end_time

    # Original values
    c1 = line.styleref.color1
    c3 = line.styleref.color3
    fscx = line.styleref.scale_x
    fscy = line.styleref.scale_y

    # New values
    new_c1 = "&HFFFFFF&"
    new_c3 = "&HABABAB&"
    new_fscx = fscx * 1.25
    new_fscy = fscy * 1.25

    tags = (
        rf"\an5\pos({syl.center},{syl.middle})"
        rf"\t(0,{syl.duration // 2},\fscx{new_fscx}\fscy{new_fscy}\1c{new_c1}\3c{new_c3})"
        rf"\t({syl.duration // 2},{syl.duration},\fscx{fscx}\fscy{fscy}\1c{c1}\3c{c3})"
    )
    l.text = f"{{{tags}}}{syl.text}"

    io.write_line(l)
```

This version is much more robust because:

- **Dynamic scaling**: Instead of hardcoded `125%`, we multiply the original scale by `1.25`
- **Style-aware colors**: We extract colors from the line's style, then return to them
- **Clear variable names**: `c1`, `c3`, `fscx`, `fscy` make the ASS tags more readable

This means your effect will work correctly regardless of the original style settings.

**3. Leadout Function**

The leadout effect gets the same treatment:

```python
def leadout_effect(line: Line, syl: Syllable, l: Line):
    l.layer = 0
    l.start_time = line.start_time + syl.end_time
    l.end_time = line.end_time + line.leadout // 2

    tags = rf"\an5\pos({syl.center},{syl.middle})\fad(0,{line.leadout // 2})"
    l.text = f"{{{tags}}}{syl.text}"

    io.write_line(l)
```

**4. Introducing PyonFX Utilities**

Now let's use PyonFX's `Utils.all_non_empty()` to clean up our main loop:

```python
for line in Utils.all_non_empty(lines):
    if line.styleref.alignment >= 7:
        l = line.copy()
        for syl in Utils.all_non_empty(line.syls):
            leadin_effect(line, syl, l)
            main_effect(line, syl, l)
            leadout_effect(line, syl, l)
```

`Utils.all_non_empty()` is incredibly handy—it automatically:

- Skips commented lines and empty syllables (no more manual `if syl.text == "":` checks)
- Reassigns indexes (`i`, `word_i`, `syl_i`, ...) of the filtered objects
- Shows a progress bar while the iteration is in progress

Your code becomes cleaner and more robust with just one function call. For more details, check its documentation [here](../../reference/utils.md#pyonfx.utils.Utils.all_non_empty).

**5. Effect Tracking with Decorators**

PyonFX includes a powerful feature for tracking your effects. Add the `@io.track` decorator to each function:

```python
@io.track
def leadin_effect(line: Line, syl: Syllable, l: Line):
    # ... function code ...

@io.track
def main_effect(line: Line, syl: Syllable, l: Line):
    # ... function code ...

@io.track
def leadout_effect(line: Line, syl: Syllable, l: Line):
    # ... function code ...
```

When you run your script, you'll get detailed statistics for each effect:

??? abstract "Show Output"
    *(Pardon the output formatting, I promise it's better when you actually see it in the terminal)*
    ```python
    🐰 Produced lines: 135
    ⏱️ Total runtime: 0.1s (avg 0.001s per generated line)

    📊 STATISTICS
    ╭────────────────┬─────────┬─────────┬────────────┬────────────────╮
    │ Name           │   Calls │   Lines │   Time (s) │   Avg/Call (s) │
    ├────────────────┼─────────┼─────────┼────────────┼────────────────┤
    │ leadin_effect  │      45 │      45 │      0.001 │              0 │
    ├────────────────┼─────────┼─────────┼────────────┼────────────────┤
    │ main_effect    │      45 │      45 │      0.001 │              0 │
    ├────────────────┼─────────┼─────────┼────────────┼────────────────┤
    │ leadout_effect │      45 │      45 │          0 │              0 │
    ╰────────────────┴─────────┴─────────┴────────────┴────────────────╯
    ```

This is invaluable for debugging complex effects—you can see exactly how many lines each function generated and spot problems immediately.

**6. Final Result**

Save and preview your organized masterpiece:

```python
io.save()
io.open_aegisub()
```

The visual result is identical to the previous tutorial, but your code is now professional-grade: organized, maintainable, and scalable.

## Conclusion

Excellent work! :tada: You've transformed a functional but messy karaoke effect into clean, professional code. You've learned to break effects into logical functions, use PyonFX utilities to handle common tasks, and track your effects with decorators.

This organizational pattern will serve you well as effects become more complex. Up next, we'll also show some love to the kanji and translation lines.

## Full Source Code
??? abstract "Show full source code"
    ```python
    --8<-- "examples/tutorials/1_beginner/02_first_kfx_organized.py"
    ```