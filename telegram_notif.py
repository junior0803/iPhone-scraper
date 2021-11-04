"""
 Copyright (C) 2020 Arnold Lam - All Rights Reserved
 Unauthorized distribution of this file, via any medium is strictly prohibited.
"""

from config import VERSION, TELEGRAM_NOTIF_CHAT_ID, TELEGRAM_NOTIF_VPSID
from schema import TELEGRAM_URL
import requests
import time


class TGHandler:
    def __init__(self, tg_msg_queue):
        self.tg_msg_queue = tg_msg_queue
        self.private_chat_enabled = False
        if TELEGRAM_NOTIF_CHAT_ID and len(TELEGRAM_NOTIF_CHAT_ID) < 16:
            self.private_chat_enabled = True
            self.send_msg(TELEGRAM_NOTIF_VPSID + ": Starting up GT BOT {}".format(VERSION))
        elif TELEGRAM_NOTIF_CHAT_ID:
            self.send_msg("請使用少於16位的USERID 以免洗頻")
        self.monitor()

    def monitor(self):
        private_msg = []
        public_msg = []
        while True:
            while self.tg_msg_queue.qsize() != 0:
                new_msg = self.tg_msg_queue.get()
                if new_msg['msg_type'] == 'public':
                    public_msg.append(new_msg)
                else:
                    private_msg.append(new_msg)

            if len(private_msg) != 0 and self.private_chat_enabled:
                msg = private_msg.pop(0)
            elif len(public_msg) != 0:
                msg = public_msg.pop(0)
            else:
                time.sleep(5)
                continue

            if not self.send_msg(msg['msg'], msg['msg_type']):
                if msg['msg_type'] == 'public':
                    public_msg.insert(0, msg)
                else:
                    private_msg.insert(0, msg)


    def send_msg(self, msg, msg_type='private'):
        # PUBLIC GROUP CHAT ID -483924452
        # TEST GROUP CHAT ID -487986465

        if msg_type == 'public':
            params = (
                ('chat_id', '-483924452'),
                ('text', f"{msg}"),
                ('parse_mode', 'Markdown'),
                ('disable_web_page_preview', 'yes')
            )
            response = requests.post(TELEGRAM_URL, params=params)
            if response.status_code != 200:
                return
        else:
            params = (
                ('chat_id', TELEGRAM_NOTIF_CHAT_ID),
                ('text', f"{msg}"),
                ('parse_mode', 'Markdown'),
                ('disable_web_page_preview', 'yes')
            )
            response = requests.post(TELEGRAM_URL, params=params)
            if response.status_code != 200:
                return
        return True
