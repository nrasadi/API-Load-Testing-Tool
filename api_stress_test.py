import matplotlib.pyplot as plt
import matplotlib as mpl
import time
from datetime import datetime
import pytz
import numpy as np
import threading
import requests as req
import json


# ################################### #
# @title Get Fields
url_field = "url_field"  # @param {type:"string"}
# api_name_field = "report/reports/steps"  # @param {type:"string"}
duration = 3  # @param {type:"integer"} #Definition: total test time (in seconds)
clients = 20  # @param {type:"integer"} #Definition: number of clients per second
rounds = 1  # @param {type:"integer"} #Definition: number of rounds
request_timeout = 10 # @param {type:"integer"} #Definition: timeout after request_timeout seconds
sleep_after_each_round = 0  # @param {type:"integer"} #Definition: time to sleep after finishing each round (in seconds)
result_log_path = "results"  # @param {type:"string"}

gdrive = "gdrive_path"
api_package = {
    "keys": ["api_path", "payload_path", "method", "name"],
    "values": [
        ["report/reports/steps", gdrive+"payload_name.txt", "get", "steps-get"],
    ]
}
# ################################### #


""" Global Variables """
my_mutex = threading.Lock()
start_time = time.time()
end_time = time.time()
dt = datetime.now(tz=pytz.timezone("Asia/Tehran"))
save_name = ((str(dt).split(" ")[0] + "-" + str(dt).split(" ")[1]).split("+")[0]).split(".")[0].replace(":", "-")

REPORTS = {
    "perSecond": {
        "response_time": [],
        "ok200_res_time": [],
        "ok1000_res_time": [],
        "err500_400_res_time": [],

    },
    "perTest": {
        "avg_res_time": [],
        "min_res_time": [],
        "max_res_time": [],
        "avg_ok200_res_time": [],
        "avg_ok1000_res_time": [],
        "avg_err500_400_res_time": [],
        "total_requests": 0,
        "ok": 0,
        "err": 0,
        "timeouts": 0,
        "mean_avg": 0,
        "global_max": [0, 0], # x,y
        "global_min": [0, np.inf]
    }
}


class Thrd(threading.Thread):
    def __init__(self, url, api_name, params, method="get"):
        threading.Thread.__init__(self)
        self.url = url
        self.api = api_name
        self.params = params
        self.method = method

    def run(self):
        global REPORTS, my_mutex
        my_mutex.acquire()
        REPORTS["perTest"]["total_requests"] += 1
        my_mutex.release()
        try:
            if self.method == "get":
                r = req.get(self.url + self.api, self.params, timeout=request_timeout, verify=False)
            else:
                r = req.get(self.url + self.api, self.params, timeout=request_timeout, verify=False)

            if r.status_code == 200:
                my_mutex.acquire()
                REPORTS["perSecond"]["ok200_res_time"].append(r.elapsed.total_seconds())
                REPORTS["perTest"]["ok"] += 1
                my_mutex.release()
                data = r.json()
                if data["error_code"] == "1000":
                    my_mutex.acquire()
                    REPORTS["perSecond"]["ok1000_res_time"].append(r.elapsed.total_seconds())
                    my_mutex.release()
            else:
                my_mutex.acquire()
                REPORTS["perSecond"]["err500_400_res_time"].append(r.elapsed.total_seconds())
                REPORTS["perTest"]["err"] += 1
                my_mutex.release()

            my_mutex.acquire()
            REPORTS["perSecond"]["response_time"].append(r.elapsed.total_seconds())
            my_mutex.release()
        except ValueError as Argument:
            my_mutex.acquire()
            s = "Exception on Thrd->run: ".format(Argument)
            print(s, file=open(f'{result_log_path}-{save_name}', 'a'))
            print(s)
            REPORTS["perSecond"]["timeouts"] += 1
            my_mutex.release()


def start_test():

    global end_time
    thrds = []
    url = url_field
    url = url + "/" if url[-1] != "/" else url

#     with open('user_data_path' 'r') as file:
    payload = []
    for api in api_package["values"]:
        with open(api[1], "r") as file:
            payload.append(json.load(file))
    # Each payload has keys , values

    n_apis = len(api_package["values"])
    used_api_names = []
    j = 0
    for i in range(clients):
        params = {}
        api_index = np.random.randint(0, n_apis)
        payload_len = len(payload[api_index])
        for index, key in enumerate(payload[api_index]["keys"]):
            params[key] = payload[api_index]["values"][j][index]
        thrds.append(Thrd(url, api_package["values"][api_index][0], params, api_package["values"][api_index][2]))
        j = (j + 1) % payload_len
        used_api_names.append(api_package["values"][api_index][3])

    for thrd in thrds:
        thrd.start()

    end_time = time.time()

    for thrd in thrds:
        thrd.join()

    return used_api_names


def run_trigger():
    global REPORTS, start_time, end_time
    for report in REPORTS["perSecond"]:
        REPORTS["perSecond"][report] = []
    for report in REPORTS["perTest"]:
        REPORTS["perTest"][report] = []
    REPORTS["perTest"]["total_requests"] = 0
    REPORTS["perTest"]["timeouts"] = 0
    REPORTS["perTest"]["ok"] = 0
    REPORTS["perTest"]["err"] = 0
    REPORTS["perTest"]["global_min"] = [0, np.inf]
    REPORTS["perTest"]["global_max"] = [0, 0]
    REPORTS["perTest"]["mean_avg"] = 0

    for i in range(rounds):
        s = "Round {}".format(i + 1)
        print(s, file=open(f'{result_log_path}-{save_name}', 'a'))
        print(s)

        for j in range(duration):
            REPORTS["perSecond"]["response_time"] = []
            REPORTS["perSecond"]["ok200_res_time"] = []
            REPORTS["perSecond"]["ok1000_res_time"] = []
            REPORTS["perSecond"]["err500_400_res_time"] = []
            start_time = time.time()
            # /// START TEST /// #
            u_apis = start_test()

            elapsed_time = end_time - start_time
            time.sleep(1-elapsed_time if elapsed_time+0.01 < 1 else 0)

            REPORTS["perTest"]["avg_res_time"].append(np.average(np.array(REPORTS["perSecond"]["response_time"])))
            REPORTS["perTest"]["min_res_time"].append(np.min(np.array(REPORTS["perSecond"]["response_time"])))
            REPORTS["perTest"]["max_res_time"].append(np.max(np.array(REPORTS["perSecond"]["response_time"])))

            temp = np.array(REPORTS["perSecond"]["ok200_res_time"])
            REPORTS["perTest"]["avg_ok200_res_time"].append(np.average(temp) if len(temp) > 0 else 0)

            temp = np.array(REPORTS["perSecond"]["ok1000_res_time"])
            REPORTS["perTest"]["avg_ok1000_res_time"].append(np.average(temp) if len(temp) > 0 else 0)

            temp = np.array(REPORTS["perSecond"]["err500_400_res_time"])
            REPORTS["perTest"]["avg_err500_400_res_time"].append(np.average(temp) if len(temp) > 0 else 0)
            s = "\n-----------------------------\nSecond #{}    used APIs:{}\n" \
                "Avg response time:{}s      min:{}s     max:{}s\n" \
                "success:{}     error:{}     timeout:{}"\
                "\n-----------------------------\n".format(j+1, u_apis,
                                                                  REPORTS["perTest"]["avg_res_time"][-1],
                                                                  REPORTS["perTest"]["min_res_time"][-1],
                                                                  REPORTS["perTest"]["max_res_time"][-1],
                                                                  REPORTS["perTest"]["ok"],
                                                                  REPORTS["perTest"]["err"],
                                                                  REPORTS["perTest"]["timeouts"])
            print(s, file=open(f'{result_log_path}-{save_name}', 'a'))
            print(s)

        rnd_avg = np.average(REPORTS["perTest"]["avg_res_time"])*1000
        rnd_min = [np.argmin(REPORTS["perTest"]["min_res_time"])+1, np.min(REPORTS["perTest"]["min_res_time"])*1000]
        rnd_max = [np.argmax(REPORTS["perTest"]["max_res_time"])+1, np.max(REPORTS["perTest"]["max_res_time"])*1000]
        REPORTS["perTest"]["mean_avg"] = (rnd_avg + REPORTS["perTest"]["mean_avg"]*i) / (i+1)
        if REPORTS["perTest"]["global_max"][1] < rnd_max[1]:
            REPORTS["perTest"]["global_max"] = rnd_max
        if REPORTS["perTest"]["global_min"][1] > rnd_min[1]:
            REPORTS["perTest"]["global_min"] = rnd_min

        plt.figure("Results", figsize=(12, 9))
        mpl.rc('lines', linewidth=3)

        plt.subplot(2, 1, 1)
        plt.plot(np.arange(1, duration+1), np.array(REPORTS["perTest"]["avg_res_time"])*1000, label="average response time", color="#007acc")
        plt.plot(np.arange(1, duration + 1), np.array(REPORTS["perTest"]["min_res_time"])*1000, label="min response time", color="#00b300")
        plt.plot(np.arange(1, duration + 1), np.array(REPORTS["perTest"]["max_res_time"])*1000, label="max response time", color="red")

        plt.hlines(REPORTS["perTest"]["mean_avg"], 1, duration, colors='#f7ba02', linestyles='-',
                   label=f'mean average ({REPORTS["perTest"]["mean_avg"]:.0f})ms', linewidth=3)
        plt.hlines(REPORTS["perTest"]["global_max"][1], 1, duration, colors='#aa0000', linestyles='--',
                   label=f'global max ({REPORTS["perTest"]["global_max"][1]:.0f})ms', linewidth=3)
        plt.hlines(REPORTS["perTest"]["global_min"][1], 1, duration, colors='#008204', linestyles='--',
                   label=f'global min ({REPORTS["perTest"]["global_min"][1]:.0f})ms', linewidth=3)
        plt.xticks(np.arange(1, duration + 1))
        plt.ylabel("Response time (milliseconds)")
        plt.yticks(np.linspace(0, np.max(REPORTS["perTest"]["max_res_time"])*1000, 15))
        plt.legend()
        plt.grid(color="#cccccc")
        plt.title("API stress test results")

        plt.subplot(2, 1, 2)
        plt.plot(np.arange(1, duration+1), np.array(REPORTS["perTest"]["avg_ok200_res_time"])*1000, label="average success response time", color="#007acc")
        plt.plot(np.arange(1, duration + 1), np.array(REPORTS["perTest"]["avg_err500_400_res_time"])*1000, label="average error response time", color="red")
        plt.xlabel("Duration (seconds)")
        plt.xticks(np.arange(1, duration + 1))
        plt.ylabel("Response time (milliseconds)")
        plt.yticks(np.linspace(0, np.max(REPORTS["perTest"]["max_res_time"])*1000, 15))
        plt.legend()
        plt.grid(color="#cccccc")


        plt.savefig("StressTest-results"+save_name)

        plt.figure("Response distribution", figsize=(5, 5))
        reports = [REPORTS["perTest"]["ok"], REPORTS["perTest"]["err"], REPORTS["perTest"]["timeouts"]]
        labels = ['Success', 'Error 500/400', 'Timeouts']
        colors = ['#00b300', 'yellow', 'red']
        for ir, report in enumerate(reports):
            if report == 0:
                labels.remove(labels[ir])
                colors.remove(colors[ir])
                reports.remove(reports[ir])

        plt.pie(reports, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors, labeldistance=0.5)

        plt.savefig("StressTest-pieChart"+save_name)
        plt.show()

        time.sleep(sleep_after_each_round)
        s = "End of the round {}. sleep {}".format(i, sleep_after_each_round)
        print(s, file=open(f'{result_log_path}-{save_name}', 'a'))
        print(s)

run_trigger()

s = "avg_res_time:{}s\nmin_res_time:{}s\nmax_res_time:{}s\navg_ok200_res_time:{}s\navg_err500_400_res_time:{}s\n"\
    .format(REPORTS["perTest"]["avg_res_time"], REPORTS["perTest"]["min_res_time"], REPORTS["perTest"]["max_res_time"],
              REPORTS["perTest"]["avg_ok200_res_time"], REPORTS["perTest"]["avg_err500_400_res_time"])
print(s, file=open(f'{result_log_path}-{save_name}', 'a'))
print(s)
print("ok:{}\nerror:{}\ntimeout:{}\ntotal:{}".format(REPORTS["perTest"]["ok"],
      REPORTS["perTest"]["err"], REPORTS["perTest"]["timeouts"], REPORTS["perTest"]["total_requests"]))

s = "mean average response time:{:.0f}ms   global min response time:{:.0f}ms    global max response time:{:.0f}ms".format(
REPORTS["perTest"]["mean_avg"], REPORTS["perTest"]["global_min"][1], REPORTS["perTest"]["global_max"][1])
print(s, file=open(f'{result_log_path}-{save_name}', 'a'))
print(s)
