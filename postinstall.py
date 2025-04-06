import subprocess

# Automatically installs Playwright browsers (Chromium, Firefox, WebKit)
subprocess.run(["playwright", "install"], check=True)
