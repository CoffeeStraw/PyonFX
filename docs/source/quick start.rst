.. _quick-start:

Quick Start Guide
-----------------

First of all, you need to know how you're creating what. You will need to learn (if you've not already) the following:

* **ASS format**. PyonFX is still an advanced tool for typesetter and karaokers, it is meant to be used by experienced typesetters that knows all the tags rendered by Libass. Check the footnote [#f1]_ for a complete list of all the tags.
* **Python3 scripting language**. A programming language like Python offers you to define what you want in which case, how often, attended to this or that... Basically you're more free. You're not limited to buttons, sliders or text fields with just a few commands in a completely graphical interface. **The basics are enough**. Variables, functions, conditions, loops, comparisons, string formatting, list and dictionaries... You can find the link to some good tutorial in the footnote [#f2]_.

To start generating, you will only have to write, as written before, a script in Python3, which will describes the process of your KFX or advanced typesetting creation.

So, if you've not installed it before, you will have to **install Python3**.
You can **download** it from the `official website <https://www.python.org/downloads/>`_.
If you're on **Windows**, just be sure to check the box that says "Add Python 3.x to PATH". This is really important to avoid some extra steps to make Python callable from the command prompt.

If you still have trouble in the installation of Python, you can check some guide online, like https://realpython.com/installing-python/.

Installation
++++++++++++

Run this command below, which will use pip to install and eventually update the library::

    $ pip install --upgrade https://github.com/CoffeeStraw/PyonFX/zipball/master

That's all. Nothing else is needed, every time you will have to update, just run again this command.

Starting
++++++++

You may want to check if everything is working nicely now. For that, I suggest you to try running some of the examples in the `github official repository of the project <https://github.com/CoffeeStraw/PyonFX/tree/master/examples>`_.

To run a script in python, all you need to do is run the following command::

    $ python namefile.py

Or if this is not working for some reason (like you're not on Windows and both Python2 and Python3 are installed)::

    $ python3 namefile.py

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
.. [#f1] List of all ASS tags with usage explaination: http://docs.aegisub.org/3.2/ASS_Tags/
.. [#f2] Suggested tutorials for Python3 learning:
   
   * Italian: https://github.com/AllenDowney/ThinkPythonItalian/blob/master/thinkpython_italian.pdf
   * English: http://greenteapress.com/thinkpython2/thinkpython2.pdf