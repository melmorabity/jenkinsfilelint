# SPDX-FileCopyrightText: © 2023 Mohamed El Morabity
# SPDX-License-Identifier: GPL-3.0-or-later

"""Provide a command-line interface to the linter."""

from __future__ import annotations

from argparse import ArgumentDefaultsHelpFormatter
from argparse import ArgumentParser
import logging
import os
from pathlib import Path

from jenkinsfilelint.config import Config
from jenkinsfilelint.exceptions import LinterError
from jenkinsfilelint.jenkins import Jenkins

logging.basicConfig(format="%(levelname)s: %(message)s")


def _argument_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Jenkins declarative pipeline linter",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-c", "--config", type=Path, help="alternative configuration file"
    )
    parser.add_argument(
        "-p",
        "--profile",
        default=Config.DEFAULT_PROFILE,
        help="Jenkins configuration profile to use for linting",
    )
    parser.add_argument(
        "-k",
        "--insecure",
        default=False,
        action="store_true",
        help="disable SSL certificate checks",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=Jenkins.TIMEOUT,
        help="timeout from reading data from Jenkins instance",
    )
    parser.add_argument(
        "-d",
        "--debug",
        default=False,
        action="store_true",
        help="print debugging information",
    )
    parser.add_argument(
        "jenkinsfile",
        nargs="+",
        type=Path,
        help="path to a Jenkinsfile to lint",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the command-line interface.

    Args:
        argv (list[str] | None, optional): Command-line arguments. Defaults to
            `None`.

    Returns:
        int: The status code for the CLI.
    """
    parser = _argument_parser()
    args = parser.parse_args(argv)

    logging.getLogger().setLevel(
        logging.DEBUG if args.debug else logging.ERROR
    )

    if url := os.environ.get("JENKINS_URL"):
        logging.debug("Loading configuration from environment variables")
        username = os.environ.get("JENKINS_USERNAME")
        password = os.environ.get("JENKINS_PASSWORD")
    else:
        try:
            url, username, password = Config(args.config).get(args.profile)
        except LinterError as ex:
            logging.error(ex)
            return 1

    try:
        jenkins = Jenkins(
            url, username=username, password=password, insecure=args.insecure
        )
    except LinterError as ex:
        logging.error(ex)
        return 1

    status = True
    with jenkins:
        for path in args.jenkinsfile:
            try:
                status &= jenkins.lint(path)
            except LinterError as ex:  # noqa: PERF203
                status &= False
                logging.error(ex)

    return 0 if status else 1
