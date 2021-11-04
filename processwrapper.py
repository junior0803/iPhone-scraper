"""
 Copyright (C) 2020 Arnold Lam - All Rights Reserved
 Unauthorized distribution of this file, via any medium is strictly prohibited.
"""

from helper import CheckoutSession
from telegram_notif import TGHandler
from config import PROCESS_CREATE_INTERVAL
from utils import bcolors
import time
from multiprocessing import Process, Queue


class ProcessMonitor:
    def __init__(self, orders, checkout_proxy_queue, startup_proxy_queue, monitor_proxy_queue):
        self.processes = []
        self.processid_map = {}
        self.orders = orders
        self.checkout_proxy_queue = checkout_proxy_queue
        self.startup_proxy_queue = startup_proxy_queue
        self.monitor_proxy_queue = monitor_proxy_queue
        self.tg_message_queue = Queue()

    def start(self):
        order_id = 1
        Process(target=TGHandler, args=(self.tg_message_queue,)).start()
        for order in self.orders:
            self.create_task(order_id, order)
            order_id += 1
            time.sleep(PROCESS_CREATE_INTERVAL)
        self.monitor()

    def monitor(self):
        while True:
            for i in self.processes:
                if not i.is_alive():
                    del self.processes[self.processes.index(i)]
                    process_key = self.processid_map[i]
                    print(bcolors.FAIL + "訂單#{} Restarting Process".format(process_key[0]) + bcolors.ENDC)
                    self.create_task(process_key[0], process_key[1])
                    time.sleep(5)
            time.sleep(1)

    def create_task(self, order_id, order):
        new_process = Process(target=CheckoutSession, args=("訂單#{}".format(order_id), order, self.checkout_proxy_queue, self.startup_proxy_queue, self.monitor_proxy_queue, self.tg_message_queue))
        new_process.start()
        self.processes.append(new_process)
        self.processid_map[new_process] = [order_id, order]
        order_id += 1
