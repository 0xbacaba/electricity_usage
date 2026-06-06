# Electricity usage

Analyze electricity usage data from Home Assistant to see how much partial feed-in and battery storage could decrease costs.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Go into `settings.py` and adjust:
- `ENTITY_IDS` - The entity ids that correspond to the bought and sold (solar produced) energy
- `COST` - The electricity cost per kWh
- `PARTIAL_FEED_IN_TARIFF` - The feed-in tariff when only selling unused solar energy
- `FULL_FEED_IN_TARIFF` - The feed-in tariff when selling all solar energy
If you want to use automatic data fetching, 
you can also set `API`, `START_TIME` and `END_TIME` ([more info](#automatic-data-fetching)).

## Usage

### Automatic data fetching

The script *can* fetch data automatically, however Home Assistant doesn't want to send what is requested if the timeframe is too big, so this method is discouraged.
It can be useful for small timeframes though.

1. Create an access token: Go to Home Assistant -> Profile -> Security -> Long-lived access tokens. Create one and paste it into a `.env` file that looks like this:
    ```bash
    export TOKEN=<your token>
    ```
    The script will detect this automatically.

2. (Optional) Modify the timeframe: Go into `settings.py` and set `START_TIME` and `END_TIME`.

### Manual data fetching

1. Go to Home Assistant -> History (`<your-url>/history` if you don't have it in your sidebar)

2. Select the timeframe and the entities (the selected entities must have the same IDs as configured in `settings.py`).

3. Click on the 3 dots -> Download data, save the file as `data.csv` in the directory where you will execute the script.

### Executing

After fetching the data (or configuring automatic fetching), just run:
```bash
python3 usage.py
```

## What does it calculate?

The script will show 

- The minimum size a battery would need to be so no electricity would have been sold (shown as min battery capacity)
- For a set of battery sizes: The energy that would have been bought and sold with said battery, as well as the costs (using the `PARTIAL_FEED_IN_TARIFF`)
- The total energy bought and sold without a battery, as well as the costs (using the `FULL_FEED_IN_TARIFF`)
