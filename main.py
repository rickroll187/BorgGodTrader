import os
from dotenv import load_dotenv
from dashboard.advanced_dashboard import show_advanced_dashboard
from services.core import BorgCore

def main():
    load_dotenv()
    core = BorgCore()
    show_advanced_dashboard(core)

if __name__ == "__main__":
    main()