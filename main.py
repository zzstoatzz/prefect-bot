# /// script
# dependencies = ["marvin", "prefect", "raggy[tpuf]"]
# ///

"""An assistant that proofs out Prefect usage by running commands in a Docker container."""

import asyncio
import subprocess

import marvin
from marvin.beta.applications import Application
from pydantic import BaseModel, Field
from raggy.vectorstores.tpuf import TurboPuffer

from mounted_filesystem import MountedDockerSandbox

CLASSIFY_MODEL = EXTRACT_MODEL = "gpt-4o-2024-11-20"


class ExecutiveSummary(BaseModel):
    title: str = Field(description="a few word summary of the input")
    main_points: list[str] = Field(default_factory=list, description="key takeaways")


class Knapsack(MountedDockerSandbox):
    """Curated state useful for performing topic-related tasks.

    Includes tool implementations for:
    - researching topics and curating notes for future reference
    - running commands/scripts/containers/file IO in a sandboxed Docker environment # via MountedDockerSandbox
    """

    notes: list[str] = Field(
        default_factory=list,
        description="A place to keep useful nuggets of information based on past errors.",
        max_length=10,
    )

    topics: list[str] = Field(
        default_factory=list,
        description="Topics to read up on / curate information for.",
    )

    vector_namespace: str = Field(default="marvin-slackbot")

    async def research_a_topic(self, query: str, n_documents: int = 3) -> str:
        """Research a prefect-related concept. MUST be used before writing any code.

        Example:
        "how to write a prefect task"
        >>> research_a_topic("how to write a prefect task")
        """
        with TurboPuffer(namespace=self.vector_namespace) as tpuf:
            vector_result = tpuf.query(
                text=query,
                top_k=n_documents,
            )
            documents = [
                str(row.attributes["text"])
                for row in (vector_result.data or [])
                if (row and row.attributes and row.attributes["text"])
            ]

        most_relevant_excerpt, summaries = await asyncio.gather(  # type: ignore
            marvin.classify_async(
                data=f"here are the {self.notes=!r}\n\n and the query: {query}",
                labels=documents,
                model_kwargs={"model": CLASSIFY_MODEL},
            ),
            marvin.extract_async(
                data="\n".join(documents),
                model_kwargs={"model": EXTRACT_MODEL},
                target=ExecutiveSummary,
                instructions=f"given the following {self.notes=!r}\n\nsummarize documents related to: {query}",
            ),
        )

        return f"Relevant excerpt: {most_relevant_excerpt}\n\nSummaries: {summaries}"


if __name__ == "__main__":
    knapsack = Knapsack(  # knapsack is a pydantic model with a few extra methods
        notes=[
            "with Flow(...) as flow syntax is obsolete, use @flow to decorate a function instead.",
            "Agents are deprecated in favor of workers, which subscribe to work pools.",
            "One should always wrap an entrypoint in a `if __name__ == '__main__':` block.",
            "To persist data in the db, use `prefect server database reset -y` to create a new database.",
        ],
        topics=["Prefect deployment"],
    )
    with (
        Application(  # application is just an Assistant + a state (BaseModel/JSONable object)
            model="gpt-4o-2024-11-20",
            name="Prefect Code assistant",
            instructions=(
                "You are modern (3.12+) Prefect code copilot in a sandboxed (docker) environment. "
                "We are using a brand new version of Prefect so you MUST rely on `research_a_topic` "
                "in order to know valid Prefect syntax and imports. Never write code without research. "
                "Review https://docs.prefect.io/v3/deploy/run-flows-in-local-processes and "
                "https://docs.prefect.io/v3/resources/upgrade-agents-to-workers and take notes, but generally "
                "flows compose tasks and are each just decorated functions and you run them like normal functions, "
                "you don't need to actually create a deployment to run it and see stdout/stderr. "
                "Write, iterate, and test your code in the scratchpad directory using the provided tools. "
                "We may use any and all data engineering tools available to us: docker, k8s, etc."
                "If you repeatedly fail with the same error, stop and await further instructions. "
                "Remember to codify lessons learned in the `notes` and update `topics` as needed."
            ),
            state=knapsack,  # type: ignore
            tools=[
                knapsack.research_a_topic,
                *knapsack.scripting_tools,
                *knapsack.docker_tools,
            ],
        ) as app
    ):
        try:
            subprocess.run("prefect server start --background".split())
            app.chat(initial_message="write and run a basic flow")
        finally:
            subprocess.run("prefect server stop".split())
