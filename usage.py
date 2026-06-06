import json
import requests
import os
import converter

from dotenv import load_dotenv
from dateutil import parser

if not load_dotenv():
    print("Failed to load .env, trying to continue anyways...")

API = "https://home.server.local/api"
ENTITY_IDS = "sensor.stromzaehler_haus_total_energy_bought_1_8_0,sensor.stromzaehler_pv_total_energy_sold_2_8_0"
START_TIME = "2026-05-28T00:00:00+02:00"
END_TIME = "2026-06-03T00:00:00+02:00"

END_TIME_URLENCODED = requests.utils.quote(END_TIME)

ENDPOINT = f"{API}/history/period/{START_TIME}?filter_entity_id={ENTITY_IDS}&minimal_response=true&end_time={END_TIME_URLENCODED}"

COST = 0.29  # €/kWh
PARTIAL_FEED_IN_TARIFF = 0.0779  # €/kWh
FULL_FEED_IN_TARIFF = 0.1235  # €/kWh

def fetch_data(output_file: str):
    if os.path.exists(output_file):
        print("checking cache...")
        with open(output_file, 'r') as file:
            cached_data = json.load(file)
            try:
                if parser.parse(cached_data[0][0]['last_changed']) == parser.parse(START_TIME):
                    print("using cached data")
                    return cached_data
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
    with open(output_file, 'w') as file:
        json.dump(data, file)
    print("done fetching")
    return data


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

def print_costs(feed_in_tariff, total_bought, total_sold):
    total_cost = COST * total_bought
    total_win = feed_in_tariff * total_sold
    print(f"with {feed_in_tariff:> 6}€/{unit} feed-in tariff: {total_cost:.2f}€ - {total_win:.2f}€ = {total_cost - total_win:.2f}€ total costs")

def print_info(energy, unit, tested_battery_capacities: [str]):
    bought, min_capacity = get_min_battery_capacity(energy)
    print(f"min battery capacity: {min_capacity:> 3}{unit}, still have to buy: {bought:> 15}{unit}")
    print_costs(PARTIAL_FEED_IN_TARIFF, bought, 0)

    print()
    for capacity in tested_battery_capacities:
        bought, sold = get_total_sold_with_battery(capacity, energy)
        print(f"total sold with {capacity:> 3}{unit} battery: {sold:> 15}{unit}, had to buy: {bought:> 15}{unit}    ", end="")
        print_costs(PARTIAL_FEED_IN_TARIFF, bought, sold)

    print()
    total_bought = sum([item['bought'] for item in energy.values()])
    total_sold = sum([item['sold'] for item in energy.values()])
    print(f"total sold when selling all solar: {total_sold}{unit}, had to buy: {total_bought}{unit}")
    print_costs(FULL_FEED_IN_TARIFF, total_bought, total_sold)


data = fetch_data('data.json')
unit = data[0][0]["attributes"]["unit_of_measurement"]

energy = converter.from_json(data)
print_info(energy, unit, [0, 1, 2, 3, 5, 10])
