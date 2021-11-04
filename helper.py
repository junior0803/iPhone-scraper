"""
 Copyright (C) 2020 Arnold Lam - All Rights Reserved
 Unauthorized distribution of this file, via any medium is strictly prohibited.
"""

from config import NAME_OBFUSCATION, NAME_OBFUSCATION_LENGTH, NAME_OBFUSCATION_POSITION, REMOVE_ORDER_PROXIES, TELEGRAM_NOTIF_USERID, TELEGRAM_NOTIF_VPSID, RANDOM_PHONE, RANDOM_EMAIL, RANDOM_EMAIL_PREFIX, RANDOM_EMAIL_DOMAIN
from schema import STORE_CODES, MODEL_NAMES
from chrome import ChromeRunner
from runner import OrderRunner
from utils import now, bcolors, remove_entry, read_csv, get_giftcards_pool, get_contacts
from random import choice
from string import ascii_lowercase, digits
from datetime import date
import random
import time


class CheckoutSession:
    def __init__(self, process_id, order, checkout_proxy_queue, startup_proxy_queue, monitor_proxy_queue, tg_msg_queue):
        self.id = process_id
        self.order = order
        self.forced_store = None
        if self.order['store_selection']:
            self.forced_store = self.order['store_selection']
        self.creditCard = None
        self.giftcards_queue = get_giftcards_pool()
        self.contacts = get_contacts()
        self.pickupName = random.choice(self.contacts['name'])
        if not RANDOM_EMAIL:
            self.pickupEmail = random.choice(self.contacts['email'])
        else:
            self.pickupEmail = RANDOM_EMAIL_PREFIX + (''.join(choice(ascii_lowercase) for i in range(8))) + '@{}'.format(RANDOM_EMAIL_DOMAIN)
        if not RANDOM_PHONE:
            self.pickupPhone = random.choice(self.contacts['phone'])
        else:
            self.pickupPhone = '9' + (''.join(choice(digits) for i in range(7)))
        if NAME_OBFUSCATION:
            if NAME_OBFUSCATION_POSITION == 'first':
                self.pickupName['firstName'] = self.pickupName['firstName'] + ' ' + (''.join(choice(ascii_lowercase) for i in range(NAME_OBFUSCATION_LENGTH)))
            else:
                self.pickupName['lastName'] = self.pickupName['firstName'] + ' ' + (''.join(choice(ascii_lowercase) for i in range(NAME_OBFUSCATION_LENGTH)))
        self.login = False
        if order['appleId_email']:
            self.login = True
        print(bcolors.OKBLUE + "{} 載入型號: {}, 強制店鋪: {}, 數量: {}, 登入模式: {}, 取貨人: {} {}, Email: {}, 電話: {}".format(self.id, self.order['model'], self.forced_store, self.order['quantity'], self.login, self.pickupName['lastName'], self.pickupName['firstName'], self.pickupEmail, self.pickupPhone) + bcolors.ENDC)
        self.paymentMode = self.findPaymentMode()
        self.startup_proxy = startup_proxy_queue.get()
        startup_proxy_queue.put(self.startup_proxy)
        self.checkout_proxy_queue = checkout_proxy_queue
        self.monitor_proxy_queue = monitor_proxy_queue
        self.checkout_proxy = self.checkout_proxy_queue.get()
        checkout_proxy_queue.put(self.checkout_proxy)
        self.tg_msg_queue = tg_msg_queue
        print(bcolors.OKBLUE + "{} 正使用 加車代理 {} 結帳代理 {}".format(self.id, self.startup_proxy, self.checkout_proxy))
        try:
            self.start()
        except:
            self.close_browser()
            exit("{} An Error Has Occurred".format(self.id))

    def start(self):
        self.chrome = ChromeRunner(self.id, self.startup_proxy, self.order)
        self.chrome.start()
        if not self.chrome.x_aos_stk:
            self.close_browser()
        self.runner = OrderRunner('{}'.format(self.id), self.order, self.creditCard, self.paymentMode, self.giftcards_queue, self.pickupName, self.pickupEmail, self.pickupPhone, self.chrome.checkout_endpoint, self.chrome.checkout_api_request_cookies, self.chrome.x_aos_stk, self.checkout_proxy, self.checkout_proxy_queue, self.monitor_proxy_queue, self.chrome)
        self.orderNumber = self.runner.start()
        if self.orderNumber:
            if self.orderNumber:
                self.postOrderProcessing(self.orderNumber)
        self.close_browser()

    def findPaymentMode(self):
        if self.order['use_credit_card']:
            try:
                self.creditCard = read_csv('creditcards')[int(self.order['use_credit_card']) - 1]
                print(bcolors.OKBLUE + "{} 付款方式: 信用卡".format(self.id) + bcolors.ENDC)
                return 'CREDIT'
            except IndexError:
                self.chrome.driver.quit()
                exit("{} INIT ERROR: CREDITCARDS.CSV ROW {} NOT SET, CHECK CREDITCARDS.CSV AND ORDERS.CSV".format(
                    self.id, int(self.order['use_credit_card'])))
        else:
            if self.order['giftcard_pin']:
                self.giftcard = []
                giftcard_pin = self.order['giftcard_pin'].replace(' ','').split('/')
                for i in giftcard_pin:
                    self.giftcard.append(i.replace(' ', ''))
                print(bcolors.OKBLUE + "{} 付款方式: 指定 {} 張禮品卡".format(self.id, len(self.giftcard)) + bcolors.ENDC)
                return 'GIFT'
            else:
                self.giftcard = self.giftcards_queue.pop(0)
                self.giftcards_queue.append(self.giftcard)
                print(bcolors.OKBLUE + "{} 沒有指明禮品卡 正使用禮品卡池 此訂單將使用{}張禮品卡".format(self.id, len(self.giftcard)) + bcolors.ENDC)
                return 'GIFTPOOL'

    def postOrderProcessing(self, orderNumber):
        info_used = open('submitted_info.txt', 'a+', encoding="utf-8")
        info_used.write(now() + ', {}, {}, {}, {}, {}'.format(self.order['model'], self.pickupName['lastName'], self.pickupName['firstName'], self.pickupEmail, self.pickupPhone) + '\n')
        info_used.close()
        if orderNumber != 'AOS_DELIVERY_ONLY':
            log_file = open("order_success_log.csv", "a+", encoding="utf-8")
            used_proxy = open("order_success_proxies.txt", "a+")
            if orderNumber != 'FALSEMODE':
                if not RANDOM_EMAIL:
                    remove_entry('./csv/emails.csv', self.pickupEmail)
                if not RANDOM_PHONE:
                    remove_entry('./csv/phones.csv', self.pickupPhone)
                if not NAME_OBFUSCATION:
                    remove_entry('./csv/names.csv', self.pickupName)
        else:
            log_file = open("forced_delivery_log.csv", "a+", encoding="utf-8")
            used_proxy = open("forced_delivery_proxies.txt", "a+")

        if orderNumber != 'FALSEMODE':
            used_proxy.write(self.runner.checkout_proxy_used + '\n')
            if REMOVE_ORDER_PROXIES:
                remove_entry('./csv/orderproxies.csv', self.runner.checkout_proxy_used)

        used_proxy.close()
        giftcards = '/'.join(self.runner.applied_giftcards)
        if orderNumber in ['AOS_DELIVERY_ONLY']:
            log_file.write("{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {} \n".format(date.today().strftime("%d/%m/%Y"), now(), self.order['model'], orderNumber, STORE_CODES[self.runner.storeCode], self.runner.pickupName['lastName'], self.runner.pickupName['firstName'], self.pickupEmail, self.pickupPhone, giftcards,self.runner.checkout_proxy_used))
            log_file.close()
        else:
            log_string_private = "{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {} , https://store.apple.com/go/hk/z/vieworder/{}/{}/AOS-HK-A10000085027\n".format(date.today().strftime("%d/%m/%Y"), now(), self.order['model'], orderNumber, STORE_CODES[self.runner.storeCode], self.runner.pickupName['lastName'], self.runner.pickupName['firstName'], self.pickupEmail, self.pickupPhone, giftcards, self.runner.checkout_proxy_used, orderNumber, self.pickupEmail)
            log_file.write(log_string_private)
            log_file.close()
            self.tg_msg_queue.put({'msg': TELEGRAM_NOTIF_VPSID + ': ' + log_string_private, 'msg_type': 'private'})
            self.tg_msg_queue.put({'msg': "{} {} {}".format(TELEGRAM_NOTIF_USERID, STORE_CODES[self.runner.storeCode], MODEL_NAMES[self.order['model']]), 'msg_type': 'public'})
        if orderNumber == 'FALSEMODE':
            self.chrome.driver.get('https://{}.store.apple.com/hk-zh/shop/checkout?_s=Review'.format(self.chrome.checkout_endpoint))
            time.sleep(5)

    def close_browser(self):
        self.chrome.driver.quit()
