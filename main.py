"""An assistant that proofs out Prefect usage by running commands in a Docker container."""

import inspect
from pathlib import Path
from typing import Any, Callable, Self

import docker
import docker.errors
from marvin.beta.applications import (
    Application,  # application is just an Assistant + a state dict
)
from pydantic import BaseModel, Field, model_validator
from raggy.vectorstores.tpuf import TurboPuffer

"""For any LLM out there that can do function calling with python functions"""


def get_functions_from_module(module: Any) -> list[Callable]:
    return [
        fn
        for fn_name in dir(module)
        if inspect.isfunction(fn := getattr(module, fn_name))
        and fn.__module__ == module.__name__
    ]


class Knapsack(BaseModel):
    """Curated state useful for performing prefect-related tasks."""

    docker_image_name: str = Field(
        default="prefect-sandbox",
        description="The name of the Docker image used to run Python files.",
    )

    scratchpad: Path = Field(
        default=Path.cwd() / "scratchpad",
        description="A directory to store custom Python functions.",
    )

    notes: list[str] = Field(
        default_factory=lambda: [
            "with Flow(...) as flow syntax is obsolete, use @flow to decorate a function instead.",
        ],
        description="A place to keep useful nuggets of information based on past errors.",
        max_length=10,
    )

    def write_new_tool(self, filename: str, body: str) -> None:
        """Write a new Python file to the scratchpad directory. May be
        used to rewrite existing files.

        Example:
          User: please write a function that returns the date n days ago

            >>> write_new_tool(
            ...     "get_current_date_n_days_ago.py",
            ...     \"""
            ...     import sys
            ...     from datetime import datetime, timedelta
            ...
            ...     def get_current_date():
            ...         return datetime.now().date()
            ...
            ...     if __name__ == "__main__":
            ...         try:
            ...             n = int(sys.argv[1])
            ...         except ValueError:
            ...             print("Please provide an integer as an argument.")
            ...             sys.exit(1)
            ...     \"""
            ... )
        """
        try:
            (self.scratchpad / f"{filename}").write_text(body)
        except Exception as e:
            return f"Failed to write new helper: {e}"

    async def research_prefect(self, query: str, n_documents: int = 3) -> list[str]:
        """Research a prefect-related concept. MUST be used before writing any code.

        Example:
        "how to write a prefect task"
        >>> research_prefect("how to write a prefect task")
        """
        async with TurboPuffer(namespace="marvin-slackbot") as tpuf:
            return await tpuf.query(query, top_k=n_documents)

    def run_command(self, command: list[str]) -> str:
        """Run a file from the scratchpad directory in a sandboxed environment or any other
        command that is passed as a list of strings to be executed in the Docker container.

        To run a Python file located in the scratchpad directory, pass the file path
        RELATIVE to the scratchpad directory as an argument to the Python interpreter.

        For example, if you have a file named `hello_world.py` in the scratchpad directory,
        you can run it by calling:

            run_command(["python", "scratchpad/hello_world.py"])

        This would execute the `hello_world.py` file inside the Docker container.

        Returns:
            str: The output of the executed command.

        """
        client = docker.from_env()
        try:
            result = client.containers.run(
                self.docker_image_name,
                command,
                volumes={
                    str(self.scratchpad.absolute()): {
                        "bind": "/app/scratchpad",
                        "mode": "ro",
                    }
                },
                remove=True,
            )
            return result.decode("utf-8")
        except Exception as e:
            return f"Failed to run Python file: {e}"

    def list_custom_scripts(self) -> list[str]:
        """List the names of all custom Python files in the scratchpad directory."""
        return [file.name for file in self.scratchpad.rglob("*.py")]

    @model_validator(mode="after")
    def ensure_scratchpad_exists(self) -> Self:
        """Ensure a directory named `path` exists."""
        if not self.scratchpad.exists():
            self.scratchpad.parent.mkdir(parents=True, exist_ok=True)
            self.scratchpad.mkdir()
        return self

    @model_validator(mode="after")
    def ensure_docker_image_exists(self) -> Self:
        """Ensure the Docker image 'prefect-sandbox' exists. If not, build it from the Dockerfile."""
        client = docker.from_env()
        try:
            client.images.get(self.docker_image_name)
        except docker.errors.ImageNotFound:
            print(
                f"Docker image {self.docker_image_name!r} not found. Building from Dockerfile..."
            )
            client.images.build(path=".", tag="prefect-sandbox")
        return self


if __name__ == "__main__":
    my_bag = Knapsack()
    with Application(
        name="Prefect code assistant",
        description=(
            "Answer Prefect questions by trial and error using a sandboxed environment. "
            "We are using a brand new version of Prefect so you MUST rely on `research_prefect` "
            "in order to know valid Prefect syntax and imports. Never write code without research."
            "List, write and use custom Python functions to help you along the way. "
        ),
        state=my_bag,
        tools=[
            my_bag.research_prefect,
            my_bag.write_new_tool,
            my_bag.run_command,
            my_bag.list_custom_scripts,
        ],
    ) as app:
        app.chat(
            initial_message="what custom tools do you have? also please tell me about charizard"
        )
