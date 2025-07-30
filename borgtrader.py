import os
from dotenv import load_dotenv
from dashboard.app import launch_dashboard
from services.core import BorgCore

def main():
    load_dotenv()
    core = BorgCore()
    launch_dashboard(core)

if __name__ == "__main__":
    main()