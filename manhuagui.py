# -*- coding: utf-8 -*-
from colorprint import *

from time import time, sleep
from queue import Queue
from fake_useragent import UserAgent
from threading import Thread
from random import random
import os, re, requests, json, argparse
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


parser = argparse.ArgumentParser(description="說明(空)", epilog="章節格式b24%13, 指單行第24個13頁, 可用-f查詢")
parser.add_argument("-a", action="store_true", help="顯示現有資料庫")
parser.add_argument("-i", nargs="+", type=str, help="指定的編號")
parser.add_argument("-f", action="store_true", help="顯示-i的完整資料")
parser.add_argument("-d", action="store_true", help="收集-i後的資料, 可為多個")
parser.add_argument("-c", type=str, help="連續下載，參數為起始點")
parser.add_argument("-e", type=str, help="指定下載，參數為範圍, 用','和'-'表示")

Path_data = "./data/"
UA = UserAgent(browsers=["chrome", "edge", "firefox", "safari", "opera"])

def prepare_sele(unseen: bool):
    global driver, headers
    print("準備瀏覽器中...")
    service = Service("../Selenium_firefox/geckodriver.exe")
    opts = Options()
    opts.binary_location = "../Selenium_firefox/firefox/firefox.exe"
    if unseen:
        opts.add_argument("-headless")
    driver = webdriver.Firefox(service=service,options=opts)
    headers = {"User-Agent":UA.random, "referer":"https://tw.manhuagui.com"}
    print("準備完成")
    return driver, headers

def collect_data(URL: str): # by selenium
    # list內：{"Name":"", "Chap-url":"", "Page":""}
    data = {
        "Title": "",
        "URL": "",
        "Chapter-list": [], 
        "Volume-list": [],
        "Other-list": [],
        "Lasttime-name": "",
        "Lasttime-page": ""
    }
    print("連線中...")
    driver.get(f"https://tw.manhuagui.com/comic/{URL}")
    print("連線完成")
    try: #check adult
        driver.find_element(By.XPATH, f"//div[@class='warning-bar']/a").click()
    except:
        pass

    data["Title"] = driver.find_element(By.TAG_NAME,"h1").text.replace("/", "_")
    data["URL"] = URL
    # 找章節種類、是否有分頁
    Ctype = list(i.text for i in driver.find_elements(By.TAG_NAME, "h4"))
    structure = driver.find_elements(By.XPATH, f"//div[@class='chapter-page cf mt10' or @class='chapter-list cf mt10']")
    
    # 收集資料
    btns = [] #如果有分頁就收集按鈕，用完刪除
    c1 = c2 = 1 #第n次動作，用於xpath定位，分屬兩個class
    for i in structure:
        if i.get_attribute("class") == "chapter-page cf mt10": #收集分頁按鈕
            btns = driver.find_elements(By.XPATH, f"//div[@class='chapter-page cf mt10'][{c1}]/ul/li/a")
            c1 += 1
        elif i.get_attribute("class") == "chapter-list cf mt10": #收集章節資料
            r = ("單話", "单话", "單行本", "单行本", "番外篇")
            if Ctype[c2-1] not in r:
                raise ValueError(f"'{Ctype[c2-1]}'不知道該被放到哪裡QQ")
            key = ["Chapter-list", "Volume-list", "Other-list"][r.index(Ctype[c2-1])//2] #決定等一下資料去哪

            if len(btns) == 0: #無分頁
                t1 = driver.find_elements(By.XPATH, f"//div[@class='chapter-list cf mt10'][{c2}]/ul/li/a") #標題、連結
                t2 = driver.find_elements(By.XPATH, f"//div[@class='chapter-list cf mt10'][{c2}]/ul/li/a/span/i") #頁數
                if len(t1) == 0:
                    raise ValueError(f"i={c2}時找不到連結與標題資料!請重新確定路徑。")
                if len(t2) == 0:
                    raise ValueError(f"i={c2}時找不到頁數資料!請重新確定路徑。")
                
                for p, q in zip(t1, t2):
                    # 連結舉例: https://tw.manhuagui.com/comic/25778/354793.html
                    data[key].append(
                        {
                            "Name": p.get_attribute("title"),
                            "Chap-url": re.search(r"([\d]+).html", p.get_attribute("href")).group(1),
                            "Page": q.text.strip("p")
                        }
                    )
            else: #有分頁
                while len(btns) > 0:
                    btns.pop().click() # 選一個分頁
                    sleep(0.3)
                    
                    t1 = driver.find_elements(By.XPATH, f"//div[@class='chapter-list cf mt10'][{c2}]/ul[@style='display:block']/li/a")
                    t2 = driver.find_elements(By.XPATH, f"//div[@class='chapter-list cf mt10'][{c2}]/ul[@style='display:block']/li/a/span/i")
                    #ul的style有兩種可能display:block或display: block;
                    if len(t1) == 0:
                        t1 = driver.find_elements(By.XPATH, f"//div[@class='chapter-list cf mt10'][{c2}]/ul[@style='display: block;']/li/a")
                        if len(t1) == 0:
                            raise ValueError(f"i={c2}時找不到連結與標題資料!請重新確定路徑。")
                    if len(t2) == 0:
                        t2 = driver.find_elements(By.XPATH, f"//div[@class='chapter-list cf mt10'][{c2}]/ul[@style='display: block;']/li/a/span/i")
                        if len(t2) == 0:
                            raise ValueError(f"i={c2}時找不到頁數資料!請重新確定路徑。")
                    
                    for p, q in zip(t1, t2):
                        # 連結舉例: https://tw.manhuagui.com/comic/25778/354793.html
                        data[key].append(
                            {
                                "Name": p.get_attribute("title"),
                                "Chap-url": re.search(r"([\d]+).html", p.get_attribute("href")).group(1),
                                "Page": q.text.strip("p")
                            }
                        )
            c2 += 1
    # 排序
    def order(x): ## 排序法，以數字表示章節數
        a = re.search("([\d\.]+)", x)
        if a is not None:
            return float(a.group(1))
        else:
            return 10000 # 放到最後
    for key in ("Chapter-list", "Volume-list"):
        if len(data[key]) != 0:
            data[key] = sorted(data[key], key = lambda x: order(x["Name"]))

    # 存檔
    os.makedirs(Path_data, 0o777, exist_ok=True)
    if os.path.isfile(Path_data + f"{data['Title']}.json"):
        a = input("是否覆蓋?(y/n)")
        if a == "n":
            print("已捨棄本次爬蟲內容")
            return
    ## 當作else
    with open(Path_data + f"{data['Title']}.json", "w", encoding="utf8") as f:
        f.write(json.dumps(data, sort_keys=True, ensure_ascii=False, indent=4, separators=(",", ": ")))
    return

def length_3(x) -> str:
	x = str(x)
	while len(x) < 3:
		x = "0" + x
	return x


class commander:
    corr = {"a": "Chapter-list","b": "Volume-list", "c": "Other-list"} # 參數代碼與種類對照

    def __init__(self, data: dict) -> None:
        '''
        data = {
        "Title": "",
        "URL": "",
        "Chapter-list": [], 
        "Volume-list": [],
        "Other-list": [],
        "Lasttime-name": "",
        "Lasttime-page": ""
        }
        網址結構:
        https://tw.manhuagui.com/comic/{漫畫}/{章節}.html#p={頁數}
        '''
        self.data = data
        self.url_front = "https://tw.manhuagui.com/comic/" + self.data["URL"] + "/"
        self.path_front = "./" + self.data["Title"] + "/"
        self.oncrawling = True
        self.forcestop = False
        self.url_que = Queue() # 存圖片真正位址
        self.fail_item_que = Queue() # 存無法下載的圖片
        
        #做根資料夾
        os.makedirs("./"+self.data["Title"], 0o777, exist_ok=True)

    def extract(self, x: str): # 解析輸入的頁數代碼
        # a01%12 -> a, 1, 12
        a = x[1:].split("%")
        return x[0], int(a[0]), int(a[1])

    def get_realurl(self, di: dict, s_p = 1, e_p = 0):
        e_p = int(di["Page"]) if e_p==0 else e_p
        # 放di章節，從s_p開始放後面的頁數直到e_p(含)
        dir_path = self.path_front + di["Name"] + "/"
        first_page_url = self.url_front + di["Chap-url"] + ".html#p=" + str(s_p)
        driver.get(first_page_url) # 方法為none，未完全載入
        for pg in range(s_p, e_p+1):
            if self.forcestop:
                driver.quit()
                return
            filename = di["Name"] + length_3(pg) + ".jpg"
            realurl = ""
            s_time = time()
            while realurl == "": # 重複尋找真網址直到找到或10秒
                if time() - s_time > 10:
                    print(f"放棄{filename}, 太久")
                    break
                try:
                    realurl = driver.find_element(By.XPATH, "//div[@id='mangaBox']/img").get_attribute("src")
                    self.url_que.put({"path": dir_path, "name": filename, "url": realurl})
                    driver.find_element(By.XPATH, "//*[@id='next']").click() #下一頁
                    sleep(random()) # 避免被鎖
                except NoSuchElementException:
                    sleep(0.1)

    def mode_c(self, arg: str): # arg: -c後面的參數
        no_record = "" in (self.data["Lasttime-name"], self.data["Lasttime-page"])
        category = "" # 下載的類別
        start_ind = 9999 # 下載的index起始
        
        # 有指定起始頁
        if arg != "record":
            t, p, q = self.extract(arg)
            category = self.corr[t]
            # 先做完該章節
            start_ind = p-1
            self.get_realurl(self.data[category][start_ind], q)
            if start_ind != len(self.data[category])-1: # 不是最後一個
                start_ind += 1
            else:
                return
        
        # 無紀錄，從頭，默認單行->章節->特別
        elif no_record:
            for i in ("Volume-list", "Chapter-list", "Other-list"):
                if self.data[i] != []:
                    category = i
                    start_ind = 0
                    print("無紀錄，默認從" + self.data[i][0]["Name"] + "開始")
                    break
        
        # 有紀錄
        elif (not no_record) and arg == "record":
            ## 記錄點是還沒下載過的
            # 先做完該章節
            for cat in ("Volume-list", "Chapter-list", "Other-list"):
                k = list(map(lambda x: x["Name"], self.data[cat]))
                if self.data["Lasttime-name"] in k:
                    category = cat
                    start_ind = k.index(self.data["Lasttime-name"])
                    break
            self.get_realurl(self.data[category][start_ind], self.data["Lasttime-page"])
            if start_ind != len(k)-1: # 不是最後一個
                start_ind += 1
            else:
                return

        else:
            raise ValueError("下載: 參數錯誤")

        # 後面的章節
        for di in self.data[category][start_ind:]:
            self.get_realurl(di)
        self.end_crawling()
        return

    def mode_e(self, arg: str): # arg: -e後面的參數
        for seg in arg.split(","):
            # 單頁
            if "-" not in seg:
                t, p, q = self.extract(seg)
                di = self.data[self.corr[t]][p-1]
                self.get_realurl(di, q, q)
            
            # 範圍
            else:
                t = seg.split("-")
                t1, p1, q1 = self.extract(t[0])
                t2, p2, q2 = self.extract(t[1])
                if t1 != t2:
                    raise ValueError("-e: 參數錯誤")
                k = self.data[self.corr[t1]]
                # 同章節
                if p1 == p2:
                    self.get_realurl(k[p1-1], q1, q2)
                
                # 跨章節
                else:
                    # 首
                    self.get_realurl(k[p1-1], q1)
                    # 中
                    if p1 < p2-1:
                        for di in k[p1:p2]:
                            self.get_realurl(di)
                    # 末
                    self.get_realurl(k[p2], 1, q2)
        self.end_crawling()
        return

    def end_crawling(self):
        print("End Crawing.")
        self.oncrawling = False
        driver.quit()

    def fail_item(self, info: dict):
        self.fail_item_que.put(info)
    
    def save(self):
        if self.url_que.empty():
            print("本次已下載完成其中一個type, 紀錄刪除")
            self.data["Lasttime-name"] = ""
            self.data["Lasttime-page"] = ""
        else:
            next_page = self.url_que.get()
            nm_pg = re.match("(.+[^\d])(\d+)", next_page["name"])
            self.data["Lasttime-name"] = nm_pg.group(1)
            self.data["Lasttime-page"] = nm_pg.group(2)
        with open(Path_data + self.data["Title"] + ".json", "w", encoding="utf8") as f:
            f.write(json.dumps(self.data, sort_keys=True, ensure_ascii=False, indent=4, separators=(",", ": ")))

    def get_status(self):
        if self.oncrawling:
            dcu = ""
            try: # 避免同步執行的時間差, 避免driver已關閉卻請求網址
                dcu = driver.current_url
            except:
                pass
            colorprint(f"Crawl-處理中:{dcu}, 倉庫{self.url_que.qsize()}張\n", FRG_BLUE)
        else:
            colorprint(f"Crawl-休息，剩餘{self.url_que.qsize()}張圖片\n", FRG_SKYBLUE)


class cell:
    def __init__(self, order: int, comm: commander) -> None:
        self.order = order
        self.commander = comm
        self.que = comm.url_que
        self.forcestop = False
        self.status = "Idle" # Idle, Downloading, Failed, Closed
        self.info = {"path": "", "name": "", "url": ""}

        self.headers = {"User-Agent": UA.random, "referer": "https://tw.manhuagui.com"}
        self.change_headers = 10 # 十張圖後改ua
    
    def run(self): # 根據status決定
        while self.status != "Closed":
            if self.forcestop:
                return
            
            elif self.status == "Idle":
                if self.change_headers == 0:
                    self.headers["User-Agent"] == UA.random
                    ## proxy??
                if self.que.qsize() != 0:
                    try:
                        self.info = self.que.get(block=False) # 因多線程可能取不到東西
                    except:
                        continue
                    self.que.task_done()
                    os.makedirs(self.info["path"], 0o777, exist_ok=True)
                    
                    # 下載
                    self.status = "Downloading"
                    r = requests.get(self.info["url"], headers=self.headers)
                    if r.ok:
                        with open(self.info["path"] + self.info["name"], "wb") as f:
                            f.write(r.content)
                        colorprint(f"Cell.{self.order}: {self.info['name']}完成\n", FRG_GREEN)
                        self.change_headers -= 1
                        self.status = "Idle"
                    else:
                        colorprint(f"Cell.{self.order}: {self.info['name']}失敗\n", FRG_RED)
                        self.status = "Failed"
                elif self.que.qsize() == 0 and not self.commander.oncrawling:
                    print(f"Cell.{self.order}關閉")
                    self.status = "Closed"
            
            elif self.status == "Failed":
                self.commander.fail_item(self.info)
                self.status = "Idle"


if __name__ == "__main__":
    args = parser.parse_args()
    js = [f for f in os.listdir(Path_data) if os.path.isfile(Path_data+f) and f.endswith(".json")]
    now_data= [] # 現有資料庫集(dict)
    for j in js:
        with open(Path_data+j, "r", encoding="utf8") as f:
            now_data.append(json.load(f))

    if args.a:
        # 顯示所有現有資料
        print("ComicName, Order, LastTimeRecord")
        for fj in now_data:
            if "" not in (fj["Lasttime-name"], fj["Lasttime-page"]):
                print(f"{fj['Title']}, {fj['URL']}, {fj['Lasttime-name']}第{fj['Lasttime-page']}頁")
            else:
                print(f"{fj['Title']}, {fj['URL']}, 無下載紀錄")
    
    elif args.d:
        # 收集資料
        driver, headers = prepare_sele(True)
        driver.get("https://tw.manhuagui.com/")
        driver.add_cookie({"name":"isAdult", "value":"1"}) # 先進網站才能加cookie
        for num in args.i:
            collect_data(num)
            print(f"完成{num}")
        driver.quit()

    elif args.f:
        # 顯示資料
        if len(args.i) != 1:
            raise ValueError("-i參數錯誤")
        aim = list(filter(lambda x: x["URL"].__eq__(args.i[0]), now_data))[0]
        print(f"名稱: {aim['Title']}, URL: {aim['URL']}")
        if "" not in (aim["Lasttime-name"], aim["Lasttime-page"]):
            print(f"上次下載至{aim['Lasttime-name']}第{aim['Lasttime-page']}頁")
        else:
            print("無下載紀錄")
        print("-"*40) # 分隔線
        print("Order, Name, Page")
        for head, typ in zip(("a", "b", "c"), ("Chapter-list", "Volume-list", "Other-list")):
            for order, di in enumerate(aim[typ], 1):
                print(f"{head}{order}, {di['Name']}, {di['Page']}")

    elif args.c is not None or args.e is not None:
        # 下載
        if len(args.i) != 1:
            raise ValueError("-i參數錯誤")
        aim = list(filter(lambda x: x["URL"].__eq__(args.i[0]), now_data))[0]
        driver, headers = prepare_sele(True)
        driver.get("https://tw.manhuagui.com/")
        driver.add_cookie({"name":"isAdult", "value":"1"}) # 先進網站才能加cookie
        Commander = commander(aim)
        
        # 爬蟲獲取真網址
        if args.c is not None:
            comm_crawl = Thread(target=Commander.mode_c, args=(args.c,))
        elif args.e is not None:
            comm_crawl = Thread(target=Commander.mode_e, args=(args.e,))
        comm_crawl.start()
        # 10個下載cell
        cell_group = [cell(i, Commander) for i in range(1, 11)]
        for c in cell_group:
            ct = Thread(target=c.run)
            ct.start()

        # 監測主程式
        allfinish = False
        comm_status_check = time()
        while not allfinish:
            try:
                # 完成檢測
                allstatus = list(map(lambda x: getattr(x, "status"), cell_group))
                if False not in map(lambda x: x.__eq__("Closed"), allstatus):
                    allfinish = True
                # 狀態顯示
                if time() - comm_status_check > 1:
                    Commander.get_status() # 每秒顯示一次狀態
                    comm_status_check = time()
            
            except KeyboardInterrupt:
                print("接收到停止訊號")
                print("剩餘", Commander.url_que.qsize())
                Commander.forcestop = True
                for c in cell_group:
                    c.forcestop = True
                if args.c is not None:
                    Commander.save()
                    print("存檔完成")
                ## driver在commander中關掉
                exit(0)
        colorprint("本次任務結束\n", FRG_YELLOW)
        if args.c is not None:
            Commander.save()
            print("存檔完成")

    else:
        print("參數有點問題，不知道該做什麼")
