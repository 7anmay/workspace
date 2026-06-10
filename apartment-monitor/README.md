# Apartment Monitor

Slack-driven apartment availability monitor for San Francisco searches.

The starter config looks for:

- 2 bed / 2 bath apartments under $5,000
- 3 bed / 2 bath apartments under $6,000
- Mission Bay, Dogpatch, SoMa, South Beach, Potrero Hill, Rincon Hill, and Design District
- 855 Brannan, The Quincy, Avalon at Mission Bay, and Craigslist SF apartments

## Slack recommendation

Use a small private channel, for example `#apartment-search`, and invite the Slack app there.
That is better than a DM because the bot can keep a visible command/history log, and you can add roommates later. A DM also works if only one person will use it.

This tool uses Slack Socket Mode, so you do not need to host a public webhook.

Required Slack app setup:

1. Create a Slack app from `slack-app-manifest.yaml`.
2. Add bot scopes: `chat:write`, `channels:history`, `groups:history`, `im:history`, `app_mentions:read`.
3. Enable Socket Mode and create an app-level token with `connections:write`.
4. Subscribe to bot events: `message.channels`, `message.groups`, `message.im`, and `app_mention`.
5. Install the app in the workspace.
6. Export:
   - `SLACK_BOT_TOKEN=xoxb-...`
   - `SLACK_APP_TOKEN=xapp-...`

## Deploy with Docker Compose

Use this on a durable host such as a VPS, home server, or always-on local machine. A Cursor Cloud agent VM is useful for building and testing, but should not be treated as the long-term production host for apartment alerts.

1. Copy the environment template:

```bash
cp .env.example .env
```

2. Fill in `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` in `.env`.
3. Invite the bot to your apartment channel.
4. Start the service:

```bash
./scripts/deploy.sh
```

The container stores `config.yaml` and `state.json` in `./data`. The default command is:

```bash
apartment-monitor --config /data/config.yaml serve
```

`serve` runs scheduled searches and the Slack command listener in one process.

## Deploy without Docker

On a durable machine with Python 3.11+ and tmux:

```bash
cp .env.example .env
# Fill in SLACK_BOT_TOKEN and SLACK_APP_TOKEN.
./scripts/deploy-venv.sh
```

This creates `.venv`, installs the browser dependencies, initializes `data/config.yaml`, and starts `apartment-monitor --config data/config.yaml serve` in tmux session `apartment-monitor`.

## Local install

```bash
cd apartment-monitor
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,browser]'
playwright install chromium
```

The `browser` extra is needed for JavaScript-heavy apartment websites. Craigslist RSS does not require it.

## Configure

```bash
apartment-monitor --config config.yaml init
```

Edit `config.yaml` directly or use Slack commands.

## Run

One search cycle:

```bash
apartment-monitor --config config.yaml run-once
```

Scheduled monitor only:

```bash
apartment-monitor --config config.yaml watch
```

Slack command bot only:

```bash
apartment-monitor --config config.yaml slack-bot
```

Scheduled monitor plus Slack command bot:

```bash
apartment-monitor --config config.yaml serve
```

In Slack, bind notifications to the channel:

```text
apt bind here
```

## Slack commands

```text
apt status
apt run
apt sources
apt set 2b max 4800
apt set 3b max 5900
apt set neighborhoods Mission Bay, Dogpatch, SoMa, South Beach
apt add source new-building https://example.com/availability name="New Building" neighborhood="Mission Bay"
apt remove source new-building
```

Messages can be sent in the bound channel or as app mentions.

## How matching works

Each source fetches current page content, extracts visible listing-like text, and normalizes price, bedrooms, bathrooms, availability, and URL. A listing is sent to Slack only when it:

- matches one configured bed/bath rule exactly on bedrooms and at least the minimum bathrooms,
- is under the max price for that rule,
- mentions one configured neighborhood in the source metadata or listing text,
- has not already been seen in `state.json`.

## Adding more apartment sites

Use `apt add source` for most building availability pages. For JavaScript-heavy pages, `render_js` defaults to true when added from Slack:

```text
apt add source mb360 https://www.example.com/floorplans name="Mission Bay 360" neighborhood="Mission Bay"
```

For a static page:

```text
apt add source small-building https://example.com/units name="Small Building" neighborhood="Dogpatch" render_js=false
```

If a specific building has unusual markup, add a dedicated source adapter under `src/apartment_monitor/sources/`.
