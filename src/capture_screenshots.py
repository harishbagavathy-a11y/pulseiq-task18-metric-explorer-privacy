import subprocess
import time
from pathlib import Path

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = Path(r"C:\Users\hp\.gemini\antigravity\scratch\PulseIQ_Task17_Live_Dashboard_Deployment\screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

phone_img = OUTPUT_DIR / "phone_dashboard_view.png"
desktop_img = OUTPUT_DIR / "desktop_dashboard_view.png"

# 1. Phone Viewport (iPhone 14/15/16 Pro: 390 x 844)
cmd_phone = [
    CHROME_PATH,
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--virtual-time-budget=6000",
    "--window-size=390,844",
    f"--screenshot={phone_img}",
    "http://localhost:8505"
]

print("Capturing mobile phone screenshot (390x844) with 6s virtual budget...")
res1 = subprocess.run(cmd_phone, capture_output=True, text=True)

# 2. Desktop Viewport (1440 x 900)
cmd_desktop = [
    CHROME_PATH,
    "--headless=new",
    "--disable-gpu",
    "--virtual-time-budget=6000",
    "--window-size=1440,900",
    f"--screenshot={desktop_img}",
    "http://localhost:8505"
]

print("Capturing desktop screenshot (1440x900) with 6s virtual budget...")
res2 = subprocess.run(cmd_desktop, capture_output=True, text=True)

print("Phone exists:", phone_img.exists(), "Size:", phone_img.stat().st_size if phone_img.exists() else 0)
print("Desktop exists:", desktop_img.exists(), "Size:", desktop_img.stat().st_size if desktop_img.exists() else 0)
