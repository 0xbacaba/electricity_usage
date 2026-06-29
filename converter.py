import csv
from datetime import datetime
from dateutil import parser
from settings import ENTITY_IDS
from collections import defaultdict

# output format:
# energy: { <timestamp>: { bought: <float>, sold: <float> } }

class Builder:
    def __init__(self):
        self.values = defaultdict(lambda: {"bought": 0.0, "sold": 0.0})
        self.last_values = {}  # {<entity_id>: <float>}

    def add_absolute(self, entity_id, value, time):
        if value == "unavailable":
            return
        value = float(value)

        prev = self.last_values.get(entity_id)
        self.last_values[entity_id] = value

        if prev is None:
            return

        change = value - prev

        key = ENTITY_IDS[entity_id]
        self.values[time][key] += change

    def result(self):
        return dict(self.values)

def floor_hour(time: str):
    return int(time[:13].replace("-", "").replace(":", "").replace("T", ""))

def from_csv(file):
    with open(file, "r") as file:
        data = csv.DictReader(file)
        output = Builder()

        for entry in data:
            time = floor_hour(entry["last_changed"])
            output.add_absolute(entry["entity_id"], entry["state"], time)

        return output.result()

def add_json_data(output, subdata):
    entity = subdata[0]["entity_id"]
    for entry in subdata:
        time = floor_hour(parser.parse(entry["last_changed"]))
        output.add_absolute(entity, entry["state"], time)


def from_json(data):
    output = Builder()

    add_json_data(output, data[0])
    add_json_data(output, data[1])

    return output.result()
