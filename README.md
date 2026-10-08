# Predict factaroy variable

Local factory time-series app. It forecasts plant sensors with **Datadog Toto 2.0** on this computer.

No Gmail. No Google login. No Streamlit Cloud. After the model is downloaded once, the app can run offline.

- **App title:** Predict factaroy variable
- **Open in browser:** http://127.0.0.1:8501
- **Project folder:** `e:\Work\factory-toto`

---

## What this project does

Two local web pages:

1. **Predict factaroy variable** — forecast plant sensors with Toto 2.0
2. **Build datasets** — make a corn-to-sweet fermentation CSV with many variants

Corn line (default sample): steep / mash / fermenter converting starch liquor toward fructose syrup. You can predict **sweet degree (Brix)**, sweetness index, fructose, pH, fermenter temperature, residual starch, and more.

The model returns **P10 / P50 / P90** bands, then flags likely limit breaches.

Default model: **Toto-2.0-22m** (~84 MB). This PC has no NVIDIA GPU, so CPU inference is the normal path.

---

## Requirements

- Windows
- Python **3.12+** (`python --version`)
- Internet **only for the first model download**
- About 2 GB disk for Python packages + the 22m weights

---

## First-time setup (once)

Open PowerShell or Command Prompt:

```bat
cd /d e:\Work\factory-toto
python -m pip install -r requirements.txt
python download_model.py
python scripts\generate_sample_data.py
```

`download_model.py` copies Toto weights into `models\Toto-2.0-22m`. If that folder already has `config.json` and a `.safetensors` file, it skips the download.

To download again:

```bat
python download_model.py --force
```

---

## How to run

### Option A — double-click

1. Double-click `run.bat`
2. Wait until the window says the server started
3. In your browser open **http://127.0.0.1:8501**

`run.bat` binds only to this PC (`127.0.0.1:8501`). It does not ask for email.

### Option B — terminal

```bat
cd /d e:\Work\factory-toto
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --server.showEmailPrompt false
```

Then open **http://127.0.0.1:8501**.

Leave the terminal window open while you use the app.

### If the page does not open

Port 8501 is already in use, or the previous run is still alive. Stop it (see below), then start again.

```bat
cd /d e:\Work\factory-toto
stop.bat
run.bat
```

---

## How to stop / kill the run

Use **one** of these.

### 1. Double-click `stop.bat`

This finds whatever is listening on port **8501** and kills it.

### 2. In the terminal that started the app

Press **Ctrl+C**. If it asks `Terminate batch job (Y/N)?`, type **Y**.

### 3. Command line

```bat
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8501 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"
```

Or by PID (replace `12345` with the PID from `netstat`):

```bat
netstat -ano | findstr :8501
taskkill /PID 12345 /F
```

After it is stopped, http://127.0.0.1:8501 should not load.

---

## How to use the app

Left sidebar pages: **app** (Predict), **Build datasets**, and **Realtime predict**.

### Predict

1. Open http://127.0.0.1:8501
2. In **Plant line** choose **Corn sweet fermentation** (or Extrusion sample, or Upload file)
3. Pick signals such as sweet degree (Brix), sweetness index, fructose, pH, fermenter temperature
4. Set context / horizon, then **Run local Toto forecast**

Sample step is 15 minutes, so 96 steps is about 24 hours. First forecast on CPU can take several seconds.

### Build datasets

1. Open **Build datasets** in the left menu
2. Set days, sample interval, number of fermenters
3. Tick factory variants (sweetness, fermentation tank, mash, utilities)
4. Optionally add one custom sensor
5. Press **Build dataset**, preview the chart
6. **Download CSV** or **Save for Predict page** (writes `data\corn_sweet_ferment.csv`)

Then go back to Predict and choose **Corn sweet fermentation**.

### Real-time prediction

1. Open **Realtime predict** in the left menu
2. Set **Refresh time** (5 / 10 / 15 / 30 / 60 seconds)
3. Leave **Live auto-update** on
4. Each refresh:
   - writes a new corn-fermenter sample into local SQLite (`data\realtime_corn.db`)
   - reloads the chart from the database
   - runs Toto and draws live vs prediction, plus a **delta graph** (live minus prediction)
5. Watch **Sweet degree (Brix)**, sweetness, fermenter temperature, and pH
6. **Pause** with the Live toggle, or **Clear DB** / **Seed line** to restart the batch

Default refresh is 10 seconds so the CPU has time to forecast.

---

## Your data format

Need a time column plus numeric sensor columns.

| timestamp           | tank_id | brix_pct | sweetness_index | fermenter_temp_c | ph |
|---------------------|---------|----------|-----------------|------------------|-----|
| 2026-09-17 08:00:00 | F-1     | 42.1     | 38.6            | 59.8             | 7.4 |

You can still use extrusion-style files (`oven_temp_c`, `power_kw`, ...). Extra columns are fine. `tank_id`, `batch_id`, and `stage` are labels, not forecast targets.

Accepted time column names: `timestamp`, `time`, `datetime`, `date`, `ts`, `recorded_at`.

Save as `.csv` or `.xlsx`.

---

## Folder map

```
e:\Work\factory-toto\
  app.py                 Predict page
  pages\1_Build_datasets.py   Dataset builder
  pages\2_Realtime_predict.py Live corn prediction
  data\realtime_corn.db       Live SQLite database
  run.bat                Start local server
  stop.bat               Kill local server (port 8501)
  download_model.py      Fetch Toto weights (once)
  requirements.txt       Python packages
  factory_toto\          Engine, corn-sweet generator, sample lines
  models\Toto-2.0-22m\   Local model weights (offline)
  data\sample_plant.csv  Extrusion sample
  data\corn_sweet_ferment.csv  Corn sweet fermentation sample
  assets\                Banner and icon
  scripts\
    generate_sample_data.py
    smoke_forecast.py
  .streamlit\            Local-only Streamlit config
```

---

## Other commands

Quick check that Toto runs on this machine (no browser):

```bat
cd /d e:\Work\factory-toto
python scripts\smoke_forecast.py
```

Rebuild the sample CSV:

```bat
python scripts\generate_sample_data.py
```

Use a smaller CPU model (4m):

```bat
python download_model.py --model Datadog/Toto-2.0-4m
```

Then set `DEFAULT_MODEL_DIR` in `factory_toto\config.py` to `models\Toto-2.0-4m`.

Alarm limits for the sample line are also in `factory_toto\config.py`.

---

## Troubleshooting

| Problem | What to do |
|---|---|
| Browser asks for Gmail / Google | You opened the wrong URL. Use **http://127.0.0.1:8501**, not streamlit.app. |
| `Port 8501 is not available` | Run `stop.bat`, then `run.bat`. |
| `Local Toto weights not found` | Run `python download_model.py` once (needs internet that one time). |
| Page is blank / old UI | Hard refresh: **Ctrl+F5**. |
| Forecast is slow | Normal on CPU. Use context 256 and horizon 24–48 for a quicker test. |
| `python` not found | Install Python 3.12 and tick **Add python.exe to PATH**. |

This project does not send plant data to the cloud. Forecasts stay on this PC.
