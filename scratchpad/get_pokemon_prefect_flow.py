from prefect import flow, task
import httpx

@task
def get_pokemon(name: str):
    response = httpx.get(f'https://pokeapi.co/api/v2/pokemon/{name}')
    return response.json()

@flow
def get_pokemon_flow():
    charizard = get_pokemon('charizard')
    print(charizard)

if __name__ == "__main__":
    get_pokemon_flow()
