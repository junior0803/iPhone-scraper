"""
 Copyright (C) 2020 Arnold Lam - All Rights Reserved
 Unauthorized distribution of this file, via any medium is strictly prohibited.
"""

from config import LIVE_MODE, ADVANCE_PAY, ADVANCE_PAY_SHIPPING_ADDRESS_ST, MONITOR_POLLING_INTERVAL, PROCESS_RESTART_TIMER, SUPPRESS_MONITOR_PROXY_SWITCH_MSG, STORE_ENABLE_R673, STORE_ENABLE_R610, STORE_ENABLE_R499, STORE_ENABLE_R485, STORE_ENABLE_R428, STORE_ENABLE_R409
from schema import STORE_CODES, CHECKOUT_SPECIAL_ITEMS, AIRPOD_MAX
from utils import now, cookie_header_format, bcolors
from bs4 import BeautifulSoup
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning, MaxRetryError
import requests
import time
import urllib.parse
import json

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

enabled_stores = {
    'R428': STORE_ENABLE_R428,
    'R485': STORE_ENABLE_R485,
    'R499': STORE_ENABLE_R499,
    'R610': STORE_ENABLE_R610,
    'R673': STORE_ENABLE_R673,
    'R409': STORE_ENABLE_R409
}

class OrderRunner:
    def __init__(self, id, order, creditCard, paymentMode, giftcards_queue, pickupName, pickupEmail, pickupPhone, endpoint, cookies, stk, proxy_ip, checkout_proxy_queue, monitor_proxy_queue, chrome):
        self.processStartTime = time.time()
        self.id = id
        self.model = order['model']
        self.forced_store = None
        self.store_placeholder = 'R428'
        if order['store_selection']:
            self.forced_store = order['store_selection']
            self.store_placeholder = self.forced_store
        self.creditCard = creditCard
        self.paymentMode = paymentMode
        if self.paymentMode != 'CREDIT':
            self.giftcard = order['giftcard_pin']
            self.giftcards_queue = giftcards_queue
        self.pickupName = pickupName
        self.pickupEmail = pickupEmail
        self.pickupPhone = pickupPhone
        self.endpoint = endpoint
        self.x_aos_stk = stk
        self.cookies = cookies
        self.chrome = chrome
        self.checkout_session = requests.Session()
        self.proxy_ip = proxy_ip
        self.checkout_session.proxies = {'https': 'https://{}'.format(self.proxy_ip)}
        self.checkout_session.verify = False
        self.checkout_session.cookies.update(cookies)
        self.checkout_proxy_used = proxy_ip
        self.checkout_proxy_queue = checkout_proxy_queue
        self.monitor_proxy_queue = monitor_proxy_queue
        self.tried_giftcards = []
        self.applied_giftcards = []
        self.gcindex = 0
        self.referrer = 'https://{}.store.apple.com/hk-zh/shop/checkout?_s=Fulfillment-init'.format(self.endpoint)
        self.storeCode = ''
        self.latencyTimeTotal = 0
        self.submitted_contact = False
        self.submitted_payment = False
        self.retry = False

    def start(self):
        self.update_cookies()
        if ADVANCE_PAY and self.model not in CHECKOUT_SPECIAL_ITEMS:
            shipping = self.adv_pay_select_shipping()
            if not shipping:
                return
            shipping_contact = self.adv_pay_shipping_contact()
            if not shipping_contact:
                return
            if self.paymentMode in ['GIFT', 'GIFTPOOL']:
                payment = self.post_payment_giftcard()
            else:
                payment = self.post_payment_credit()
            if not payment:
                return
            review = self.adv_pay_order_review()
            if not review:
                return
            switch = self.adv_pay_switch_mode()
            if not switch:
                return
            pickup = self.adv_pay_select_pickup()
            if not pickup:
                return
            self.processStartTime = time.time()

        while True:
            response = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=search&_m=checkout.fulfillment.pickupTab.pickup.storeLocator&checkout.fulfillment.pickupTab.pickup.storeLocator.showAllStores=false&checkout.fulfillment.pickupTab.pickup.storeLocator.selectStore={}&checkout.fulfillment.pickupTab.pickup.storeLocator.searchInput=Tsim%20Sha%20Tsui'.format(self.endpoint, self.store_placeholder), headers=self.get_headers_post())
            if response.status_code == 200:
                self.update_cookies()
                break
            else:
                print("{} {} Response: {}".format(now(), self.id, response.status_code))
                self.switch_checkout_proxy()
                time.sleep(1)

        if self.model in AIRPOD_MAX:
            time.sleep(10)
            self.select_store('R499')
            time.sleep(10)
            self.post_pickup_contact()
            time.sleep(10)
            self.post_payment_giftcard()
            time.sleep(10)
            review_data = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=continue&_m=checkout.billing'.format(self.endpoint), headers=self.get_headers_post())
            self.update_cookies()
            self.extract_review_data(review_data)
            time.sleep(20)
            self.am_adv_info_edit_pickup()

        print(bcolors.OKGREEN + "{} 初始化成功".format(self.id) + bcolors.ENDC)
        while True:
            if self.get_pickup_availability():
                result = self.start_checkout_process(self.storeCode)
                return result
            else:
                return

    def start_checkout_process(self, retailStore):
        startTime = datetime.now()
        if self.model not in AIRPOD_MAX:
            self.select_store(retailStore)
            self.post_pickup_contact()
            if not ADVANCE_PAY:
                if self.paymentMode in ['GIFT', 'GIFTPOOL']:
                    payment = self.post_payment_giftcard()
                else:
                    payment = self.post_payment_credit()
                if not payment:
                    print(bcolors.FAIL + "{} {} {} 付款失敗".format(now(), self.id, self.proxy_ip))
                    return
            review_data = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=continue&_m=checkout.billing'.format(self.endpoint), headers=self.get_headers_post())
        else:
            review_data = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=continue&_m=checkout.fulfillment&checkout.fulfillment.fulfillmentOptions.selectFulfillmentLocation=RETAIL&checkout.fulfillment.pickupTab.pickup.storeLocator.showAllStores=false&checkout.fulfillment.pickupTab.pickup.storeLocator.selectStore={}&checkout.fulfillment.pickupTab.pickup.storeLocator.searchInput=Sha%20Tin'.format(self.endpoint, retailStore), headers=self.get_headers_post())

        self.update_cookies()
        review_data = self.extract_review_data(review_data)
        end_time = datetime.now()
        if not review_data:
            print(bcolors.FAIL + "{} {} {} 未能成功獲取訂單總結 此物品已售罄".format(now(), self.id, self.proxy_ip) + bcolors.ENDC)
            return
        if review_data == 'FUTURE':
            print(bcolors.FAIL + "{} {} {} 未能選取當天現貨 此物品已售罄".format(now(), self.id, self.proxy_ip) + bcolors.ENDC)
            return
        totalTime = (end_time - startTime).total_seconds()
        print(bcolors.HEADER + "{} Time Elapsed To Prepare Order: {}s".format(self.id, round(totalTime,3)) + bcolors.ENDC)
        if LIVE_MODE == True:
            self.post_confirm_order()
            return self.postorder_analysis()
        else:
            print(bcolors.WARNING + "LIVE MODE IS SET TO FALSE, ORDER NOT SUBMITTED." + bcolors.ENDC)
            return 'FALSEMODE'

    def adv_pay_select_shipping(self):
        response = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=continue&_m=checkout.fulfillment'.format(self.endpoint), headers=self.get_headers_post())
        if response.status_code != 200:
            if response.status_code == 503:
                print(bcolors.FAIL + "{} {} ADV PAY 未能選取送貨模式. 正在重試".format(self.id, self.proxy_ip) + bcolors.ENDC)
                self.switch_checkout_proxy()
                return self.adv_pay_select_shipping()
            print(bcolors.FAIL + "{} {} ADV PAY 未能選取送貨模式.".format(self.id, self.proxy_ip) + bcolors.ENDC)
            return
        print(bcolors.HEADER + "{} {} ADV PAY 成功選取送貨模式.".format(self.id, self.proxy_ip) + bcolors.ENDC)
        self.update_cookies()
        time.sleep(10)
        return True

    def adv_pay_shipping_contact(self):
        response = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=continue&_m=checkout.shipping&checkout.shipping.addressContactEmail.address.emailAddress={}&checkout.shipping.addressContactPhone.address.mobilePhone={}&checkout.shipping.addressContactPhone.address.isDaytimePhoneSelected=false&checkout.shipping.addressNotification.address.emailAddress=&checkout.shipping.addressSelector.newAddress.address.street2=&checkout.shipping.addressSelector.newAddress.address.lastName={}&checkout.shipping.addressSelector.newAddress.address.firstName={}&checkout.shipping.addressSelector.newAddress.address.companyName=&checkout.shipping.addressSelector.newAddress.address.street={}&checkout.shipping.addressSelector.newAddress.address.isBusinessAddress=false'.format(self.endpoint, self.pickupEmail, self.pickupPhone, self.pickupName['lastName'], self.pickupName['firstName'], ADVANCE_PAY_SHIPPING_ADDRESS_ST), headers=self.get_headers_post())
        if response.status_code != 200:
            if response.status_code == 503:
                print(bcolors.FAIL + "{} {} ADV PAY 未能選提交貨資料. 正在重試".format(self.id, self.proxy_ip) + bcolors.ENDC)
                self.switch_checkout_proxy()
                return self.adv_pay_shipping_contact()
            print(bcolors.FAIL + "{} {} ADV PAY 未能選提交貨資料.".format(self.id, self.proxy_ip) + bcolors.ENDC)
            return
        print(bcolors.HEADER + "{} {} ADV PAY 成功提交送貨資料.".format(self.id, self.proxy_ip) + bcolors.ENDC)
        self.update_cookies()
        time.sleep(10)
        return True

    def adv_pay_order_review(self):
        response = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=continue&_m=checkout.billing'.format(self.endpoint), headers=self.get_headers_post())
        if response.status_code != 200:
            if response.status_code == 503:
                print(bcolors.FAIL + "{} {} ADV PAY 未能獲取訂單總結. 正在重試".format(self.id, self.proxy_ip) + bcolors.ENDC)
                self.switch_checkout_proxy()
                return self.adv_pay_order_review()
            print(bcolors.FAIL + "{} {} ADV PAY 未能獲取訂單總結.".format(self.id, self.proxy_ip) + bcolors.ENDC)
            return
        print(bcolors.HEADER + "{} {} ADV PAY 成功獲取訂單總結.".format(self.id, self.proxy_ip) + bcolors.ENDC)
        self.update_cookies()
        time.sleep(10)
        return True

    def adv_pay_switch_mode(self):
        response = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=edit&_m=checkout.review.fulfillmentReview.reviewGroup-1&checkout.locationConsent.locationConsent=false'.format(self.endpoint), headers=self.get_headers_post())
        if response.status_code != 200:
            if response.status_code == 503:
                print(bcolors.FAIL + "{} {} ADV PAY 未能選取更改訂單. 正在重試".format(self.id, self.proxy_ip) + bcolors.ENDC)
                self.switch_checkout_proxy()
                return self.adv_pay_switch_mode()
            print(bcolors.FAIL + "{} {} ADV PAY 未能選取更改訂單.".format(self.id, self.proxy_ip) + bcolors.ENDC)
            return
        print(bcolors.HEADER + "{} {} ADV PAY 成功選取更改訂單.".format(self.id, self.proxy_ip) + bcolors.ENDC)
        self.update_cookies()
        time.sleep(10)
        return True

    def adv_pay_select_pickup(self):
        response = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=selectFulfillmentLocationAction&_m=checkout.fulfillment.fulfillmentOptions&checkout.fulfillment.fulfillmentOptions.selectFulfillmentLocation=RETAIL'.format(self.endpoint), headers=self.get_headers_post())
        if response.status_code != 200:
            if response.status_code == 503:
                print(bcolors.FAIL + "{} {} ADV PAY 未能選取提取模式. 正在重試".format(self.id, self.proxy_ip) + bcolors.ENDC)
                self.switch_checkout_proxy()
                return self.adv_pay_select_pickup()
            print(bcolors.FAIL + "{} {} ADV PAY 未能選取提取模式.".format(self.id, self.proxy_ip) + bcolors.ENDC)
            return
        print(bcolors.HEADER + "{} {} ADV PAY 成功選取提取模式.".format(self.id, self.proxy_ip) + bcolors.ENDC)
        self.update_cookies()
        time.sleep(10)
        return True

    def am_adv_info_edit_pickup(self):
        response = self.checkout_session.request("POST", 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=edit&_m=checkout.review.fulfillmentReview.reviewGroup-1'.format(self.endpoint), headers=self.get_headers_post())
        if response.status_code != 200:
            if response.status_code == 503:
                print(bcolors.FAIL + "{} {} AM預先提交 未能預先提交資料. 正在重試".format(self.id, self.proxy_ip) + bcolors.ENDC)
                self.switch_checkout_proxy()
                return self.am_adv_info_edit_pickup()
            print(bcolors.FAIL + "{} {} AM預先提交 未能預先提交資料.".format(self.id, self.proxy_ip) + bcolors.ENDC)
            return
        print(bcolors.HEADER + "{} {} AM預先提交 成功預先提交資料.".format(self.id, self.proxy_ip) + bcolors.ENDC)
        self.update_cookies()
        return True

    def get_pickup_availability(self):
        if self.model in AIRPOD_MAX:
            link = 'https://{}.store.apple.com/hk-zh/shop/checkout?_s=Fulfillment'.format(self.endpoint)
        else:
            link = 'https://{}.store.apple.com/hk-zh/shop/checkout?_s=Fulfillment-init'.format(self.endpoint)
        proxy_ip = self.monitor_proxy_queue.get()
        self.monitor_proxy_queue.put(proxy_ip)
        self.monitor_session = requests.Session()
        self.monitor_session.verify = False
        self.monitor_session.cookies.update(self.checkout_session.cookies)
        self.monitor_session.proxies = {'http:': 'http://{}'.format(proxy_ip), 'https': 'http://{}'.format(proxy_ip)}
        session_timer = time.time()
        req_count = 0
        fail_count = 0
        while True:
            try:
                get_content = self.monitor_session.get(link, headers=self.get_headers_get())
                if get_content.status_code != 200:
                    if get_content.status_code == 503:
                        self.switch_monitor_proxy()
                        req_count = 0
                        continue
                    elif get_content.status_code == 400:
                        print(bcolors.FAIL + "{} {} {} Error Occurred While Polling Stock Availability.".format(now(), self.id, get_content.status_code) + bcolors.ENDC)
                        return
                self.update_cookies()
                soup = BeautifulSoup(get_content.content, 'lxml')
                if soup.find(id="init_data"):
                    in_stock = False
                    retailStores = json.loads(soup.find(id="init_data").string)['checkout']['fulfillment']['pickupTab']['pickup']['storeLocator']['searchResults']['d']['retailStores']
                    for store in retailStores:
                        if (enabled_stores[store['storeId']] and self.forced_store is None) or (store['storeId'] == self.forced_store):
                            if (self.model not in CHECKOUT_SPECIAL_ITEMS and store['availability']['storeAvailability'] != "無法使用") or (self.model in CHECKOUT_SPECIAL_ITEMS and store['availability']['storeAvailability'] in ['可供取貨：明天', '可供取貨：今日']):
                                in_stock = True
                                if time.time() - self.processStartTime > 45:
                                    self.storeCode = store['storeId']
                                    print(bcolors.OKGREEN + "{} {} {} 於 {} 發現存貨. ".format(now(), self.id, self.model, store['storeName']) + bcolors.ENDC)
                                    return True
                    if in_stock:
                        print(bcolors.WARNING + "{} {} {} 發現存貨. 初始時間未夠45秒 暫緩結帳程序".format(now(), self.id, self.model) + bcolors.ENDC)

                if time.time() - session_timer > 50:
                    self.chrome.driver.get(link)
                    self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=search&_m=checkout.fulfillment.pickupTab.pickup.storeLocator&checkout.fulfillment.pickupTab.pickup.storeLocator.showAllStores=false&checkout.fulfillment.pickupTab.pickup.storeLocator.selectStore={}&checkout.fulfillment.pickupTab.pickup.storeLocator.searchInput=Central'.format(self.endpoint, self.store_placeholder), headers=self.get_headers_post())
                    print("{} {} {} Refreshing Session to Prevent Timeout".format(now(), self.id, self.proxy_ip))
                    session_timer = time.time()

                if time.time() - self.processStartTime >= PROCESS_RESTART_TIMER * 60:
                    print(bcolors.OKBLUE + "{} {} RESTART TIME REACHED, RESTARTING CHECKOUT SESSION".format(now(), self.id, proxy_ip) + bcolors.ENDC)
                    return
                fail_count = 0
                if req_count >= 5:
                    self.switch_monitor_proxy()
                    req_count = 0
                else:
                    req_count += 1
                time.sleep(MONITOR_POLLING_INTERVAL)

            except KeyError as e:
                print(bcolors.FAIL + "{} {} POLLING PROXY Key Error Occured while polling pickup availability. {}".format(now(), self.id, e) + bcolors.ENDC)
                return

            except:
                if fail_count <= 10:
                    self.switch_monitor_proxy()
                    fail_count += 1
                else:
                    print("Continuous Monitor Session Error. Terminating Process")
                    return

    def select_store(self, retailStore):
        request_time = datetime.now()
        response = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=continue&_m=checkout.fulfillment&checkout.fulfillment.fulfillmentOptions.selectFulfillmentLocation=RETAIL&checkout.fulfillment.pickupTab.pickup.storeLocator.showAllStores=false&checkout.fulfillment.pickupTab.pickup.storeLocator.selectStore={}&checkout.fulfillment.pickupTab.pickup.storeLocator.searchInput=%E9%A6%99%E6%B8%AF'.format(self.endpoint, retailStore), headers=self.get_headers_post())
        response_time = datetime.now()
        if response.status_code != 200:
            print(bcolors.FAIL + "{} {} {} {} Error Occurred While Selecting Pickup Store".format(now(), self.id, self.proxy_ip, response.status_code) + bcolors.ENDC)
            return
        if response.status_code == 503:
            self.switch_checkout_proxy()
            self.select_store(retailStore)
        self.update_cookies()
        print(bcolors.HEADER + "{} {} {} 已選取零售店{} {} ".format(now(), self.id, self.proxy_ip, STORE_CODES[retailStore], self.latency(request_time, response_time)) + bcolors.ENDC)

    def post_pickup_contact(self):
        self.referrer = "https://{}.store.apple.com/hk-zh/shop/checkout?_s=PickupContact-init".format(self.endpoint)
        emailAddress = urllib.parse.quote(self.pickupEmail, safe='')
        mobilePhone = self.pickupPhone
        lastName = urllib.parse.quote(self.pickupName['lastName'], safe='')
        firstName = urllib.parse.quote(self.pickupName['firstName'], safe='')
        request_time = datetime.now()
        response = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=continue&_m=checkout.pickupContact&checkout.pickupContact.selfPickupContact.selfContact.address.emailAddress={}&checkout.pickupContact.selfPickupContact.selfContact.address.mobilePhone={}&checkout.pickupContact.selfPickupContact.selfContact.address.isDaytimePhoneSelected=false&checkout.pickupContact.selfPickupContact.selfContact.address.lastName={}&checkout.pickupContact.selfPickupContact.selfContact.address.firstName={}'.format(self.endpoint, emailAddress, mobilePhone, lastName, firstName), headers=self.get_headers_post())
        response_time = datetime.now()
        if response.status_code != 200:
            print(bcolors.FAIL + "{} {} {} {} Error Occurred While Posting Pickup Contact".format(now(), self.id, self.proxy_ip, response.status_code) + bcolors.ENDC)
            if response.status_code == 503:
                self.switch_checkout_proxy()
                return self.post_pickup_contact()
            return
        self.update_cookies()
        print(bcolors.HEADER + "{} {} {} 成功提交取貨人. {}".format(now(), self.id, self.proxy_ip, self.latency(request_time, response_time)) + bcolors.ENDC)

    def extract_review_data(self, response):
        try:
            review = response.json()['body']['checkout']['review']
            fulfillmentReview = review['fulfillmentReview'][review['fulfillmentReview']['c'][0]]
            pickupContactReview = review['pickupContactReview'][review['pickupContactReview']['c'][0]]
            itemReview = fulfillmentReview[fulfillmentReview['c'][0]]
            print(bcolors.HEADER + bcolors.BOLD + self.id, response.json()['body']['meta']['page']['title'])
            print(self.id, "================訂單總結=================")
            print(self.id, fulfillmentReview['d']['pickup']['quote'])
            print(self.id, "取貨人: {} {}".format(pickupContactReview['d']['lastName'], pickupContactReview['d']['firstName']))
            print(self.id, "Email: {}".format(pickupContactReview['d']['emailAddress']))
            print(self.id, "電話: {}".format(pickupContactReview['d']['mobilePhone']))
            print(self.id, "型號: {}".format(itemReview['d']['name']))
            print(self.id, "數量: {}".format(itemReview['itemQuantity']['d']['quantity']))
            print(self.id, "訂單總計: {}".format(itemReview['d']['totalPrice']))
            print(self.id, "=======================================" + bcolors.ENDC)
            if self.model not in CHECKOUT_SPECIAL_ITEMS:
                return True
            elif self.model in CHECKOUT_SPECIAL_ITEMS and ('今日' in fulfillmentReview['d']['pickup']['quote'] or '明天' in fulfillmentReview['d']['pickup']['quote']):
                return True
            return
        except KeyError:
                return
        except Exception as e:
            print(e)

    def post_payment_giftcard(self):
        if not self.giftcard:
            if len(self.giftcards_queue) > 0:
                self.giftcard = self.giftcards_queue.pop(0)
            else:
                print(bcolors.FAIL + "{} {} {} 禮品卡池庫存不足".format(now(), self.id, self.proxy_ip) + bcolors.ENDC)
                return False
        else:
            self.giftcard = self.giftcard.replace(' ','').split('/')
        for i in self.giftcard:
            if i in self.tried_giftcards:
                print(bcolors.FAIL + "{} {} {} 禮品卡 {} 已曾嘗試提交，將提取下一張禮品卡重試".format(now(), self.id, self.proxy_ip, i[-4:]) + bcolors.ENDC)
                continue
            request_time = datetime.now()
            response = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=applyGiftCard&_m=checkout.billing&checkout.billing.billingOptions.selectBillingOption=&checkout.billing.billingOptions.selectedBillingOptions.giftCard.giftCardInput.deviceID={}&checkout.billing.billingOptions.selectedBillingOptions.giftCard.giftCardInput.giftCard={}'.format(self.endpoint, self.deviceID, i), headers=self.get_headers_post())
            response_time = datetime.now()
            if response.status_code != 200:
                if response.status_code == 503:
                    self.switch_checkout_proxy()
                    self.giftcard = None
                    print(bcolors.FAIL + "{} {} {} {} Error Occurred While Applying Gift Card. Retrying Payment.".format(now(), self.id, self.proxy_ip, response.status_code) + bcolors.ENDC)
                    continue
                else:
                    print(bcolors.FAIL + "{} {} {} {} Error Occurred While Applying Gift Card".format(now(), self.id, self.proxy_ip, response.status_code) + bcolors.ENDC)
                    return
            self.update_cookies()
            self.tried_giftcards.append(i)
            try:
                error = response.json()['body']['checkout']['billing']['billingOptions']['selectedBillingOptions']['giftCard']['giftCardInput']['m'][0]['text']
                if error:
                    print(bcolors.FAIL + "{} {} {} 無法提交禮品卡 {}. {} {}".format(now(), self.id, self.proxy_ip, i, error, self.latency(request_time, response_time)) + bcolors.ENDC)
                    continue
            except:
                pass
            try:
                gc_num = response.json()['body']['checkout']['billing']['billingOptions']['selectedBillingOptions']['giftCard']['c'][self.gcindex]
                amount = response.json()['body']['checkout']['billing']['billingOptions']['selectedBillingOptions']['giftCard'][gc_num]['d']['amount']
                remaining_balance = response.json()['body']['checkout']['billing']['billingOptions']['selectedBillingOptions']['giftCard'][gc_num]['d']['remainingBalance']
                pin = response.json()['body']['checkout']['billing']['billingOptions']['selectedBillingOptions']['giftCard'][gc_num]['d']['pin']
                print(bcolors.HEADER + "{} {} {} 成功提交禮品卡 {} 扣除:{} 餘額:{} {}".format(now(), self.id, self.proxy_ip, pin[-4:], amount, remaining_balance, self.latency(request_time, response_time)) + bcolors.ENDC)
                self.gcindex += 1
                self.applied_giftcards.append(i)
            except:
                print(bcolors.FAIL + "{} {} {} 未能提交禮品卡 此物品已售罄.".format(now(), self.id, self.proxy_ip) + bcolors.ENDC)
                return False
            try:
                cannotAddGC = response.json()['body']['checkout']['billing']['billingOptions']['selectedBillingOptions']['giftCard']['d']['cannotAddGiftCardMessage']
                print(bcolors.HEADER + "{} {} {} {}".format(now(), self.id, self.proxy_ip, cannotAddGC) + bcolors.ENDC)
                return True
            except:
                continue
        try:
            cannotAddGC = response.json()['body']['checkout']['billing']['billingOptions']['selectedBillingOptions']['giftCard']['d']['cannotAddGiftCardMessage']
            print(bcolors.HEADER + "{} {} {} {}".format(now(), self.id, self.proxy_ip, cannotAddGC) + bcolors.ENDC)
            return True
        except:
            print(bcolors.FAIL + "{} {} {} 此組禮品卡餘額不足，將從禮品卡池提取下一組禮品卡嘗試完成支付。".format(now(), self.id, self.proxy_ip) + bcolors.ENDC)
            self.giftcard = None
            return self.post_payment_giftcard()

    def post_payment_credit(self):
        self.referrer = "https://{}.store.apple.com/hk-zh/shop/checkout?_s=Billing-init".format(self.endpoint)
        self.update_cookies()
        response = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=selectBillingOptionAction&_m=checkout.billing.billingOptions&checkout.billing.billingOptions.selectBillingOption=CREDIT&checkout.billing.billingOptions.selectedBillingOptions.giftCard.giftCardInput.deviceID={}&checkout.billing.billingOptions.selectedBillingOptions.giftCard.giftCardInput.giftCard='.format(self.endpoint, self.deviceID), headers=self.get_headers_post())
        self.update_cookies()
        encryption = response.json()['body']['checkout']['billing']['billingOptions']['selectedBillingOptions']['creditCard']['cardInputs']['cardInput-0']['d']['encryption']['config']
        publicKey = encryption['publicKey']
        publicKeyHash = encryption['publicKeyHash']
        print(publicKey, publicKeyHash)
        #response = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=checkCreditCardTypeAction&_m=checkout.billing.billingOptions.selectedBillingOptions.creditCard.cardInputs.cardInput-0&checkout.billing.billingOptions.selectedBillingOptions.creditCard.cardInputs.cardInput-0.cardNumberForBinDetection=5289%2046&checkout.billing.billingOptions.selectedBillingOptions.creditCard.cardInputs.cardInput-0.selectCardType=MASTERCARD'.format(self.endpoint), headers=self.get_headers_post())
        #print(response.status_code)
        #print(response.json())
        '''lastName = urllib.parse.quote(self.creditCard['CARD_LASTNAME'], safe='')
        firstName = urllib.parse.quote(self.creditCard['CARD_FIRSTNAME'], safe='')
        address = urllib.parse.quote(self.creditCard['CARD_ADDRESS_ST'], safe='')
        card_type = urllib.parse.quote(self.creditCard['CARD_TYPE'], safe='')
        securityCode = urllib.parse.quote(self.creditCard['CARD_CVV'], safe='')
        expiration = urllib.parse.quote(self.creditCard['CARD_EXP'], safe='')
        cardNumber = urllib.parse.quote(self.creditCard['CARD_NUMBER'], safe='')
        print(lastName, firstName, address, card_type, securityCode, expiration, cardNumber)
        request_time = datetime.now()
        response = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=continue&_m=checkout.billing&checkout.billing.billingOptions.selectBillingOption=CREDIT&checkout.billing.billingOptions.selectedBillingOptions.creditCard.billingAddress.address.street2=&checkout.billing.billingOptions.selectedBillingOptions.creditCard.billingAddress.address.lastName={}&checkout.billing.billingOptions.selectedBillingOptions.creditCard.billingAddress.address.firstName={}&checkout.billing.billingOptions.selectedBillingOptions.creditCard.billingAddress.address.street={}&checkout.billing.billingOptions.selectedBillingOptions.creditCard.cardInputs.cardInput-0.selectCardType={}&checkout.billing.billingOptions.selectedBillingOptions.creditCard.cardInputs.cardInput-0.securityCode={}&checkout.billing.billingOptions.selectedBillingOptions.creditCard.cardInputs.cardInput-0.expiration={}&checkout.billing.billingOptions.selectedBillingOptions.creditCard.cardInputs.cardInput-0.cardNumber={}&checkout.billing.billingOptions.selectedBillingOptions.giftCard.giftCardInput.deviceID={}&checkout.billing.billingOptions.selectedBillingOptions.giftCard.giftCardInput.giftCard='.format(self.endpoint, lastName, firstName, address, card_type, securityCode, expiration, cardNumber, self.deviceID), headers=self.get_headers_post())
        response_time = datetime.now()
        print(response.status_code)
        print(response.json())'''
        self.chrome.driver.get('https://{}.store.apple.com/hk-zh/shop/checkout?_s=Billing-init'.format(self.endpoint))
        time.sleep(3000)
        self.update_cookies()
        if response.status_code != 200:
            if response.status_code == 503:
                self.switch_checkout_proxy()
                self.post_payment_credit()
            print(bcolors.FAIL + "{} {} {} Error Occurred While CREDIT CARD. Retrying Payment".format(now(), self.id, response.status_code) + bcolors.ENDC)
        print(bcolors.HEADER + "{} {} 成功提交信用卡信息".format(now(), self.id) + bcolors.ENDC)
        return True



    def post_confirm_order(self):
        self.referrer = "https://{}.store.apple.com/hk-zh/shop/checkout?_s=Review".format(self.endpoint)
        while True:
            response, request_time, response_time = self.post_order_submit()
            if response.status_code == 503:
                self.switch_checkout_proxy()
                print(bcolors.FAIL + "{} {} {} {} Error Occurred While Submitting Order. Re-Submitting Order".format(now(), self.id, self.proxy_ip, response.status_code) + bcolors.ENDC)
                continue
            try:
                self.update_cookies()
                submitOrderStatus = response.json()['head']['status']
                submitOrderRedirect = response.json()['head']['data']['url']
                if submitOrderStatus and submitOrderRedirect:
                    print(bcolors.HEADER + "{} {} {} Order Submitted. {}".format(now(), self.id, self.proxy_ip, self.latency(request_time, response_time)) + bcolors.ENDC)
                break
            except KeyError:
                print(bcolors.FAIL + "{} {} {} Unable To Submit Order.".format(now(), self.id, self.proxy_ip) + bcolors.ENDC)
                break

    def post_order_submit(self):
        request_time = datetime.now()
        response = self.checkout_session.request('POST', 'https://{}.store.apple.com/hk-zh/shop/checkoutx?_a=continue&_m=checkout.review.placeOrder'.format(self.endpoint), headers=self.get_headers_post())
        response_time = datetime.now()
        return response, request_time, response_time

    def postorder_analysis(self):
        wait = WebDriverWait(self.chrome.driver, 30)
        self.chrome.driver.get("https://{}.store.apple.com/hk-zh/shop/checkout/status".format(self.endpoint))
        timeout = time.time()
        while True:
            currentUrl = self.chrome.driver.current_url
            if (currentUrl != "https://{}.store.apple.com/hk-zh/shop/checkout/status".format(self.endpoint) and currentUrl != "https://{}.store.apple.com/hk-zh/shop/checkout/status?_s=Process".format(self.endpoint)) or time.time() - timeout >= 30:
                break
            time.sleep(0.5)

        if currentUrl == 'https://{}.store.apple.com/hk-zh/shop/checkout/thankyou'.format(self.endpoint):
            orderNumber = self.get_order_number()
            print(bcolors.WARNING + "{} {} Order Successfully Submitted. Order Number: {}".format(now(), self.id, orderNumber) + bcolors.ENDC)
            self.chrome.driver.save_screenshot("SUCCESS_{}_{}.png".format(datetime.now().strftime("%H%M%S"), orderNumber))
            return orderNumber

        elif currentUrl == 'https://{}.store.apple.com/hk-zh/shop/checkout?_s=Fulfillment'.format(self.endpoint):
            try:
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'rs-fulfillment-forceddeliveryonly')))
                print(bcolors.WARNING + "{} {} Order Submission Failed, AOS Delivery Only.".format(now(), self.id) + bcolors.ENDC)
                return 'AOS_DELIVERY_ONLY'
            except:
                self.chrome.driver.save_screenshot("UNKNOWN_{}.png".format(datetime.now().strftime("%H%M%S")))
                return
        self.chrome.driver.save_screenshot("UNKNOWN_{}.png".format(datetime.now().strftime("%H%M%S")))
        return

    def get_order_number(self, retries=0):
        wait = WebDriverWait(self.chrome.driver, 30)
        if retries <= 3:
            try:
                wait.until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'rs-thankyou-ordernumber')))
                order_number = self.chrome.driver.find_element_by_class_name('rs-thankyou-ordernumber').get_attribute("innerHTML").split()
                return order_number[1]
            except:
                time.sleep(10)
                self.chrome.driver.refresh()
                return self.get_order_number(retries+1)
        return 'NOTFOUND'

    def update_cookies(self):
        session_cookies_dict = self.checkout_session.cookies.get_dict()
        for key, value in session_cookies_dict.items():
            self.cookies[key] = value

    def switch_checkout_proxy(self):
        new_proxy = self.checkout_proxy_queue.get()
        self.checkout_proxy_queue.put(new_proxy)
        self.checkout_proxy_used = new_proxy
        self.checkout_session.proxies = {'https': 'https://{}'.format(new_proxy)}
        self.proxy_ip = new_proxy
        if not SUPPRESS_MONITOR_PROXY_SWITCH_MSG:
            print("{} {} Switching Proxy to: {}".format(now(), self.id, new_proxy))

    def switch_monitor_proxy(self):
        new_proxy = self.monitor_proxy_queue.get()
        self.monitor_proxy_queue.put(new_proxy)
        self.monitor_session.proxies = {'https': 'https://{}'.format(new_proxy)}
        if not SUPPRESS_MONITOR_PROXY_SWITCH_MSG:
            print("{} {} Switching MONITOR proxy to: {}".format(now(), self.id, new_proxy))

    def get_headers_post(self):
        headers_post = {
            "Connection": "keep-alive",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36',
            "syntax": "graviton",
            "modelversion": "v2",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "origin": "https://{}.store.apple.com".format(self.endpoint),
            "referer": self.referrer,
            "host": "{}.store.apple.com".format(self.endpoint),
            "x-aos-model-page": 'checkoutPage',
            "x-aos-stk": self.x_aos_stk,
            "x-requested-with": "XMLHttpRequest",
            "cookie": cookie_header_format(self.cookies),
        }
        return headers_post

    def get_headers_get(self):
        headers_get = {
            "Connection": "keep-alive",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "origin": "https://{}.store.apple.com".format(self.endpoint),
            "host": "{}.store.apple.com".format(self.endpoint),
            "cookie": cookie_header_format(self.cookies),
        }
        return headers_get

    def latency(self, start, end):
        rtt = round((end - start).total_seconds()*1000)
        self.latencyTimeTotal += rtt
        return '延遲{}ms'.format(rtt)

    def deviceID(self):
        return urllib.parse.quote('TF1;015;;;;;;;;;;;;;;;;;;;;;;Mozilla;Netscape;5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36;20030107;undefined;true;;true;Win32;undefined;Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36;en-US;undefined;{}.store.apple.com;undefined;undefined;undefined;undefined;false;false;{};8;6/7/2005, 9:33:44 PM;2560;1440;;;;;;;;-480;-480;{},{};24;2560;1400;-2560;0;;;;;;;;;;;;;;;;;;;25;'.format('secure1', int(time.time()), datetime.strftime(datetime.now(), '%m/%d/%Y'), datetime.now().strftime(' %I:%M:%S %p')))
