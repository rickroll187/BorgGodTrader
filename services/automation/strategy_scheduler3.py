import threading
import time

class StrategyScheduler:
    def __init__(self, strategies):
        self.strategies = strategies
        self.jobs = []

    def schedule_interval(self, name, interval_sec):
        def job():
            while True:
                self.strategies[name].run({})
                time.sleep(interval_sec)
        t = threading.Thread(target=job, daemon=True)
        t.start()
        self.jobs.append(t)

    def schedule_event(self, name, event_func):
        def job():
            while True:
                event_func()
                self.strategies[name].run({})
        t = threading.Thread(target=job, daemon=True)
        t.start()
        self.jobs.append(t)