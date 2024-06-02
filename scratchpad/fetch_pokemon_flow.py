import sys
from prefect import flow, task
import httpx

@task(retries=3, retry_delay_seconds=10)
def fetch_pokemon_batch(batch_size: int) -> list:
    url = "https://pokeapi.co/api/v2/pokemon"
    response = httpx.get(url, params={"limit": batch_size})
    response.raise_for_status()
    return response.json()["results"]

@flow(name="Fetch Pokemon Flow")
def get_pokemon(total: int, batch_size: int):
    batches = [batch_size] * (total // batch_size)
    all_pokemon_futures = fetch_pokemon_batch.map(batches)
    all_pokemon = [future.result() for future in all_pokemon_futures]  # resolve futures
    pokemon_names = [pokemon["name"] for batch in all_pokemon for pokemon in batch]
    return len(pokemon_names)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python fetch_pokemon_flow.py <total_pokemon> <batch_size>")
        sys.exit(1)
    total_pokemon = int(sys.argv[1])
    batch_size = int(sys.argv[2])
    total_fetched = get_pokemon.with_options(
        name=f"Fetch Pokemon Flow - Batch size {batch_size}"
    )(total=total_pokemon, batch_size=batch_size)
    print(f"Total Pokémon fetched: {total_fetched}")