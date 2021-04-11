# Contributing to PyonFX
Welcome to **PyonFX**!

If you intend to contribute to this project, please read following text carefully to avoid bad misunderstandings and wasted work. Contributions are appreciated but just under correct terms.

## Table of contents
1) [Introduction](#introduction)
2) [Expectations](#expectations)
3) [Style guideline](#style-guideline)
4) [What we're looking for](#what-were-looking-for)
5) [How to contribute](#how-to-contribute)
6) [Community](#community)

## Introduction
Please start by reading our [license](https://github.com/CoffeeStraw/PyonFX/blob/master/LICENSE) and [code-of-conduct](https://github.com/CoffeeStraw/PyonFX/blob/master/CODE_OF_CONDUCT.md). If you don't agree with them, this isn't your project.

For further questions, visit our [discord chat](https://discord.gg/Xxy3YAv).

## Expectations
* We're **mentoring** but just to a certain degree. An initial effort should have been done, training in programming basics or computer science isn't part of the offer. We want to speed up development, not slowing it down.
* **Quality** has priority, not getting fastly done. Faults by unnecessary hurry or sentences like "at least it works" are the opposite of "being welcome" here. Putting experiments on users is disrespectful for their time investment.
* Don't get emotional, act logical. **Personal taste** has to back off if there's no explanation why _xy_ makes more sense for others too. Let's combine the best of all!
* Contributing should happen as **teamwork**, not as competition. Join discussions, look through PRs and issues, merge compatible forks. Ignoring the progress of others leads to lost time (and motivation).

## Style guideline
* Continue present **conventions** and follow **best practices**. Don't break our pattern, code needs no multi-culture.
* **Comment &amp; document** your changes. Keep in mind others may work on same project parts too and don't want to spend much time understanding what you've done. 10 seconds you saved costs another contributor 10 minutes.
* **Include unit tests** when you contribute *new features*, as they help to a) prove that your code works correctly, and b) guard against future breaking changes to lower the maintenance cost.
* *Bug fixes* also generally require unit tests, because the presence of bugs usually indicates insufficient test coverage.
* **Format your code** using [black](https://github.com/psf/black).
* **Include a license** at the top of new files ([Python license example](https://github.com/CoffeeStraw/PyonFX/blob/master/pyonfx/ass_core.py#L1-L16)).

## What we're looking for
* Bugfixes
* Feature ideas
* Examples or tutorials
* Tests

## How to contribute
Main contribution ways are to [open issues](https://github.com/CoffeeStraw/PyonFX/issues) and [fork with later pull requests](https://github.com/CoffeeStraw/PyonFX/network/members). Furthermore you can discuss issues, review PRs or mention this project in public/chat with the community about your experience.

If you want to contribute with a pull request, please remember to:
* Install the PyonFX package in development mode with the command ``pip install -e .[dev]``. Packages included in ``dev`` allows you to run tests, format your code and generate documentation.
* Check if your changes are consistent with the [Style guideline](#style-guideline).
* Increase the version number in the [``__init__.py``](https://github.com/CoffeeStraw/PyonFX/blob/master/pyonfx/__init__.py) file. It follows the following setup: ``MainVersion.NewFeature.BugFixes``. This means that if your PR contains bux fixes, you must increment the final number. If you've added a new feature, increase the second number. You should never have to touch the first number, as 0 stands for "beta stage" and 1 for "release stage".

## Community
The community has a high value for this project!

As much as possible should be discussed in public, important decisions made by multiple individuals and people not getting excluded just because of a little dispute.