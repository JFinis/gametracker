import keyboard
import datetime
from playsound import playsound

from tableauhyperapi import HyperProcess, Telemetry, \
    Connection, CreateMode

import argparse


class SessionSuccessStats:

    def __init__(self):
        self._num = 0
        self._count = 0

    def update(self, results, is_new):
        if is_new:
            self._num += 1
            self._count += results[-1]

    def print_caption(self):
        print(f"Session", end='|')

    def print(self):
            print(f" {self._count / self._num*100:5.1f} " if self._num > 0 else f"{'':7}", end='|')


class LastNStats:

    def __init__(self, num):
        self._num = num
        self._count = 0
        self._num_values = 0

    def update(self, results, is_new):
        self._num_values = len(results)
        pos_to_remove = self._num_values - self._num - 1
        if pos_to_remove >= 0:
            self._count -= results[pos_to_remove]
        self._count += results[-1]

    def print_caption(self):
        print(f"{self._num:3}-Su%", end='|')

    def print(self):
        print(f" {self._count / min(self._num_values,self._num)*100:5.1f} ", end='|')


class StreakStats:

    def __init__(self, outcome):
        self._outcome = outcome
        self._longest_streak = 0
        self._longest_session_streak = 0
        self._cur_streak = 0

    def update(self, results, is_new):
        val = results[-1]
        if val == self._outcome:
            self._cur_streak += 1
            self._longest_streak = max(self._longest_streak, self._cur_streak)
            if is_new:
                self._longest_session_streak = max(self._longest_session_streak, self._cur_streak)
        else:
            self._cur_streak = 0

    def print_caption(self):
        print(f"          {'Win' if self._outcome else 'Loss':>4}-Streak           ", end='|')

    def print(self):
        print(f"{self._cur_streak:3} (session {self._longest_session_streak:3}) (longest {self._longest_streak:3}) ", end='|')


class TimeStats:

    def __init__(self):
        self._start = datetime.datetime.now().replace(microsecond=0)
        self._end = None

    def update(self, results, is_new):
        if is_new:
            self._end = datetime.datetime.now().replace(microsecond=0)

    def print_caption(self):
        print(f"  Time   ", end='|')

    def print(self):
        if self._end is None:
            print(f"   old   ", end='|')
        else:
            print(f" {self._end - self._start} ", end='|')


class RunCounterStats:

    def __init__(self):
        self._num_runs = 0
        self._num_runs_this_session = 0

    def update(self, results, is_new):
        self._num_runs += 1
        if is_new:
            self._num_runs_this_session += 1

    def print_caption(self):
        print(" Run ", end='|')
        print(" RunID ", end='|')

    def print(self):
        print(f" {self._num_runs_this_session if self._num_runs_this_session > 0 else '':3} ",  end='|')
        print(f"{self._num_runs:6} ", end='|')


class GameState:

    def __init__(self, connection, log_file):
        self._connection = connection
        self._results = []
        self._log_file = log_file
        self._stats = [RunCounterStats(), TimeStats(), LastNStats(20), LastNStats(100), LastNStats(200), LastNStats(500), SessionSuccessStats(), StreakStats(False), StreakStats(True)]
        res = connection.execute_list_query(
            f"SELECT outcome FROM '{self._log_file}' (schema (time timestamp, outcome bool) with (format csv)) ORDER BY time")

        for r in res:
            self.update_state(r[0], False)
            self.print_state()
        print(f"==== SESSION START (log file: {self._log_file}) ====")
        self.print_caption()


    def update_state(self, outcome, is_new):
        self._results.append(outcome)
        for s in self._stats:
            s.update(self._results, is_new)


    def print_caption(self):
        for s in self._stats:
            s.print_caption()
        print("")

    def print_state(self):
        num_results = len(self._results)
        if (num_results-1) % 20 == 0:
            self.print_caption()
        for s in self._stats:
            s.print()
        print("")

    def write_log(self, outcome):
        now = datetime.datetime.now()
        f = open(self._log_file, "a")
        output = (now.strftime("%Y-%m-%d %H:%M:%S") + "," + str(outcome) + '\n')
        f.write(output)
        f.close()

    def log_game(self, outcome):
        self.write_log(outcome)
        self.update_state(outcome, True)
        self.print_state()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("logfile")
    args = parser.parse_args()

    # Create log file if it doesn't exist, yet
    f = open(args.logfile, "a")
    f.close()

    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(endpoint=hyper.endpoint) as connection:

            print("Press 'space' to register a win, 'down arrow' to register a loss.")
            gameState = GameState(connection, args.logfile)
            while True:
                key = keyboard.read_key()
                if key == "space":
                    gameState.log_game(1)
                    playsound('sounds/win.mp3')
                elif key == "down":
                    gameState.log_game(0)
                    playsound('sounds/loss.mp3')
