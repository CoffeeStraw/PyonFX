import setuptools
from pyonfx import __version__

setuptools.setup(
    name="PyonFX",
    url="https://github.com/CoffeeStraw/PyonFX",
    author="Antonio Strippoli",
    author_email="clarantonio98@gmail.com",
    version=__version__,
    license='GNU LGPL 3.0 or later',
    description="An easy way to do KFX and complex typesetting based on subtitle format ASS (Advanced Substation Alpha).",
    long_description=open('README.md').read(),
    packages=['pyonfx'],
    install_requires=["pywin32; sys_platform == \"Win32\""],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
)