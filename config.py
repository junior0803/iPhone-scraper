VERSION = '1.4.2'

# TELEGRAM_NOTIF_CHAT_ID
# TELEGRAM通知的USER ID
TELEGRAM_NOTIF_CHAT_ID = ''

# TELEGRAM_NOTIF_USERID
# 於公開頻度顯示的暱稱
TELEGRAM_NOTIF_USERID = 'Hidden User'

# TELEGRAM_NOTIF_VPSID
#
TELEGRAM_NOTIF_VPSID = 'VPS 1'

# CHROME_CLICK_SPEED_MODIFIER
# 按鍵速度 這項設定決定程式對瀏覽器操作的速度 增加此倍數能有效減少出現瀏覽器輸入途中出現紅字ERROR問題 這些設定因每人電腦配置而異。
CHROME_CLICK_SPEED_MODIFIER = 1

# PROCESS_CREATE_INTERVAL
# 啟動線程等待時間 對於硬件配置低的電腦 調高此設定可增加程式能夠運行的TASKS
PROCESS_CREATE_INTERVAL = 15

# PROCESS_RESTART_TIMER
# 自動重啟結帳程序 (分鐘)
PROCESS_RESTART_TIMER = 60

# MONITOR_POLLING_INTERVAL
# 掃描器冷卻時間(秒) 此數值入過低有可能導致400錯誤碼
MONITOR_POLLING_INTERVAL = 0.25

# CHECKOUT_ENDPOINT_SELECTION
# 選擇Checkout時所選擇的Apple服務器分區
# 只有 1 2 4 可選 不能夠填寫3 或其他數值
# Example: 1 / 2 / 4
CHECKOUT_ENDPOINT_SELECTION = 1

# SUPPRESS_MONITOR_PROXY_SWITCH_MSG
# 設定隱藏Monitor Proxy切換信息 True / False
SUPPRESS_MONITOR_PROXY_SWITCH_MSG = False

# NAME_OBFUSCATION
# 隨機生成姓名英文字串 (Chan, Tai Man dkc / Chan, Tai Man pfg)
NAME_OBFUSCATION = False

# NAME_OBFUSCATION_LENGTH
# 隨機生成姓名英文字串長度
NAME_OBFUSCATION_LENGTH = 5

# NAME_OBFUSCATION_POSITION
# 隨機生成英文字串位置 'first' / 'last'
NAME_OBFUSCATION_POSITION = 'first'

# RANDOM_PHONE
# 隨機生成電話號碼 e.g 91287342
RANDOM_PHONE = False

# RANDOM_EMAIL
# 隨機生成亂碼EMAIL地址 e.g ckdjauh@abc.com
RANDOM_EMAIL = False

# RANDOM_EMAIL_DOMAIN
# 隨機生成電郵地址之DOMAIN e.g ABC.com
RANDOM_EMAIL_DOMAIN = ''

# RANDOM_EMAIL_PREFIX
# 隨機生成電郵地址之前綴 e.g abc_xxxxx@abc.com
RANDOM_EMAIL_PREFIX = 'abc_'

# HIDE_BROWSER
# 設定隱藏瀏覽器 True / False
HIDE_BROWSER = True

# REMOVE_ORDER_PROXIES
# 從orderproxies.csv移除已使用的Order Proxy
REMOVE_ORDER_PROXIES = False

# IFC
STORE_ENABLE_R428 = True
# FW
STORE_ENABLE_R485 = True
# CR
STORE_ENABLE_R499 = True
# NTP
STORE_ENABLE_R610 = True
# APM
STORE_ENABLE_R673 = True
# CWB
STORE_ENABLE_R409 = True

# ADVANCE_PAY
# 先結帳 後搶單模式
ADVANCE_PAY = False

# SHIPPING_STREET_ADDRESS and SHIPPING_STREET_BLDG
# 這兩個設定將設定Checkout過程時所需要填寫的送貨地址 建議自行更改以免出現信息重複的問題從而被CUT單
ADVANCE_PAY_SHIPPING_ADDRESS_ST = "100 Nathan Road"

# LIVE_MODE
# 測試模式 需要填寫True 程式才會真實落單。否則，程式將在確認訂單前停止。
# Example: True / False
LIVE_MODE = False

