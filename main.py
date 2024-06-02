"""An assistant that proofs out Prefect usage by running commands in a Docker container."""

from pathlib import Path
from typing import Self

import docker
import docker.errors
from marvin.beta.applications import (
    Application,  # application is just an Assistant + a state dict
)
from pydantic import BaseModel, Field, PrivateAttr, model_validator
from raggy.vectorstores.tpuf import query_namespace


class Knapsack(BaseModel):
    """Curated state useful for performing prefect-related tasks.

    Includes tool implementations for:
    - reading/writing new Python files
    - researching Prefect concepts
    - running scripts/commands in a sandboxed Docker environment
    """

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

    _docker_image_name: str = PrivateAttr(default="prefect-sandbox")

    _namespace: str = PrivateAttr(
        default="marvin-slackbot",
    )

    def create_or_update_scripts(self, filename: str, body: str) -> None:
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
            ...     if __name__ == "__main__":
            ...         try:
            ...             n = int(sys.argv[1])
            ...             print(datetime.now().date() - timedelta(days=n))
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

    def delete_script(self, filename: str) -> None:
        """Delete a Python file from the scratchpad directory.

        Example:
        "delete the file named 'get_current_date_n_days_ago.py'"
        >>> delete_script("get_current_date_n_days_ago.py")
        """
        try:
            (self.scratchpad / f"{filename}").unlink()
        except Exception as e:
            return f"Failed to delete helper: {e}"

    async def research_prefect(self, query: str, n_documents: int = 3) -> list[str]:
        """Research a prefect-related concept. MUST be used before writing any code.

        Example:
        "how to write a prefect task"
        >>> research_prefect("how to write a prefect task")
        """
        return await query_namespace(
            query_text=query, top_k=n_documents, namespace=self._namespace
        )

    def run_command(self, command: list[str]) -> str:
        """Run any linux command (including Python scripts) in a sandboxed
        docker container with Prefect installed. All paths are RELATIVE to repo root.
        NEVER use absolute paths.

        Examples:
            run_command(["python", "scratchpad/hello_world.py"]) # run existing py file

            run_command(["cat", "scratchpad/hello_world.py"]) # view contents of existing file

            run_command(["ls", "-l"]) # list files in current directory

            run_command(["ls", "-l", "scratchpad"]) # list files in scratchpad directory

            run_command(["prefect", "version"]) # check Prefect version

            run_command(["prefect", "flow-run", "ls"]) # list all flow runs

        Returns:
            str: The output of the executed command.
        """
        client = docker.from_env()
        try:
            result = client.containers.run(
                self._docker_image_name,
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

    def list_scripts(self) -> list[str]:
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
    def ensure_docker_image_ready(self) -> Self:
        """Ensure the Docker image 'prefect-sandbox' exists. If not, build it from the Dockerfile."""
        client = docker.from_env()
        try:
            client.images.get(self._docker_image_name)
        except docker.errors.ImageNotFound:
            print(
                f"Docker image {self._docker_image_name!r} not found. Building from Dockerfile..."
            )
            client.images.build(path=".", tag="prefect-sandbox")
        return self


if __name__ == "__main__":
    my_bag = Knapsack()
    with Application(
        name="Prefect code assistant",
        instructions=(
            "Act as a Prefect code copilot in a sandboxed environment. "
            "We are using a brand new version of Prefect so you MUST rely on `research_prefect` "
            "in order to know valid Prefect syntax and imports. Never write code without research."
            "List, write and use custom Python functions to help you along the way. "
            "If you repeatedly fail with the same error, stop and await further instructions. "
            "Remember to codify lessons learned in the `notes` attribute when profound."
        ),
        state=my_bag,
        tools=[
            my_bag.research_prefect,
            my_bag.create_or_update_scripts,
            my_bag.delete_script,
            my_bag.run_command,
            my_bag.list_scripts,
        ],
    ) as app:
        app.chat(initial_message="what custom tools are available?")
