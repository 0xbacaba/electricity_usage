import json
import requests
import os
import converter

from dotenv import load_dotenv
from dateutil import parser

from settings import API, ENTITY_IDS, START_TIME, END_TIME, COST, FULL_FEED_IN_TARIFF, PARTIAL_FEED_IN_TARIFF

if not load_dotenv():
    print("Failed to load .env, trying to continue anyways...")

END_TIME_URLENCODED = requests.utils.quote(END_TIME)
RAW_ENTITY_IDS = ",".join(ENTITY_IDS.keys())

ENDPOINT = f"{API}/history/period/{START_TIME}?filter_entity_id={ENTITY_IDS}&minimal_response=true&end_time={END_TIME_URLENCODED}"

def fetch_data(csv_file: str, cache_file: str):
    """
    First checks for the csv_file. If it doesn't exist, fetches the data from the HomeAssistant api from START_TIME to END_TIME and caches it in the cache_file.
    The resulting data will be converted to the internal format (see ./converter.py) and returned.
    """
    if os.path.exists(csv_file):
        print("using data from csv file")
        return converter.from_csv(csv_file)

    if os.path.exists(cache_file):
        print("checking cache...")
        with open(cache_file, 'r') as file:
            cached_data = json.load(file)
            try:
                if parser.parse(cached_data[0][0]['last_changed']) == parser.parse(START_TIME):
                    print("using cached data")
                    return converter.from_json(cached_data)
                print("cache out-of-date")
            except IndexError as e:
                print(f"error reading cached data: {e}")
                pass

    api_token = os.getenv("TOKEN")
    print("fetching {ENDPOINT}...")
    response = requests.get(ENDPOINT, headers={
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }, verify=False)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data: {response.status_code} {response.text}")
    data = json.loads(response.text)
    if len(data) == 0:
        raise Exception("Failed to fetch data: Got empty response")
    with open(cache_file, 'w') as file:
        json.dump(data, file)
    print("done fetching")
    return converter.from_json(data)


def get_min_battery_capacity(energy) -> (float, float):
    """
    Gets the minimum battery capacity required so no energy is sold anymore.
    Returns the total bought energy and the computed capacity.
    """
    total_bought = 0
    battery = 0
    min_capacity = 0
    for values in energy.values():
        bought = values['bought']
        sold = values['sold']

        def diff():
            return abs(sold - bought)

        if bought > sold:
            battery_used = min(battery, diff())
            bought -= battery_used
            battery -= battery_used

            total_bought += diff()
            continue

        battery += sold
        min_capacity = max(min_capacity, battery)

    return (total_bought, min_capacity)

def get_total_sold_with_battery(battery_capacity: float, energy) -> (float, float):
    """
    Gets the total amount of sold energy when using a battery with the given capacity.
    The given capacity should have the same unit as the energies.
    Returns the total bought and total sold energy.
    """

    total_bought = 0
    total_sold = 0
    battery = 0
    for values in energy.values():
        bought = values['bought']
        sold = values['sold']

        diff = abs(sold - bought)

        if bought > sold:
            battery_used = min(battery, diff)
            battery -= battery_used
            diff -= battery_used
            assert battery >= 0
            assert diff >= 0

            total_bought += diff
            continue

        charged = min(battery_capacity - battery, diff)
        battery += charged
        diff -= charged
        assert battery <= battery_capacity
        assert diff >= 0

        total_sold += diff

    return (total_bought, total_sold)

def print_costs(unit, feed_in_tariff, total_bought, total_sold):
    total_cost = COST * total_bought
    total_win = feed_in_tariff * total_sold
    print(f"with {feed_in_tariff:> 6}€/{unit} feed-in tariff: {total_cost:.2f}€ - {total_win:.2f}€ = {total_cost - total_win:.2f}€ total costs")

def print_info(energy, unit, tested_battery_capacities: [str]):
    bought, min_capacity = get_min_battery_capacity(energy)
    print(f"min battery capacity: {min_capacity:> 3}{unit}, still have to buy: {bought:> 15}{unit}")
    print_costs(unit, PARTIAL_FEED_IN_TARIFF, bought, 0)

    print()
    for capacity in tested_battery_capacities:
        bought, sold = get_total_sold_with_battery(capacity, energy)
        print(f"total sold with {capacity:> 3}{unit} battery: {sold:> 15}{unit}, had to buy: {bought:> 15}{unit}    ", end="")
        print_costs(unit, PARTIAL_FEED_IN_TARIFF, bought, sold)

    print()
    total_bought = sum([item['bought'] for item in energy.values()])
    total_sold = sum([item['sold'] for item in energy.values()])
    print(f"total sold when selling all solar: {total_sold}{unit}, had to buy: {total_bought}{unit}")
    print_costs(unit, FULL_FEED_IN_TARIFF, total_bought, total_sold)


if __name__ == "__main__":
    energy = fetch_data('data.csv', 'data.json')

    print_info(energy, "kWh", [0, 1, 2, 3, 5, 10])
