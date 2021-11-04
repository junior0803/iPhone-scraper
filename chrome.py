"""
 Copyright (C) 2020 Arnold Lam - All Rights Reserved
 Unauthorized distribution of this file, via any medium is strictly prohibited.
"""

from schema import SHOP_LINKS, XPATHS, CHECKOUT_SPECIAL_ITEMS, ENGRAVING_ITEMS
from config import CHECKOUT_ENDPOINT_SELECTION, CHROME_CLICK_SPEED_MODIFIER, HIDE_BROWSER, ADVANCE_PAY
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import *
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from datetime import datetime
from schema import USER_AGENTS
from utils import bcolors
import random
import json

x = CHROME_CLICK_SPEED_MODIFIER

class ChromeRunner:
    def __init__(self, process_id, proxy_ip, order):
        self.id = process_id
        self.proxy_ip = proxy_ip
        self.order = order
        self.x_aos_stk = None
        self.checkout_api_request_cookies = {}
        self.driver = self.initBrowser()

    def start(self):
        print("{} Starting Chrome Session With ORDER PROXY".format(self.id))
        try:
            self.endpoint_init()
            pre_checkout = self.pre_checkout_flow()
            if not pre_checkout:
                return
            method_select = self.checkout_method_select()
            if not method_select:
                return
            cookies_list = self.driver.get_cookies()
            for cookie in cookies_list:
                self.checkout_api_request_cookies[cookie['name']] = cookie['value']
            self.find_x_aos_stk()
            self.checkout_endpoint = self.driver.current_url.split('.')[0].replace('https://', '')
            return self.driver

        except (NoSuchElementException, TimeoutException) as e:
            self.driver.save_screenshot("CHROME_ERROR_CHECKOUT_{}.png".format(datetime.now().strftime("%m%d%Y%H%M%S")))
            self.driver.quit()
            print("{} AN ERROR HAS OCCURED WHILE INITIALIZING CHECKOUT SESSION. THERE MAY BE INPUT ERROR".format(self.id, e))
            return

        except:
            return

    def endpoint_init(self):
        self.driver.get('https://secure{}.store.apple.com'.format(CHECKOUT_ENDPOINT_SELECTION))

    def pre_checkout_flow(self):
        wait = WebDriverWait(self.driver, 5)
        for k in range(int(self.order['quantity'])):
            self.driver.get(SHOP_LINKS[self.order['model']])
            try:
                if self.order['model'] in ENGRAVING_ITEMS:
                    wait.until(EC.presence_of_element_located((By.XPATH,'/html/body/div[2]/div[5]/div[3]/div[2]/div[3]/div[2]/div[3]/div/div/div/div[1]/div/fieldset/div/div[2]/label')))
                    self.driver.find_element_by_xpath('/html/body/div[2]/div[5]/div[3]/div[2]/div[3]/div[2]/div[3]/div/div/div/div[1]/div/fieldset/div/div[2]/label').click()
                wait.until(EC.presence_of_element_located((By.NAME, 'add-to-cart')))
                self.driver.find_element_by_name('add-to-cart').click()
                if self.order['model'] not in CHECKOUT_SPECIAL_ITEMS:
                    wait.until(EC.presence_of_element_located((By.XPATH, XPATHS['ITEM_PAGE_BAG_ICON'])))
                else:
                    wait.until(EC.presence_of_element_located((By.XPATH, XPATHS['HOMEPOD_ITEM_PAGE_BAG_ICON'])))
                break
            except:
                print("{} item page exception. Restarting Process".format(self.id))
                return
        while True:
            try:
                self.driver.get('https://www.apple.com/hk-zh/shop/bag')
                wait.until(EC.presence_of_element_located((By.ID, 'shoppingCart.actions.navCheckout')))
                self.driver.find_element_by_id('shoppingCart.actions.navCheckout').click()
                break
            except:
                print("{} 503 Error at checkout page. Retrying...".format(self.id))

        try:
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "rs-guestcheckout-header")))
            return True
        except:
            print("{} checkout exception. Restarting Process".format(self.id))
            return

    def checkout_method_select(self):
        wait = WebDriverWait(self.driver, 5)
        while True:
            try:
                if self.order['appleId_email']:
                    print(bcolors.OKBLUE + "{} 登入AppleID: {}".format(self.id, self.order['appleId_email']) + bcolors.ENDC)
                    self.driver.find_element_by_xpath(XPATHS['CHECKOUT_LOGIN_CREDENTIALS']).send_keys(self.order['appleId_email'] + Keys.TAB + self.order['appleId_password'] + Keys.TAB + Keys.ENTER)
                else:
                    print("{} 進入訪客模式".format(self.id))
                    self.driver.find_element_by_xpath(XPATHS['CHECKOUT_GUEST']).click()
                    wait.until(EC.presence_of_element_located((By.XPATH, XPATHS['CREDIT_SELECT_DELIVERY_METHOD'])))
                break
            except:
                print("{} checkout method exception. Restarting Process".format(self.id))
                return
        if not ADVANCE_PAY:
            while True:
                try:
                    wait.until(EC.presence_of_element_located((By.XPATH, XPATHS['CREDIT_SELECT_DELIVERY_METHOD'])))
                    self.driver.find_element_by_xpath(XPATHS['CHECKOUT_SELECT_PICKUP_OPTION']).click()
                    wait.until(EC.presence_of_element_located((By.XPATH, XPATHS['CHECKOUT_LOCATION_SEARCH_INPUT'])))
                    self.driver.find_element_by_xpath(XPATHS['CHECKOUT_LOCATION_SEARCH_INPUT']).send_keys('Tsim Sha Tsui' + Keys.ENTER)
                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'rs-store-locator')))
                    return True
                except:
                    print("{} delivery method exception. Restarting Process".format(self.id))
                    return
        else:
            return True

    def find_x_aos_stk(self):
        init_data = self.driver.find_elements_by_id('init_data')
        if len(init_data) != 0:
            attributes = json.loads(init_data[0].get_attribute('innerHTML'))
            self.x_aos_stk = attributes['meta']['h']['x-aos-stk']
            print(self.id, "Chrome Session Initialization Complete")
        else:
            self.driver.quit()
            exit("{} CHECKOUT SESSION INITIALIZATION FAILED: INIT x-aos-stk NOT FOUND!".format(self.id))

    def initBrowser(self):
        options = Options()
        options.add_argument('--proxy-server={}'.format(self.proxy_ip))
        print(bcolors.OKBLUE + "{} 開始進行加車 Proxy: {}".format(self.id, self.proxy_ip) + bcolors.ENDC)
        options.add_argument('--allow-running-insecure-content')
        options.add_argument("--window-size=1920,1080")
        options.add_argument('--disable-gpu')
        options.add_argument('--incognito')
        options.add_argument('--user-agent={}'.format(random.choice(USER_AGENTS)))
        options.headless = HIDE_BROWSER
        return webdriver.Chrome(ChromeDriverManager().install(), options=options)