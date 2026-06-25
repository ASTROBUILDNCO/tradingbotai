import schedule
import time
from astro_agent.orchestrator import Orchestrator


def main():
    o = Orchestrator()
    schedule.every().day.at("07:30").do(o.run_morning_routine)
    schedule.every().day.at("12:30").do(o.run_midday_routine)
    schedule.every().day.at("18:30").do(o.run_evening_routine)
    print("AstroBuild&Co. scheduler started")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
