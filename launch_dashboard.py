import os
import subprocess
import sys

def main():
    print("""
    ╔══════════════════════════════════════════╗
    ║         🤖 BorgGodTrader 🤖              ║
    ║       Assimilate. Adapt. Advance.        ║
    ╚══════════════════════════════════════════╝
    """)

    # Run using main.py which initializes core properly
    dashboard_path = "main.py"
    if not os.path.exists(dashboard_path):
        print("ERROR: main.py not found.")
        sys.exit(1)

    print("Launching dashboard...")
    print("Press Ctrl+C to stop\n")

    subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path,
                    "--server.headless", "true",
                    "--browser.gatherUsageStats", "false"])

if __name__ == "__main__":
    main()