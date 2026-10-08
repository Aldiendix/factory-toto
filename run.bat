@echo off
cd /d "%~dp0"
REM Fully local: no Google/Gmail, no Streamlit Cloud, no Hugging Face login.
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
set HF_HUB_DISABLE_TELEMETRY=1
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
echo Starting local app at http://127.0.0.1:8501
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --server.showEmailPrompt false --browser.gatherUsageStats false
