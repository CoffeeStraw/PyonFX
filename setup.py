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
    url="https://github.com/CoffeeStraw/PyonFX",
    author="Antonio Strippoli",
    author_email="clarantonio98@gmail.com",
    version=find_version("pyonfx", "__init__.py"),
    license="GNU LGPL 3.0 or later",
    description="An easy way to do KFX and complex typesetting based on subtitle format ASS (Advanced Substation Alpha).",
    long_description=open("README.md", encoding="utf-8").read(),
    packages=["pyonfx"],
    install_requires=get_requirements(),
    extras_require={
        "dev": ["pytest", "pytest-check", "sphinx_rtd_theme", "sphinxcontrib-napoleon"]
    },
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
)
