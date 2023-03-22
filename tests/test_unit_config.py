# SPDX-FileCopyrightText: © 2023 Mohamed El Morabity
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import TestCase

from jenkinsfilelint.config import Config
from jenkinsfilelint.exceptions import ConfigError


class TestConfig(TestCase):
    def test_config_not_exists(self) -> None:
        path = Path("/no/file/here")
        with self.assertRaises(ConfigError) as context:
            Config(path)

        self.assertEqual(
            f"Unable to load configuration file {path}", str(context.exception)
        )

    def test_config_not_ini(self) -> None:
        with NamedTemporaryFile() as config_file:
            config_file.write(b"Not an INI file")
            config_file.seek(0)

            with self.assertRaises(ConfigError) as context:
                Config(Path(config_file.name))

        self.assertIn(
            "File contains no section headers", str(context.exception)
        )

    def test_config_valid_default_profile(self) -> None:
        url = "https://example.net"
        username = "username"
        password = "password"  # nosec
        config = (
            "[default]\n"
            f"url = {url}\n"
            f"username = {username}\n"
            f"password = {password}"
        )
        with NamedTemporaryFile() as config_file:
            config_file.write(config.encode())
            config_file.seek(0)

            linter_config = Config(Path(config_file.name))
            result = linter_config.get()

        self.assertEqual(result, (url, username, password))

    def test_config_valid_custom_profile(self) -> None:
        profile = "custom"
        url = "https://example.net"
        username = "username"
        password = "password"  # nosec
        config = (
            f"[{profile}]\n"
            f"url = {url}\n"
            f"username = {username}\n"
            f"password = {password}"
        )
        with NamedTemporaryFile() as config_file:
            config_file.write(config.encode())
            config_file.seek(0)

            linter_config = Config(Path(config_file.name))
            result = linter_config.get(profile=profile)

        self.assertEqual(result, (url, username, password))

    def test_config_valid_minimal(self) -> None:
        profile = "custom"
        url = "https://example.net"
        config = f"[{profile}]\nurl = {url}\n"
        with NamedTemporaryFile() as config_file:
            config_file.write(config.encode())
            config_file.seek(0)

            linter_config = Config(Path(config_file.name))
            result = linter_config.get(profile=profile)

        self.assertEqual(result, (url, None, None))

    def test_config_invalid_missing_profile(self) -> None:
        config = (
            "[default]\n"
            "url = https://example.net\n"
            "username = username\n"
            "password = password"
        )
        with NamedTemporaryFile() as config_file:
            config_file.write(config.encode())
            config_file.seek(0)

            linter_config = Config(Path(config_file.name))
            with self.assertRaises(ConfigError):
                linter_config.get(profile="custom")

    def test_config_invalid_missing_url(self) -> None:
        config = "[custom]\nusername = username\npassword = password"
        with NamedTemporaryFile() as config_file:
            config_file.write(config.encode())
            config_file.seek(0)

            linter_config = Config(Path(config_file.name))
            with self.assertRaises(ConfigError):
                linter_config.get(profile="custom")
