.. _quick-start:

Quick Start Guide
-----------------

First of all, you need to know how you're creating what. You will need to learn (if you've not already) the following:

* **ASS format**. PyonFX is still an advanced tool for typesetter and karaokers, it is meant to be used by experienced typesetters that knows all the tags rendered by Libass. Check the footnote [#f1]_ for a complete list of all the tags.
* **Python3 scripting language**. A programming language like Python offers you to define what you want in which case, how often, attended to this or that... Basically you're more free. You're not limited to buttons, sliders or text fields with just a few commands in a completely graphical interface. **The basics are enough**. Variables, functions, conditions, loops, comparisons, string formatting, list and dictionaries... You can find the link to some good tutorials in the footnote [#f2]_.

To start generating, you will only have to write a script in Python3, which will describes the process of your KFX or advanced typesetting creation.

If you have trouble with the installation of Python, you can check some online guide, like https://realpython.com/installing-python/.

Windows
+++++++

So, if you've not installed it before, you will have to **install Python3**.
You can **download** it from the `official website <https://www.python.org/downloads/>`_.
Just be sure to check the box that says "Add Python 3.x to PATH". This is really important to avoid some extra steps that would make Python callable in every directory from the command prompt.


Run this command below, which will use pip to install and eventually update the library:

.. code-block:: sh
   :emphasize-lines: 1

   pip install --upgrade https://github.com/CoffeeStraw/PyonFX/zipball/master

That's all. Nothing else is needed, every time you will have to update, just run again this command.

Ubuntu/Debian
+++++++++++++

Warning: The first of the following commands is not well tested. If you run into any problems, please create an issue or refer to the `official installation guide <https://pygobject.readthedocs.io/en/latest/getting_started.html>`_.

.. code-block:: sh
   :emphasize-lines: 1,2
   
   sudo apt install python3 python3-pip libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0 python3-gi python3-gi-cairo
   python3 -m pip install --upgrade https://github.com/CoffeeStraw/PyonFX/zipball/master

Fedora
++++++

Warning: The first of the following commands is not well tested. If you run into any problems, please create an issue or refer to the `official installation guide <https://pygobject.readthedocs.io/en/latest/getting_started.html>`_.

.. code-block:: sh
   :emphasize-lines: 1,2
   
   sudo dnf install python3 python3-pip gcc gobject-introspection-devel cairo-devel pkg-config python3-devel python3-gobject gtk3
   python3 -m pip install --upgrade https://github.com/CoffeeStraw/PyonFX/zipball/master

Arch Linux
++++++++++

Warning: The first of the following commands is not well tested. If you run into any problems, please create an issue or refer to the `official installation guide <https://pygobject.readthedocs.io/en/latest/getting_started.html>`_.

.. code-block:: sh
   :emphasize-lines: 1,2
   
   sudo pacman -S python python-pip cairo pkgconf gobject-introspection python-gobject gtk3
   python3 -m pip install --upgrade https://github.com/CoffeeStraw/PyonFX/zipball/master

openSUSE
++++++++

Warning: The first of the following commands is not well tested. If you run into any problems, please create an issue or refer to the `official installation guide <https://pygobject.readthedocs.io/en/latest/getting_started.html>`_.

.. code-block:: sh
   :emphasize-lines: 1,2
   
   sudo zypper install python3 python3-pip cairo-devel pkg-config python3-devel gcc gobject-introspection-devel python3-gobject python3-gobject-Gdk typelib-1_0-Gtk-3_0 libgtk-3-0
   python3 -m pip install --upgrade https://github.com/CoffeeStraw/PyonFX/zipball/master

macOS
+++++

You may need to install `Homebrew <https://brew.sh/>`_ first.

Warning: The first of the following commands is not well tested. If you run into any problems, please create an issue or refer to the `official installation guide <https://pygobject.readthedocs.io/en/latest/getting_started.html>`_.

.. code-block:: sh
   :emphasize-lines: 1,2
   
   brew install pygobject3 gtk+3 cairo py3cairo pkg-config
   python3 -m pip install --upgrade https://github.com/CoffeeStraw/PyonFX/zipball/master

Warning: If you have font issues, you might need to change the PangoCairo backend to fontconfig.

.. code-block:: sh
   :emphasize-lines: 1
   
   PANGOCAIRO_BACKEND=fc python3 namefile.py


Installation - Extra Step
+++++++++++++++++++++++++

This step is not needed to start working with the library, but personally I consider Aegisub quite old and heavy, so I needed a more comfortable way to work.

That's why PyonFX integrates an additional way to reproduce your works in softsub faster after each generation, using the `MPV player <https://mpv.io/>`_. Installing it should be enough to make everything work if your're NOT on Windows.

If you're on Windows, all you need to do once you have installed it (check the website for that), is to add it to the PATH, so that the library will be able to utilize it. There are several guide for that, `here you can find one <https://www.architectryan.com/2018/03/17/add-to-the-path-on-windows-10/>`_.

You need to add the folder that contains the .exe of mpv, generally C:\\Program Files\\mpv.


Starting
++++++++

You may want to check if everything is working nicely now. For that, I suggest you to try running some of the examples in the `GitHub official repository of the project <https://github.com/CoffeeStraw/PyonFX/tree/master/examples>`_.

To run a script in python, all you need to do is run the following command:

.. code-block:: sh
   :emphasize-lines: 1

   python namefile.py

Or if this is not working for some reason (like you're not on Windows and both Python2 and Python3 are installed):

.. code-block:: sh
   :emphasize-lines: 1

   python3 namefile.py

I highly suggest you to generate and study every single example in this examples folder (download always up-to-date `here <https://minhaskamal.github.io/DownGit/#/home?url=https://github.com/CoffeeStraw/PyonFX/tree/master/examples>`_). These are meant for absolute beginners until advanced users and explain in detail the usage of all the relevant functions of the library.

Tips
++++

* Don't make a KFX in one go. Make pauses, go for a walk, collect ideas from your surroundings;
* Pick elements of the video. Your effect should merge with the background in some manner;
* Consider human recognition. Mostly we notice motion, then contrasts, then colors. Too much can give a headache, too less is boring;
* Use modern styles to impress (light, curves, particles, gradients) and old ones for readability (solid colors, thick borders, static positions);
* When background is too flashy, try to insert a panel shape to put your text on 'safe terrain';
* Adjust to karaoke times and voice. Fast sung lines haven't syllable durations for effects which need some time to get seen.

----------

.. rubric:: Footnotes
.. [#f1] List of all ASS tags with usage explanation: http://docs.aegisub.org/3.2/ASS_Tags/
.. [#f2] Suggested tutorials for learning Python3:
   
   * Italian: https://github.com/AllenDowney/ThinkPythonItalian/blob/master/thinkpython_italian.pdf
   * English: http://greenteapress.com/thinkpython2/thinkpython2.pdf
