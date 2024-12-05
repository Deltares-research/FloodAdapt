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
