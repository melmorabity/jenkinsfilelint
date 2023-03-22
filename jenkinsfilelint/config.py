# SPDX-FileCopyrightText: © 2023 Mohamed El Morabity
# SPDX-License-Identifier: GPL-3.0-or-later

"""Provide configuration management for the linter."""

from __future__ import annotations

from configparser import ConfigParser
from configparser import Error
from pathlib import Path
from typing import ClassVar

from jenkinsfilelint.exceptions import ConfigError


class Config:
    """A class to manage configuration for the Jenkinsfile linter."""

    _DEFAULT_CONFIG_PATHS: ClassVar[list[Path]] = [
        Path.cwd() / ".jenkinsfilelintrc",
        Path.home() / ".config" / "jenkinsfilelintrc",
    ]
    DEFAULT_PROFILE = "default"

    def __init__(self, path: Path | None = None) -> None:
        """Initialize a new instance of the `LinterConfig` class.

        Args:
            path (Path, optional): The path to the linter configuration file.
                Defaults to `DEFAULT_CONFIG_PATH`.

        Raises:
            ConfigError: If the configuration file cannot be opened or if there
                is an error parsing the configuration file.
        """
        self._config_parser = ConfigParser()

        paths = [
            str(p) for p in ([path] if path else self._DEFAULT_CONFIG_PATHS)
        ]

        try:
            self._path = self._config_parser.read(paths).pop()
        except IndexError:
            msg = (
                f"Unable to load configuration file{'s'[:len(paths) ^ 1]} "
                f"{' or '.join(paths)}"
            )
            raise ConfigError(msg) from None
        except Error as ex:
            raise ConfigError(ex) from ex

    def get(
        self, profile: str = DEFAULT_PROFILE
    ) -> tuple[str, str | None, str | None]:
        """Get Jenkins server information from a configuration profile.

        Args:
            profile (str, optional): The Jenkins profile to use. Defaults to
                `DEFAULT_PROFILE`.

        Raises:
            ConfigError: If the specified profile is missing from the
                configuration file or if a required key is missing.

        Returns:
            tuple[str, str | None, str | None]: A tuple containing the
                URL of the Jenkins server, and the username and password if
                provided.
        """
        if not self._config_parser.has_section(profile):
            msg = (
                f"Missing profile `{profile}` in configuration file "
                f"{self._path}"
            )
            raise ConfigError(msg)

        if not (url := self._config_parser[profile].get("url")):
            msg = (
                f"Missing `url` key for profile `{profile}` in configuration "
                f"file {self._path}"
            )
            raise ConfigError(msg)

        username = self._config_parser[profile].get("username")
        password = self._config_parser[profile].get("password")

        return (url, username, password)
