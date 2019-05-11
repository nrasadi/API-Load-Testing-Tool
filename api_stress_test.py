import matplotlib.pyplot as plt
import sys
import time
import numpy as np
import threading
import requests as req
import json

""" Global Variables """
my_mutex = threading.Lock()
start_time = time.time()
end_time = time.time()
DURATION_ROUND = []
# DURATION_STEP = []

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
        "timeouts": 0
    }
}

# REPORTS = {
#     # "total_requests": 0,
#     # "response_time": [],
#     # "ok200_res_time": [],
#     # "ok1000_res_time": [],
#     # "avg_res_time": [],
#     # "min_res_time": [],
#     # "max_res_time": [],
#     # "ok200_ratio": [],
#     # "ok1000_ratio": [],
#     # "err500_400": [],
#     # "avg_ok200_res_time": [],
#     # "avg_ok1000_res_time": [],
#     # "timeouts": 0
# }


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
        print("Starting " + self.name)
        REPORTS["perTest"]["total_requests"] += 1
        my_mutex.release()
        try:
            if self.method == "get":
                r = req.get(self.url + self.api, self.params, timeout=10, verify=False)
            else:
                r = req.get(self.url + self.api, self.params, timeout=10, verify=False)

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
            print("{} status={}  Response_time= {}seconds".format(self.name, r.status_code, r.elapsed))
            my_mutex.release()
        except ValueError as Argument:
            my_mutex.acquire()
            print("Exception on Thrd->run: ".format(Argument))
            REPORTS["perSecond"]["timeouts"] += 1
            my_mutex.release()


# ################################### #
# @title Get Fields
url_field = "http://i-dia.ir/api/v1/"  # @param {type:"string"}
api_name_field = "report/reports/steps"  # @param {type:"string"}
method = "get"  # @param {type:"string"}
duration = 3  # @param {type:"integer"} # Definition: total test time (in seconds)
clients = 5  # @param {type:"integer"} # Definition: number of clients per second
rounds = 1  # @param {type:"integer"} # Definition: number of rounds
sleep_after_each_round = 0  # @param {type:"integer"} # Definition: time to sleep after finishing each round (in seconds)
# ################################### #


def start_test():

    global end_time
    thrds = []
    url = url_field
    url = url + "/" if url[-1] != "/" else url

    api = api_name_field

    # load users token and phone number
    # with open('/content/gdrive/My Drive/Colab Notebooks/user_data.txt', 'r') as file:
    with open("payload_for_activity_get_api.txt", "r") as file:
        payload = json.load(file)
    # payload has keys , values

    payload_len = len(payload)
    j = 0
    for i in range(clients):
        params = {}
        for index, key in enumerate(payload["keys"]):
            params[key] = payload["values"][j][index]
        thrds.append(Thrd(url, api, params, method))
        j = (j + 1) % payload_len

    for thrd in thrds:
        thrd.start()

    end_time = time.time()

    for thrd in thrds:
        thrd.join()

    print("Exiting Main Thread")
    return 0


def run_trigger():
    global REPORTS, start_time, end_time, DURATION_ROUND
    for report in REPORTS["perSecond"]:
        REPORTS["perSecond"][report] = []
    for report in REPORTS["perTest"]:
        REPORTS["perTest"][report] = []
    REPORTS["perTest"]["total_requests"] = 0
    REPORTS["perTest"]["timeouts"] = 0
    REPORTS["perTest"]["ok"] = 0
    REPORTS["perTest"]["err"] = 0

    for i in range(rounds):
        print("Round {}".format(i + 1))

        for j in range(duration):
            REPORTS["perSecond"]["response_time"] = []
            REPORTS["perSecond"]["ok200_res_time"] = []
            REPORTS["perSecond"]["ok1000_res_time"] = []
            REPORTS["perSecond"]["err500_400_res_time"] = []
            start_time = time.time()
            # /// START TEST /// #
            print("second {}th".format(j + 1))
            start_test()

            elapsed_time = end_time - start_time
            time.sleep(1-elapsed_time if elapsed_time+0.01 < 1 else 0)

            REPORTS["perTest"]["avg_res_time"].append(np.average(np.array(REPORTS["perSecond"]["response_time"])))
            REPORTS["perTest"]["min_res_time"].append(np.min(np.array(REPORTS["perSecond"]["response_time"])))
            REPORTS["perTest"]["max_res_time"].append(np.max(np.array(REPORTS["perSecond"]["response_time"])))
            REPORTS["perTest"]["avg_ok200_res_time"].append(np.average(np.array(REPORTS["perSecond"]["ok200_res_time"])))
            REPORTS["perTest"]["avg_ok1000_res_time"].append(np.average(np.array(REPORTS["perSecond"]["ok1000_res_time"])))

        time.sleep(sleep_after_each_round)
        print("End of the round {}. sleep {}".format(i, sleep_after_each_round))

run_trigger()
print("avg_res_time:{}\nmin_res_time:{}\nmax_res_time{}\navg_ok200_res_time{}\navg_err500_400_res_time{}\n"
      .format(REPORTS["perTest"]["avg_res_time"], REPORTS["perTest"]["min_res_time"], REPORTS["perTest"]["max_res_time"],
              REPORTS["perTest"]["avg_ok200_res_time"], REPORTS["perTest"]["avg_err500_400_res_time"]))
print("ok:{}\nerror:{}\ntimeout:{}\ntotal:{}".format(REPORTS["perTest"]["ok"],
      REPORTS["perTest"]["err"], REPORTS["perTest"]["timeouts"], REPORTS["perTest"]["total_requests"]))
