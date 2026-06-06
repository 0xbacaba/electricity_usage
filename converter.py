import csv
from datetime import datetime
from dateutil import parser

# output format:
# energy: { <datetime>: { bought: <float>, sold: <float> } }

class Builder:
    def __init__(self):
        self.values = {}  # in output format
        self.last_values = {}  # {<entity_id>: <float>}

    def add_absolute(self, entity_id, value, time):
        keys = {
            "sensor.stromzaehler_haus_total_energy_bought_1_8_0": "bought",
            "sensor.stromzaehler_pv_total_energy_sold_2_8_0": "sold"
        }
        if value == "unavailable":
            return
        value = float(value)

        if entity_id not in self.last_values:
            self.last_values[entity_id] = value

        change = value - self.last_values[entity_id]
        self.last_values[entity_id] = value

        for eid, key in keys.items():
            if time not in self.values:
                self.values[time] = {}
            # we need to ensure every entry has both keys (bought and sold)
            if key not in self.values[time]:
                self.values[time][key] = 0
            if eid == entity_id:
                self.values[time][key] += change

    def result(self):
        return self.values

def floor_hour(time: datetime):
    return datetime(time.year, time.month, time.day, time.hour, 0, 0, 0, time.tzinfo)

def from_csv(file):
    with open(file, "r") as file:
        data = csv.DictReader(file)
        output = Builder()

        for entry in data:
            time = floor_hour(parser.parse(entry["last_changed"]))
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
