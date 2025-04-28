# Contributing guidelines

## Commit messages

In FloodAdapt we use the [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/#summary) specification. That means that commits which are going to end up in the main branch should have a message that conforms to the following format:

```
<type>[scope]: <title>

[description]
```

type can be one of the following:
- feat
- fix
- revert
- refactor
- ci
- dep
- doc
- test

and scope should be one of:
- adapters
- object-model
- dbs-controller
- dbs-builder
- api
- misc

For example the PR introducing the conventional commits reads like so:

```
feat(misc): Add linters and docs for using conventional commits

To enable automatic changelog generation and having a more uniform of recording the work done we are
introducing the use of conventional commits. There are docs on how to use this in CONTRIBUTING.md
and we added ci workflows to make sure we conform to the standard. PR titles and descriptions should conform
to the standard.
```

To make it easier for people to develop on their own branches, not each commit has to conform to this standard, but the
commit messages that end up in the main branch should. Since we only allow for squash merges, this means that you can
use whatever commit messages you want in your own branches. The PR title, and description will eventually become the messages
that end up in main. When you open a PR or edit its title/description a workflow should run that will check that the title and
description conforms to the standard.

## Changelog generation

For changelog generation we use [git cliff](https://github.com/orhun/git-cliff). As long as the conventional commit specification
is followed as specified above, this should happen automatically with every release. If you wish you can also generate them
locally by simply running `git cliff` if you have the tool installed.


# Releases

This section explains how to create new releases for the Python package and how the release process works.

---

## Workflow Overview

The [release workflow](.github/workflows/publish-to-pypi.yml) is triggered when a new tag is pushed to the repository in the format `v*.*.*` (e.g., `v1.2.3`). It performs the following steps:
1. Validates that the new version is greater than the latest version on PyPI.
2. Installs dependencies and builds the package.
3. Publishes the package to PyPI.
4. Creates a GitHub release with the tag name and release notes.

---

## Steps to Create a New Release

1. **Create a release branch**
```bash
git checkout main
git pull
git checkout -b feat/release-v123
```
2. **Increase the version in [`__init__.py`](flood_adapt/__init__.py)**
```python
__version__ = "1.2.3"
# Note that the v is excluded here
```

3. **Commit & Push**
```bash
git add .
git commit -m "bump version 1.2.3"
git push
```
4. **Create a PR, Review and Merge**

- By forcing these changes to go via a PR, we ensure that releases can only be made from code that passes all tests and has valid documentation.
- After having all status checks pass (tests & docs), you can merge the PR into main

5. **Create and push a new Tag**

Use the following commands to create a tag for the new version:
```bash
git tag v1.2.3
git push --tags

# Note that creating a tag is essentially like labeling a snapshot of your current local repository. So any other information/meta-data will be lost when people view the tag.

# i.e. it does not matter on which branch you are, just what your code looks like at the moment of running the above commands.
```

From here, the workflow should handle everything. You can find the latest release [here](https://github.com/Deltares/FloodAdapt/releases/latest).
