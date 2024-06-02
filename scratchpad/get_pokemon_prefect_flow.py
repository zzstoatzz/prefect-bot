import sys
import httpx
from prefect import flow

@flow
def get_pokemon_info(pokemon_name: str):
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}"
    response = httpx.get(url)
    response.raise_for_status()
    pokemon = response.json()
    print(f"Name: {pokemon['name']}")
    print(f"Height: {pokemon['height']}")
    print(f"Weight: {pokemon['weight']}")
    print(f"Base Experience: {pokemon['base_experience']}")
    print(f"Types: {[t['type']['name'] for t in pokemon['types']]}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide the name of a Pokémon as an argument.")
        sys.exit(1)
    pokemon_name = sys.argv[1]
    get_pokemon_info(pokemon_name)