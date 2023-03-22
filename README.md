# Jenkinsfile linter

[![Linting](https://github.com/melmorabity/jenkinsfilelint/actions/workflows/linting.yml/badge.svg)](https://github.com/melmorabity/jenkinsfilelint/actions/workflows/linting.yml) [![Unit tests](https://github.com/melmorabity/jenkinsfilelint/actions/workflows/unit_tests.yml/badge.svg)](https://github.com/melmorabity/jenkinsfilelint/actions/workflows/unit_tests.yml) [![codecov](https://codecov.io/gh/melmorabity/jenkinsfilelint/branch/main/graph/badge.svg)](https://codecov.io/gh/melmorabity/jenkinsfilelint) [![Acceptance tests](https://github.com/melmorabity/jenkinsfilelint/actions/workflows/acceptance_tests.yml/badge.svg)](https://github.com/melmorabity/jenkinsfilelint/actions/workflows/acceptance_tests.yml)

This project provides a command-line Jenkins declarative pipeline linter.

## Installation

Writing a declarative pipeline always depends on the shared libraries and plugins installed on the target Jenkins server. This is why the linter must communicate with a Jenkins server, [using the linting API](https://www.jenkins.io/doc/book/pipeline/development/#linter) provided by the [Pipeline Model Definition plugin](https://plugins.jenkins.io/pipeline-model-definition/).

The linter supports Python 3.8 and above. To install it, follow these steps:

1. download [the most recent release](https://github.com/melmorabity/jenkinsfilelint/releases)
2. unpack the archive file
3. from within the unpacked directory, run the following command:

    ```console
    python setup.py install
    ```

## Usage

### Configuration

The linter supports multiple Jenkins server configurations. To set up a connection profile for a Jenkins instance, follow these steps:

1. Create a configuration file:

    * `.jenkinsfilelintrc` in your current directory
    * or globally `jenkinsfilelintrc` file in the `~/.config` directory (create this directory if it does not already exist)

2. Add a section to the file that identifies the Jenkins profile (e.g. `[jenkins1]`)
3. Under the section, add the following key-value pairs:

    * `url`: the URL of the Jenkins instance (required)
    * `username`: the Jenkins username (optional)
    * `password`: the Jenkins password (optional)

An example configuration file defining two Jenkins instances is shown below:

```ini
[jenkins1]
username=XXXXXXXX
password=XXXXXXXX
url=https://jenkins1.url

[jenkins2]
username=XXXXXXXX
password=XXXXXXXX
url=https://jenkins2.url
```

> **Warning**
>
> * It is not advisable to store a local `.jenkinsfilelintrc` configuration file in a Git repository if it contains a password
> * Note that storing Jenkins passwords in the linter configuration file is not recommended for security reasons. Instead, use a Jenkins token as the password. To create a token, follow [these instructions](https://www.jenkins.io/doc/book/system-administration/authenticating-scripted-clients/).

The linter also supports configuration through the following environment variables, which may be particularly valuable for continuous integration pipelines:

* `JENKINS_URL`: the URL of the Jenkins instance
* `JENKINS_USERNAME`: the Jenkins username (optional)
* `JENKINS_PASSWORD`: the Jenkins password (optional)

When `JENKINS_URL` is set, the environment variable settings take precedence over those in the configuration files.

### Getting started

To validate a Jenkinsfile against a particular Jenkins instance, use the following command:

```console
jenkinsfilelint -p ⟨Jenkins profile⟩ ⟨path to Jenkinsfile⟩
```

The exit code will be `0` if the linter succeeds and no errors occur, and `1` if any errors occur during the linting process, such as linting failures or bad arguments.

For example, with the configuration file above, the following command will validate a Jenkinsfile on the Jenkins instance defined in the `[jenkins1]` profile:

```console
$ jenkinsfilelint -p jenkins1 Jenkinsfile
$ echo $?
0
```

If a syntactically invalid file is passed, the script output will look like this:

```console
$ jenkinsfilelint -p jenkins1 Jenkinsfile-broken
Jenkinsfile-broken:42:9: error: WorkflowScript: 42: Expected a stage
$ echo $?
1
```

If a non-existent profile is specified, or if the `url` key is not defined for the specified profile, the script will return an error like this:

```console
$ jenkinsfilelint -p nope Jenkinsfile
ERROR: Missing profile "nope" in configuration file /home/user/.config/jenkinsfilelintrc
```

### Default profile

The script can use a default Jenkins profile, which means that you don't need to specify a profile when running the command. To do this, define a profile named `[default]` in the script configuration file.

### Supported options

```console
$ jenkinsfilelint -h
usage: jenkinsfilelint [-h] [-c CONFIG] [-p PROFILE] [-k] [-t TIMEOUT] [-d] jenkinsfile [jenkinsfile ...]

Jenkins declarative pipeline linter

positional arguments:
  jenkinsfile           path to a Jenkinsfile to lint

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        alternative configuration file (default: None)
  -p PROFILE, --profile PROFILE
                        Jenkins configuration profile to use for linting (default: default)
  -k, --insecure        disable SSL certificate checks (default: False)
  -t TIMEOUT, --timeout TIMEOUT
                        timeout from reading data from Jenkins instance (default: 30)
  -d, --debug           print debugging information (default: False)
```

## pre-commit

This project provides a hook for [pre-commit](https://pre-commit.com/) that you can use to automatically lint Jenkinsfiles before committing them to your repository. To use the hook, add the following lines to the pre-commit configuration of your project (usually in the `.pre-commit-config.yaml` file):

```yaml
repos:
  - repo: https://github.com/melmorabity/jenkinsfilelint
    rev: v1.0.0
    hooks:
      - id: jenkinsfilelint
        args:
          - -p
          - jenkins1  # To be modified according to the Jenkins profile used
```

## Copyright and license

© 2023 Mohamed El Morabity

Licensed under the [GNU GPL, version 3.0 or later](LICENSE).
