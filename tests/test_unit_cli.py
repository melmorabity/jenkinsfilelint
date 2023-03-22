# SPDX-FileCopyrightText: © 2023 Mohamed El Morabity
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
import os
import typing
from unittest import TestCase
import unittest.mock

import jenkinsfilelint.cli
from jenkinsfilelint.exceptions import ConfigError
from jenkinsfilelint.exceptions import JenkinsError

if typing.TYPE_CHECKING:
    from pathlib import Path


class TestCli(TestCase):
    def setUp(self) -> None:
        config_patch = unittest.mock.patch("jenkinsfilelint.cli.Config")
        self.config_mock = config_patch.start()
        self.addCleanup(config_patch.stop)

        jenkins_patch = unittest.mock.patch("jenkinsfilelint.cli.Jenkins")
        self.jenkins_mock = jenkins_patch.start()
        self.addCleanup(jenkins_patch.stop)

        # Set valid configuration
        self.config_mock.return_value.get.return_value = (
            "url",
            "username",
            "password",
        )

    def test_cli_config_error(self) -> None:
        # Force configuration failure
        exception_message = "Bad config"
        self.config_mock.side_effect = ConfigError(exception_message)

        with self.assertLogs(level="ERROR") as log_context:
            status = jenkinsfilelint.cli.main(["Jenkinsfile"])

        self.assertEqual(status, 1)
        self.assertIn(exception_message, log_context.output[0])

    def test_cli_jenkins_error(self) -> None:
        exception_message = "Bad config"
        self.jenkins_mock.side_effect = JenkinsError(exception_message)

        with self.assertLogs(level="ERROR") as log_context:
            status = jenkinsfilelint.cli.main(["Jenkinsfile"])

        self.assertEqual(status, 1)
        self.jenkins_mock.assert_called_with(
            "url", username="username", password="password", insecure=False
        )
        self.assertIn(exception_message, log_context.output[0])

    def test_cli_lint_ko(self) -> None:
        self.jenkins_mock.return_value.lint.side_effect = [True, False, True]

        self.assertEqual(jenkinsfilelint.cli.main(["jf1", "jf2", "jf3"]), 1)
        self.jenkins_mock.assert_called_with(
            "url", username="username", password="password", insecure=False
        )

    def test_cli_lint_error(self) -> None:
        exception_message = "Jenkins failure"
        self.jenkins_mock.return_value.lint.side_effect = [
            True,
            JenkinsError(exception_message),
            True,
        ]

        with self.assertLogs(level="ERROR") as log_context:
            status = jenkinsfilelint.cli.main(["jf1", "jf2", "jf3"])

        self.assertEqual(status, 1)
        self.jenkins_mock.assert_called_with(
            "url", username="username", password="password", insecure=False
        )
        self.assertIn(exception_message, log_context.output[0])

    def test_cli_lint_ok(self) -> None:
        self.jenkins_mock.return_value.lint.side_effect = [True, True, True]

        self.assertEqual(jenkinsfilelint.cli.main(["jf1", "jf2", "jf3"]), 0)
        self.jenkins_mock.assert_called_with(
            "url", username="username", password="password", insecure=False
        )

    @unittest.mock.patch.dict(
        os.environ,
        {
            "JENKINS_URL": "url2",
            "JENKINS_USERNAME": "username2",
            "JENKINS_PASSWORD": "password2",
        },
    )
    def test_cli_config_env(self) -> None:
        self.assertEqual(jenkinsfilelint.cli.main(["Jenkinsfile"]), 0)
        self.jenkins_mock.assert_called_with(
            "url2", username="username2", password="password2", insecure=False
        )

    def test_cli_debug(self) -> None:
        message = "Debug lint"

        def mock_jenkins_lint(
            _path: Path,
        ) -> bool:  # pylint: disable=used-before-assignment
            logging.getLogger().debug(message)
            return True

        self.jenkins_mock.return_value.lint.side_effect = mock_jenkins_lint

        with self.assertLogs(level="DEBUG") as log_context:
            status = jenkinsfilelint.cli.main(["--debug", "Jenkinsfile"])

        self.assertEqual(status, 0)
        self.assertIn(message, log_context.output[0])
