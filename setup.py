import os
import re
import setuptools

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    with open(os.path.join(here, *parts), "r") as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = [\'\"](.+)[\'\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


def get_requirements():
    requirements = ["pyquaternion"]

    if os.environ.get("READTHEDOCS") != "True":
        requirements.extend(
            [
                'pywin32; sys_platform == "win32"',
                'pycairo; sys_platform == "linux" or sys_platform == "darwin"',
                'PyGObject; sys_platform == "linux" or sys_platform == "darwin"',
            ]
        )

    return requirements


setuptools.setup(
    name="pyonfx",
    url="https://github.com/CoffeeStraw/PyonFX/",
    project_urls={
        "Documentation": "http://pyonfx.rtfd.io/",
        "Source": "https://github.com/CoffeeStraw/PyonFX/",
        "Tracker": "https://github.com/CoffeeStraw/PyonFX/issues/",
    },
    author="Antonio Strippoli",
    author_email="clarantonio98@gmail.com",
    description="An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    version=find_version("pyonfx", "__init__.py"),
    packages=["pyonfx"],
    python_requires=">=3.7",
    install_requires=get_requirements(),
    extras_require={
        "dev": [
            "black",
            "pytest",
            "pytest-check",
            "sphinx_panels",
            "sphinx_rtd_theme",
            "sphinxcontrib-napoleon",
        ]
    },
    keywords="typesetting ass subtitle aegisub karaoke kfx advanced-substation-alpha karaoke-effect",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
    ],
    license="GNU LGPL 3.0 or later",
)
