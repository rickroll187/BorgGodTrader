import os
import subprocess
import sys

def main():
    dashboard_path = os.path.join("dashboard", "streamlit_app.py")
    if not os.path.exists(dashboard_path):
        print("ERROR: dashboard/streamlit_app.py not found.")
        sys.exit(1)
    print("Launching BorgGodTrader dashboard...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])

if __name__ == "__main__":
    main()