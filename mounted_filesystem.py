import time
from pathlib import Path
from typing import Self

import docker
import docker.errors
from pydantic import BaseModel, Field, model_validator


class MountedDockerSandbox(BaseModel):
    """Interface to mount a container on some host scratchpad directory."""

    scratchpad: Path = Field(
        default=Path.cwd() / "scratchpad",
        description="A directory to store custom Python functions.",
    )

    docker_images: list[str] = Field(
        default_factory=lambda: ["prefect-sandbox"],
        min_length=1,
    )

    @property
    def docker_client(self) -> docker.DockerClient:
        return docker.from_env()

    @property
    def docker_tools(self) -> list:
        return [
            self.run_command,
            self.start_background_service,
            self.stop_background_service,
        ]

    @property
    def scripting_tools(self) -> list:
        return [
            self.create_or_update_scripts,
            self.delete_script,
            self.list_scripts,
        ]

    ### MODEL VALIDATORS ###

    @model_validator(mode="after")
    def ensure_scratchpad_exists(self) -> Self:
        """Ensure a directory named `path` exists."""
        if not self.scratchpad.exists():
            self.scratchpad.parent.mkdir(parents=True, exist_ok=True)
            self.scratchpad.mkdir()
        return self

    @model_validator(mode="after")
    def ensure_docker_image_ready(self) -> Self:
        """Ensure the Docker image exists. If not, build it from the Dockerfile."""
        try:
            self.docker_client.images.get(self.docker_images[0])
        except docker.errors.ImageNotFound:
            print(
                f"Docker image {self.docker_images[0]!r} not found locally. Building from Dockerfile..."
            )
            self.docker_client.images.build(path=".", tag=self.docker_images[0])
        return self

    def create_or_update_scripts(self, filename: str, body: str) -> str | None:
        """Write or rewrite a file in the scratchpad directory. These may be
        python scripts, yaml files, or markdown files (docker, k8s, docs, etc.)

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

    def delete_script(self, filename: str) -> str | None:
        """Delete a file from the scratchpad directory.

        Example:
        "delete the file named 'get_current_date_n_days_ago.py'"
        >>> delete_script("get_current_date_n_days_ago.py")
        """
        try:
            (self.scratchpad / f"{filename}").unlink()
        except Exception as e:
            return f"Failed to delete helper: {e}"

    def list_scripts(self, pattern: str = "*.py") -> list[str]:
        """List the names of all files in the scratchpad directory that match a pattern."""
        return [file.name for file in self.scratchpad.rglob(pattern)]

    def start_background_service(
        self, command: str, max_retries: int = 3, retry_interval: int = 2
    ) -> str:
        """Start a background service in the Docker container and ensure it's running.

        Example:
        "start a service that checks the price of ETH every 5 minutes"
        >>> start_background_service("python scratchpad/eth_price_checker.py") # runs blocking script
        """
        try:
            container = self.docker_client.containers.run(
                self.docker_images[0],
                command,
                volumes={
                    str(self.scratchpad.absolute()): {
                        "bind": "/app/scratchpad",
                        "mode": "ro",
                    }
                },
                detach=True,
            )

            # Wait for the container to start and check its status
            retry_count = 0
            while retry_count < max_retries:
                container.reload()
                if container.status == "running":
                    return f"Service started successfully with container ID: {container.id}"

                retry_count += 1
                time.sleep(retry_interval)

            # If the container is not running after max retries, stop and remove it
            container.stop()
            container.remove()
            return f"Failed to start background service after {max_retries} retries"

        except Exception as e:
            return f"Failed to start background service: {e}"

    def stop_background_service(self, container_id: str) -> str:
        """Stop a background service in the Docker container and ensure it's stopped.

        Example:
        "stop the service with container ID 123456789"
        >>> stop_background_service("123456789")
        """
        try:
            container = self.docker_client.containers.get(container_id)
            container.stop()

            # Wait for the container to stop and check its status
            container.reload()
            if container.status == "exited":
                container.remove()
                return f"Service stopped and container removed with ID: {container_id}"
            else:
                return f"Failed to stop background service with container ID: {container_id}"

        except Exception as e:
            return f"Failed to stop background service: {e}"

    def run_command(self, command: list[str], image: str | None = None) -> str:
        """Run any linux command (including Python scripts) in a sandboxed
        docker container with Prefect installed. All paths are RELATIVE to repo root.
        NEVER use absolute paths.

        Examples:
            >>> run_command(["python", "scratchpad/hello_world.py"]) # run existing py file

            >>> run_command(["cat", "scratchpad/hello_world.py"]) # view contents of existing file

            >>> run_command(["ls", "-l"]) # list files in current directory

            >>> run_command(["ls", "-l", "scratchpad"]) # list files in scratchpad directory

            >>> run_command(["prefect", "version"]) # check Prefect version

            >>> run_command(["prefect", "flow-run", "ls"]) # list all flow runs

        Returns:
            str: The output of the executed command.
        """
        try:
            result = self.docker_client.containers.run(
                image or self.docker_images[0],
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
