# SPDX-FileCopyrightText: © 2023 Mohamed El Morabity
# SPDX-License-Identifier: GPL-3.0-or-later

"""Provide exceptions for the linter."""


class LinterError(Exception):
    """Base class for exceptions raised by the linter."""


class JenkinsError(LinterError):
    """Raised if an error occurs while communicating with a Jenkins server."""


class ConfigError(LinterError):
    """Raised if linter configuration file cannot be opened or parsed."""
