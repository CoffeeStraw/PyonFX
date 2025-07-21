---
title: Install & Set-up
---

## Prerequisites

To get started with PyonFX, we recommend that you have some knowledge on:
- **Python 3**: familiarity with basic constructs like variables, functions, conditions, loops, comparisons, string formatting, lists, and dictionaries[^py];
- **ASS/SSA Tags**: familiarity with primary tags. See the [ASS Tags Guide](https://aegisub.org/docs/latest/ass_tags/) for details.

## Installation

??? note "Windows"
    Download and install Python 3 from the [official website](https://www.python.org/downloads/). Ensure you check "Add Python 3.x to PATH". Then, install PyonFX:

    ```bash
    pip install --upgrade pyonfx
    ```

??? note "Ubuntu/Debian"
    Install prerequisites:

    ```bash
    sudo apt-get update
    sudo apt-get install libgirepository-2.0-dev gobject-introspection libcairo2-dev python3-dev build-essential gir1.2-gtk-3.0 python3-gi python3-gi-cairo
    ```

    Then, install PyonFX:

    ```bash
    python3 -m pip install --upgrade pyonfx
    ```

??? note "macOS"
    Install Homebrew if needed, then install prerequisites:

    ```bash
    brew install python py3cairo pygobject3 pango cairo glib
    ```

    Then, install PyonFX:

    ```bash
    python3 -m pip install --upgrade pyonfx
    ```

    If you encounter rendering issues, try:

    ```bash
    PANGOCAIRO_BACKEND=fc python3 namefile.py
    ```

??? note "Fedora"
    Install prerequisites:

    ```bash
    sudo dnf install python3 python3-pip gcc gobject-introspection-devel cairo-devel pkg-config python3-devel python3-gobject gtk3
    ```

    Then, install PyonFX:

    ```bash
    python3 -m pip install --upgrade pyonfx
    ```

    !!! warning
        Commands are not fully tested.

??? note "Arch Linux"
    - Via AUR: [python-pyonfx](https://aur.archlinux.org/packages/python-pyonfx)
    - Or manually:

    ```bash
    sudo pacman -S --needed python python-pip python-cairo python-gobject pango
    python -m pip install --upgrade pyonfx
    ```

??? note "OpenSUSE"
    Install prerequisites:

    ```bash
    sudo zypper install python3 python3-pip cairo-devel pkg-config python3-devel gcc gobject-introspection-devel python3-gobject python3-gobject-Gdk typelib-1_0-Gtk-3_0 libgtk-3-0
    ```

    Then, install PyonFX:

    ```bash
    python3 -m pip install --upgrade pyonfx
    ```

    !!! warning
        Commands are not fully tested.


### Additional Setup

Enhance your development workflow by setting up your environment as follows:

- Install Visual Studio Code for a feature-rich editing experience. Enable type hinting by installing the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) and, if desired, [Pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance) for enhanced type support;
- To automatically execute your Python script on save, install a 'Run on Save' extension such as [RunOnSave](https://marketplace.visualstudio.com/items?itemName=emeraldwalk.RunOnSave);
- Install the [MPV player](https://mpv.io/) for lightweight, hot-reload output preview without relying on Aegisub. On Windows, add the folder containing MPV’s executable (typically `C:\Program Files\mpv`) to your system PATH (if you don't know how, follow [this guide](https://www.architectryan.com/2018/03/17/add-to-the-path-on-windows-10/)).

## What's next

After completing these steps, continue with our [Your First Effect](your_first_effect.md) tutorial to begin creating your first effect.

[^py]: For beginners, see [Think Python 2](http://greenteapress.com/thinkpython2/thinkpython2.pdf) (English) or [Think Python Italian](https://github.com/AllenDowney/ThinkPythonItalian/blob/master/thinkpython_italian.pdf) (Italian) for additional Python resources. 