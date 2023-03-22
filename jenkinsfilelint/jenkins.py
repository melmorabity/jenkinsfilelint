# SPDX-FileCopyrightText: © 2023 Mohamed El Morabity
# SPDX-License-Identifier: GPL-3.0-or-later

"""Interact with a Jenkins instance for declarative pipeline linting."""

from __future__ import annotations

import re
import typing

from requests import RequestException
from requests import Session
from requests.auth import HTTPBasicAuth
import urllib3
from urllib3.exceptions import InsecureRequestWarning

from jenkinsfilelint.exceptions import JenkinsError

if typing.TYPE_CHECKING:  # pragma: no cover
    from pathlib import Path
    from types import TracebackType

    from requests import Response


class Jenkins:
    """A class for interacting with a Jenkins server to perform linting."""

    TIMEOUT = 30
    _CRUMB_PATH = (
        'crumbIssuer/api/xml?xpath=concat(//crumbRequestField,":",//crumb)'
    )
    _VALIDATOR_PATH = "pipeline-model-converter/validateJenkinsfile"
    _VALIDATOR_SUCCESS = "success"

    def __init__(
        self,
        url: str,
        username: str | None = None,
        password: str | None = None,
        insecure: bool = False,
        timeout: int = TIMEOUT,
    ) -> None:
        """Initialize a new instance of the Jenkins class.

        Args:
            url (str): The base URL of the Jenkins server.
            username (str | None, optional): The Jenkins username to use for
                authentication (if required). Defaults to `None`.
            password (str | None, optional): The Jenkins password to use for
                authentication (if required). Defaults to `None`.
            insecure (bool, optional): Whether to disable SSL verification for
                requests. Defaults to `False`.
            timeout (int, optional): Timeout from reading data from Jenkins
                instance. Defaults to `TIMEOUT`.
        """
        self._url = url.rstrip("/")

        self._session = Session()

        if username:
            self._session.auth = HTTPBasicAuth(username, password or "")

        self._session.verify = not insecure
        if insecure:
            urllib3.disable_warnings(InsecureRequestWarning)

        self._session.hooks["response"].append(
            lambda r, *_args, **_kwargs: r.raise_for_status()
        )

        self._timeout = timeout
        self._crumb = self._get_crumb()

    def _query(
        self,
        method: str,
        path: str,
        data: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        url = f"{self._url}/{path}"
        try:
            response = self._session.request(
                method, url, data=data, headers=headers, timeout=self._timeout
            )
        except RequestException as ex:
            raise JenkinsError(ex) from ex

        return response

    def _get_crumb(self) -> dict[str, str]:
        response = self._query("get", self._CRUMB_PATH)
        if not response.text.lower().startswith("jenkins-crumb:"):
            raise JenkinsError(
                f"Unable to retrieve crumb from {self._url}. Crumb issuer "
                "is probably blocked."
            )

        crumb = response.text.split(":")
        return {crumb[0].strip(): crumb[1].strip()}

    @staticmethod
    def _parse_error(message: str) -> tuple[int, int, str]:
        message_re = re.compile(
            r"^(?P<message>.*?)(:?\s*@ line\s*(?P<line>\d+), "
            r"column (?P<column>\d+)\.)?$",
            flags=re.DOTALL,
        )

        line = 1
        column = 1

        if match := message_re.match(message):
            message = match.group("message")
            if _line := match.group("line"):
                line = int(_line)
            if _column := match.group("column"):
                column = int(_column)

        message = re.sub(
            r"^Jenkinsfile content '.+' did not",
            "Jenkinsfile did not",
            message,
            flags=re.DOTALL,
        )

        return (line, column, message)

    def lint(self, path: Path) -> bool:
        """Validate a Jenkinsfile using the Jenkins Linter service.

        Args:
            path (Path): The path to the Jenkinsfile to be linted.

        Raises:
            JenkinsError: If an error occurs while communicating with the
                Jenkins instance.

        Returns:
            bool: `True` if the Jenkinsfile is valid; `False` otherwise.
        """
        try:
            jenkinsfile_reader = path.open("rb")
        except OSError as ex:
            raise JenkinsError(ex) from ex

        with jenkinsfile_reader:
            try:
                jenkinsfile_content = jenkinsfile_reader.read().decode()
            except UnicodeDecodeError as ex:
                raise JenkinsError(ex) from ex

        response = self._query(
            "post",
            self._VALIDATOR_PATH,
            data={"jenkinsfile": jenkinsfile_content},
            headers=self._crumb,
        )
        result = response.json()
        data = result.get("data") or {}

        _errors = [
            (*self._parse_error(message), level)
            for errors in (data.get("errors") or [])
            for level, messages in errors.items()
            for message in (
                messages if isinstance(messages, list) else [messages]
            )
        ]
        for line, column, error, level in sorted(_errors, key=lambda x: x[0]):
            print(f"{path}:{line}:{column}: {level}: {error}")

        status: str = result["data"]["result"]
        return status == self._VALIDATOR_SUCCESS

    def __enter__(self) -> Jenkins:
        """Enter the context manager and return the `Jenkins` object.

        Returns:
            Jenkins: The `Jenkins` object itself.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """_summary_.

        Args:
            exc_type (type[BaseException] | None): The type of the exception
                raised in the `with` block, if any.
            exc_value (BaseException | None): The value of the exception raised
                in the `with` block, if any.
            traceback (TracebackType | None): The traceback of the exception
                raised in the `with` block, if any.
        """
        if self._session:
            self._session.close()
