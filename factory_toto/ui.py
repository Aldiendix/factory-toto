THEME = """
<style>
html, body, [class*="css"] {
  font-family: "Segoe UI", "IBM Plex Sans", sans-serif;
}
.stApp {
  background:
    radial-gradient(900px 420px at 8% -10%, #ccfbf1 0%, transparent 55%),
    radial-gradient(800px 380px at 100% 0%, #ffedd5 0%, transparent 50%),
    #eef7f8;
}
.block-container { padding-top: 1rem; max-width: 1440px; }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.stDeployButton {display: none !important;}
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
  background: #ffffff !important;
  border-right: 1px solid #d1f0ea;
}
[data-testid="stSidebar"] h3 {
  color: #0f766e;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-size: 0.82rem;
}
.hero-wrap img {
  border-radius: 28px;
  box-shadow: 0 18px 40px rgba(15, 118, 110, 0.16);
  border: 3px solid #99f6e4;
}
div[data-testid="stImage"] img {
  border-radius: 24px;
  box-shadow: 0 16px 36px rgba(15, 118, 110, 0.18);
}
[data-testid="stSidebar"] div[data-testid="stImage"] img {
  box-shadow: 0 8px 18px rgba(15, 118, 110, 0.18);
  border: 2px solid #99f6e4;
}
.kpi {
  background: #ffffff;
  border: 1px solid #d1f0ea;
  border-left: 6px solid #0d9488;
  border-radius: 16px;
  padding: 16px 18px;
  min-height: 108px;
  box-shadow: 0 8px 20px rgba(15, 118, 110, 0.08);
}
.kpi .label {
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.kpi .value {
  color: #134e4a;
  font-size: 1.7rem;
  font-weight: 750;
  margin-top: 6px;
}
.kpi .hint { color: #64748b; font-size: 12px; margin-top: 4px; }
.badge {
  display: inline-block;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.ok { background: #d1fae5; color: #065f46; }
.warn { background: #ffedd5; color: #9a3412; }
.crit { background: #fee2e2; color: #991b1b; }
.stButton>button {
  background: linear-gradient(90deg, #0d9488, #0f766e);
  color: #ffffff !important;
  border: 0;
  font-weight: 750;
  border-radius: 12px;
  padding: 0.6rem 1.2rem;
  box-shadow: 0 8px 18px rgba(13, 148, 136, 0.28);
}
.panel {
  background: #ffffff;
  border: 1px solid #d1f0ea;
  border-radius: 18px;
  padding: 8px 4px 4px 4px;
}
</style>
"""


def page_banner(title: str, subtitle: str, kicker: str = "Local plant forecast · Toto 2.0") -> str:
    return f"""
    <div style="
      background: linear-gradient(90deg, #0f766e 0%, #0d9488 58%, #ea580c 140%);
      color: #ffffff;
      padding: 20px 28px;
      border-radius: 20px;
      margin-bottom: 14px;
      box-shadow: 0 14px 28px rgba(15, 118, 110, 0.24);
    ">
      <div style="font-size:12px; letter-spacing:0.16em; text-transform:uppercase; color:#ccfbf1; font-weight:700;">
        {kicker}
      </div>
      <div style="font-size:2.25rem; font-weight:800; line-height:1.15; margin-top:4px;">
        {title}
      </div>
      <div style="margin-top:6px; font-size:1.05rem; color:#f0fdfa;">
        {subtitle}
      </div>
    </div>
    """
