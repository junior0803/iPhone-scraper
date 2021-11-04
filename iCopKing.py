"""
 Copyright (C) 2020 Arnold Lam - All Rights Reserved
 Unauthorized distribution of this file, via any medium is strictly prohibited.
"""

from processwrapper import ProcessMonitor
from config import LIVE_MODE, VERSION
from utils import get_inputs, verify_inputs, bcolors


if __name__ == "__main__":
    orders, checkout_proxy_queue, startup_proxy_queue, monitor_proxy_queue = get_inputs()
    print(bcolors.OKBLUE + bcolors.BOLD + "================iCopKing {}================".format(bcolors.HEADER + VERSION + bcolors.OKBLUE))
    if LIVE_MODE == True:
        print(bcolors.WARNING + "LIVE MODE ENABLED ORDER WILL BE PLACED")
        print("LIVE MODE ENABLED ORDER WILL BE PLACED")
        print("LIVE MODE ENABLED ORDER WILL BE PLACED" + bcolors.OKBLUE)
    print("已載入 {} 張訂單".format(len(orders)))
    print("已載入 {} 個結帳代理 及 {} 個刷貨代理".format(checkout_proxy_queue.qsize(), monitor_proxy_queue.qsize()))
    print("====================開始運行===================" + bcolors.ENDC)
    verify_inputs()
    monitor = ProcessMonitor(orders, checkout_proxy_queue, startup_proxy_queue, monitor_proxy_queue)
    monitor.start()
