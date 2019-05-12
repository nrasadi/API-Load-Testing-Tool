import matplotlib.pyplot as plt
import matplotlib as mpl
import time
import numpy as np
import threading
import requests as req
import json

""" Global Variables """
my_mutex = threading.Lock()
start_time = time.time()
end_time = time.time()

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
        # print("Starting " + self.name)
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
            # print("{} status={}  Response_time= {}seconds".format(self.name, r.status_code, r.elapsed))
            my_mutex.release()
        except ValueError as Argument:
            my_mutex.acquire()
            print("Exception on Thrd->run: ".format(Argument))
            REPORTS["perSecond"]["timeouts"] += 1
            my_mutex.release()


# ################################### #
# @title Get Fields
url_field = "http://i-dia.ir/api/v1/"  # @param {type:"string"}
# api_name_field = "report/reports/steps"  # @param {type:"string"}
api_package = {
    "keys": ["api_path", "payload_path", "method", "name"],
    "values": [
        ["report/reports/steps", "payload_for_activity_get_api.txt", "get", "steps-get"],
        ["report/sugar", "loader_io_payload - Copy.txt", "get", "sugar-get"]
    ]
}
duration = 60  # @param {type:"integer"} # Definition: total test time (in seconds)
clients = 20  # @param {type:"integer"} # Definition: number of clients per second
rounds = 1  # @param {type:"integer"} # Definition: number of rounds
sleep_after_each_round = 0  # @param {type:"integer"} # Definition: time to sleep after finishing each round (in seconds)
# ################################### #


def start_test():

    global end_time
    thrds = []
    url = url_field
    url = url + "/" if url[-1] != "/" else url

    # with open('/content/gdrive/My Drive/Colab Notebooks/user_data.txt', 'r') as file:
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

    for i in range(rounds):
        print("Round {}".format(i + 1))

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

            print("\n-----------------------------\nSecond {}th    used APIs:{}\n"
                  "Avg response time:{}s      min:{}s     max:{}s\n"
                  "success:{}     error:{}     timeout:{}"
                  "\n-----------------------------\n".format(j+1, u_apis,
                                                                  REPORTS["perTest"]["avg_res_time"][-1],
                                                                  REPORTS["perTest"]["min_res_time"][-1],
                                                                  REPORTS["perTest"]["max_res_time"][-1],
                                                                  REPORTS["perTest"]["ok"],
                                                                  REPORTS["perTest"]["err"],
                                                                  REPORTS["perTest"]["timeouts"]))

        plt.figure("Results", figsize=(12, 9))
        mpl.rc('lines', linewidth=3)

        plt.subplot(2, 1, 1)
        plt.plot(np.arange(1, duration+1), np.array(REPORTS["perTest"]["avg_res_time"])*1000, label="average response time", color="#007acc")
        plt.plot(np.arange(1, duration + 1), np.array(REPORTS["perTest"]["min_res_time"])*1000, label="min response time", color="#00b300")
        plt.plot(np.arange(1, duration + 1), np.array(REPORTS["perTest"]["max_res_time"])*1000, label="max response time", color="red")
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

        plt.figure("Response distribution", figsize=(5, 5))
        plt.pie([REPORTS["perTest"]["ok"], REPORTS["perTest"]["err"], REPORTS["perTest"]["timeouts"]],
                labels=('Success', 'Error 500/400', 'Timeouts'), autopct='%1.1f%%', startangle=90,
                colors=('#00b300', 'yellow', 'red'), labeldistance=0.5)

        plt.show()

        time.sleep(sleep_after_each_round)
        print("End of the round {}. sleep {}".format(i, sleep_after_each_round))

run_trigger()
print("avg_res_time:{}s\nmin_res_time:{}s\nmax_res_time{}s\navg_ok200_res_time{}s\navg_err500_400_res_time{}s\n"
      .format(REPORTS["perTest"]["avg_res_time"], REPORTS["perTest"]["min_res_time"], REPORTS["perTest"]["max_res_time"],
              REPORTS["perTest"]["avg_ok200_res_time"], REPORTS["perTest"]["avg_err500_400_res_time"]))
print("ok:{}\nerror:{}\ntimeout:{}\ntotal:{}".format(REPORTS["perTest"]["ok"],
      REPORTS["perTest"]["err"], REPORTS["perTest"]["timeouts"], REPORTS["perTest"]["total_requests"]))
