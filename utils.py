"""
 Copyright (C) 2020 Arnold Lam - All Rights Reserved
 Unauthorized distribution of this file, via any medium is strictly prohibited.
"""
from config import RANDOM_PHONE, RANDOM_EMAIL, RANDOM_EMAIL_DOMAIN
from datetime import datetime
from multiprocessing import Queue
import csv
import random


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_inputs():
    monitor_proxy_queue = Queue()
    startup_proxy_queue = Queue()
    checkout_proxy_queue = get_checkout_proxy_queue()
    monitor_proxies = read_proxies('MONITOR')
    startup_proxies = read_proxies('STARTUP')
    orders = read_csv('orders')
    if len(orders) == 0:
        exit("INIT ERROR: NO ORDERS WERE FOUND IN ORDERS.CSV")
    if len(monitor_proxies) == 0:
        exit("INIT ERROR: NO PROXIES WERE FOUND IN POLLINGPROXIES.CSV")
    if len(startup_proxies) == 0:
        exit("INIT ERROR: NO PROXIES WERE FOUND IN STARTUPPROXIES.CSV")
    for i in monitor_proxies:
        monitor_proxy_queue.put(i)
    for i in startup_proxies:
        startup_proxy_queue.put(i)
    return orders, checkout_proxy_queue, startup_proxy_queue, monitor_proxy_queue


def get_checkout_proxy_queue():
    checkout_proxy_queue = Queue()
    checkout_proxies = read_proxies('CHECKOUT')
    if len(checkout_proxies) == 0:
        exit("INIT ERROR: NO PROXIES WERE FOUND IN ORDERPROXIES.CSV")
    for i in checkout_proxies:
        checkout_proxy_queue.put(i)
    return checkout_proxy_queue

def get_contacts():
    contacts = {}
    contacts['name'] = read_csv('names')
    if RANDOM_EMAIL:
        contacts['email'] = ''
    else:
        contacts['email'] = read_csv('emails')
    if RANDOM_PHONE:
        contacts['phone'] = ''
    else:
        contacts['phone'] = read_csv('phones')
    if len(contacts['name']) == 0:
        exit("INIT ERROR: NO PICKUP CONTACT NAMES WERE FOUND IN PICKUPNAMES.CSV")
    if len(contacts['email']) == 0 and not RANDOM_EMAIL:
        exit("INIT ERROR: NO PICKUP CONTACT EMAILS WERE FOUND IN EMAIL.CSV")
    if len(contacts['phone']) == 0 and not RANDOM_PHONE:
        exit("INIT ERROR: NO PICKUP CONTACT PHONES WERE FOUND IN PHONENUMBERS.CSV")
    return contacts

def get_giftcards_pool():
    giftcards_queue = []
    giftcards = read_csv('giftcards')
    for i in giftcards:
        giftcards_queue.append(i)
    return giftcards_queue

def format_proxy_address(ip):
    if ip:
        splitted = ip.split(':')
        if len(splitted) == 4:
            return splitted[2] + ':' + splitted[3] + '@' + splitted[0] + ':' + splitted[1]
        return ip
    return ip

def read_proxies(type):
    if type == 'MONITOR':
        f = './csv/pollingproxies.csv'
    elif type == 'CHECKOUT':
        f = './csv/orderproxies.csv'
    elif type == 'STARTUP':
        f = './csv/startupproxies.csv'
    with open(f, 'r') as f:
        proxies = [format_proxy_address(l.rstrip('\n')) for l in f]
        del proxies[0]
        random.shuffle(proxies)
        return proxies

def read_csv(type):
    if type == 'orders':
        with open('./csv/orders.csv') as f:
            orders = [{k: v for k, v in r.items()}
                 for r in csv.DictReader(f, skipinitialspace=True)]
            return orders

    if type == 'names':
        with open('./csv/names.csv', encoding="utf-8") as f:
            contacts = [{k: v for k, v in r.items()} for r in csv.DictReader(f, skipinitialspace=True)]
            return contacts

    elif type == 'emails':
        with open('./csv/emails.csv') as f:
            emails = [l.rstrip('\n') for l in f]
            del emails[0]
            return emails

    elif type == 'phones':
        with open('./csv/phones.csv') as f:
            phoneNumbers = [l.rstrip('\n') for l in f]
            del phoneNumbers[0]
            return phoneNumbers

    elif type == 'creditcards':
        with open('./csv/creditcards.csv') as f:
            creditCards = [{k: v for k, v in r.items()} for r in csv.DictReader(f, skipinitialspace=True)]
            return creditCards

    elif type == 'giftcards':
        with open('./csv/giftcards.csv') as f:
            giftCards = [l.rstrip('\n').replace(' ', '').split('/') for l in f]
            random.shuffle(giftCards)
            return giftCards

def cookie_header_format(cookie_dict):
    cookie_string = ''
    for key, value in cookie_dict.items():
        cookie_string += key + '=' + value + '; '
    return cookie_string

def remove_entry(file, value):
    if type(value) != dict:
        lines = list()
        with open(file, 'r', encoding="utf-8") as f:
            reader = csv.reader(l.replace('\0', '') for l in f)
            for row in reader:
                lines.append(row)
                for field in row:
                    if field == value:
                        lines.remove(row)
            f.close()
        with open(file, 'w', encoding="utf-8", newline='') as f:
            writer = csv.writer(f)
            writer.writerows(lines)
            f.close()
    else:
        contacts = read_csv('names')
        with open(file, 'w', encoding="utf-8", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['firstName', 'lastName'])
            writer.writeheader()
            for contact in contacts:
                if value != contact:
                    writer.writerow(contact)
            f.close()

def verify_inputs():
    if RANDOM_EMAIL and not RANDOM_EMAIL_DOMAIN:
        exit("請先設定 RANDOM_EMAIL_DOMAIN 或取消 RANDOM_EMAIL 選項")


def now():
    return datetime.now().strftime('%H:%M:%S.%f')[:-3]