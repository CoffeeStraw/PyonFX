---
tags:
  - Quick Start
  - Installation
  - Python
  - PyonFX
---
# Quick Start Guide

First things first, you must have a good idea of how to create your effects. You will need to learn (if you haven't already) the following:

* **ASS format**. As PyonFX is an advanced tool for typesetting and karaoke, it is meant to be used by experienced typesetters who are familiar with the tags Libass supports, as well as how they function. Check the footnote [^1] for a complete list of tags.
* **Python3 scripting language**. A programming language like Python allows you to define a set of instructions to be executed by your computer. Compared to softwares with GUI it gives you much more freedom, as you aren't tied to buttons or sliders. **You only need to know the basics for this module**. Knowledge on how to use variable, functions, conditions, loops, comparisons, string formatting, lists, and dictionaries is more than enough. You can find a link to some good tutorials in the footnotes [^2].

To use PyonFX, you'll have to write a Python3 script. Within it you will fully define the process of your KFX or advanced typesetting creation.

If you don't know how to install Python3, there are resources online that can help you out, like [Installing Python](https://realpython.com/installing-python/).

## Installation

### Windows

If you haven't installed it yet, make sure to **install** Python3.
You can **download** it from the [official website](https://www.python.org/downloads/).
Make sure you check the box that says "Add Python 3.x to PATH". This is very important to avoid some extra steps that would make Python callable in every directory from the command prompt.

Run the following command below. It will use pip to install and update the library:
```bash
pip install --upgrade pyonfx
```

That's all you need to do for now. If you need to update this library at a later date, run that same command again.

### Ubuntu/Debian

> ⚠️ **Warning:** The following commands are not well tested. If you run into any problems, please create an issue or refer to the [official installation guide](https://pygobject.readthedocs.io/en/latest/getting_started.html).

```bash
sudo apt install python3 python3-pip libgirepository-2.0-dev gobject-introspection libcairo2-dev build-essential gir1.2-gtk-3.0 python3-gi python3-gi-cairo
python3 -m pip install --upgrade pyonfx
```

### Fedora

> ⚠️ **Warning:** The following commands are not well tested.

```bash
sudo dnf install python3 python3-pip gcc gobject-introspection-devel cairo-devel pkg-config python3-devel python3-gobject gtk3
python3 -m pip install --upgrade pyonfx
```

### Arch Linux

For Arch Linux, you can install via AUR: [python-pyonfx](https://aur.archlinux.org/packages/python-pyonfx). Alternatively, for manual installation:

```bash
paru -S python-pyonfx
```

or

```bash
sudo pacman -S --needed python python-pip python-cairo python-gobject pango
python -m pip install --upgrade pyonfx
```

### OpenSUSE

> ⚠️ **Warning:** The following commands are not well tested.

```bash
sudo zypper install python3 python3-pip cairo-devel pkg-config python3-devel gcc gobject-introspection-devel python3-gobject python3-gobject-Gdk typelib-1_0-Gtk-3_0 libgtk-3-0
python3 -m pip install --upgrade pyonfx
```

### macOS

You may need to install [Homebrew](https://brew.sh/) first.

> ⚠️ **Warning:** The following commands are not well tested.

```bash
brew install python py3cairo pygobject3 pango cairo glib
python3 -m pip install --upgrade pyonfx
```

If output is not rendered correctly, you might need to change the `PANGOCAIRO_BACKEND`:

```bash
PANGOCAIRO_BACKEND=fc python3 namefile.py
```

## Installation - Extra Step

This step is not mandatory to start working with the library, but I personally consider Aegisub to be quite old and heavy, so I needed a more comfortable work setup.

That's why PyonFX integrates an additional way to reproduce your works in softsub faster after each generation, using the [MPV player](https://mpv.io/). Installing it should be enough to make everything work if you're **not** on Windows.

If you're on Windows, you will need to add it to PATH after downloading it so the library will be able to utilize it. There are several guides for that, [like this one](https://www.architectryan.com/2018/03/17/add-to-the-path-on-windows-10/).

You need to add the folder that contains the .exe of mpv, generally '*C:\\Program Files\\mpv*'.

## Starting Out

Before starting, you may want to make sure everything works as intended. I suggest you to try running some of the examples in the `official GitHub repository of the project <https://github.com/CoffeeStraw/PyonFX/tree/master/examples>`_.

To run a script in python, execute the following command:
```bash
python namefile.py
```

Or if this for some reason doesn't work (like if you're not on Windows and both Python2 and Python3 are installed):
```bash
python3 namefile.py
```

I highly suggest you generate and study every single example in the examples folder (download always up-to-date [here](https://minhaskamal.github.io/DownGit/#/home?url=https://github.com/CoffeeStraw/PyonFX/tree/master/examples)). These are meant to help out beginners to advanced users by explaining all the relevant functions of the library and how they work in detail.

## Tips

- Don't make KFX in one go. Take breaks, go for a walk, obtain inspiration from your surroundings;
- Pick elements of the video. Your effects should ideally blend in with the video;
- Consider human recognition. Humans notice motion first, then contrasts, then colors. Too much of any of this can result in headaches, but too little can be boring to look at;
- Use modern styles to impress (light, curves, particles, gradients) and old ones for readability (solid colors, thick borders, static positions);
- When backgrounds are too flashy, try to insert a panel shape to put your text on 'safe terrain';
- Adjust to karaoke timing and voice. Fast sung lines will have very short syllable durations for effects, and may not always be visible.

[^1]: [ASS Tags Guide](https://aegisub.org/docs/latest/ass_tags/)
[^2]: Tutorials for Python3:
    
    - English: [Think Python 2](http://greenteapress.com/thinkpython2/thinkpython2.pdf)
    - Italian: [Think Python Italian](https://github.com/AllenDowney/ThinkPythonItalian/blob/master/thinkpython_italian.pdf)
