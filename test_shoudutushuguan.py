import requests
import random
import json
from lxml import etree
import re
import time
import pymysql
import hashlib
import socket



#登陆后的cookies   以后想用 selenium+redis方式设置和获取cookie
COOKIES = [
    "自己的cookies"
]
#user_agent
USER_AGENT = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.133 Safari/534.16",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0",
    "Mozilla/5.0 (X11; U; Linux x86_64; zh-CN; rv:1.9.2.10) Gecko/20100922 Ubuntu/10.10 (maverick) Firefox/3.6.10",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36 ",
    "OPR/26.0.1656.60",
    "Opera/8.0 (Windows NT 5.1; U; en)",
    "Mozilla/5.0 (Windows NT 5.1; U; en; rv:1.8.1) Gecko/20061208 Firefox/2.0.0 Opera 9.50",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera 9.50",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/534.57.2 (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E; QQBrowser/7.0.3698.400)",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)",
    "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.84 Safari/535.11 SE 2.X MetaSr 1.0",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; SV1; QQDownload 732; .NET4.0C; .NET4.0E; SE 2.X MetaSr 1.0)",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.122 ",
    "UBrowser/4.0.3214.0 Safari/537.36",
]

MYSQL_SETTING = {
    "user": "root",
    "host": "localhost",
    "password": "123456",
    "db": "newspaper_info",
    "charset": "utf8",
    "port": 3306
}

#设置已经完成的集合
completed = set()

def set_headers():
    """设置headlers"""
    HEADERS = {
        'Cookie': random.choice(COOKIES),
        "Host": "mp.weixin.qq.com",
        "User-Agent": random.choice(USER_AGENT)
    }
    return HEADERS


def create_tables():
    "创建表 json_info"
    sql = "create table json_info(id varchar(255) primary key, info text)"
    cursor.execute(sql)
    print("CREATE TABLE OK")

def get_ip():
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    return ip

def request_url(data):
    ip = get_ip()
    print(ip)
    res = requests.get("https://mp.weixin.qq.com/cgi-bin/appmsg", params=data, headers=set_headers())
    return res


def get_detail_url(res):
    """返回详情页的response"""
    print(res.text)
    try:
        new_urls = res.json()["app_msg_list"]
        for new_url in new_urls:
            yield requests.get(new_url["link"])
    except Exception as e:
        print("错误：", e)
        with open("url.txt", "a+", encoding="utf-8") as f:
            f.write(res.url)


def get_parse_detail(res):
    """解析页面"""
    url = res.url
    print(f"获得{url}页面")
    html = etree.HTML(res.text)
    article = '\n'.join(html.xpath('//div[@class="rich_media_content "]//p//span//text()'))
    #利用生成指纹+缓存去重
    m = hashlib.md5(article.encode("utf-8"))
    fingerprint = m.hexdigest()
    if fingerprint in completed:
        return

    title = html.xpath('//h2[@class="rich_media_title"]/text()')[0]
    author = re.findall('var title ="(.*?)";', res.text)[0]
    # 图片规则有点...
    images = re.findall(r'<img.*?data-ratio=".*?".*?data-src="(.*?)"', res.text)
    invalid_imgs = [
        "https://mmbiz.qpic.cn/mmbiz_gif/zMAZCXOibsjd86Mjo7SWBfNaf5uetibZDYXAdCu4rqrONDzrDzrImGglRxMBicHvM3U42MgoY019GQ1csbia3auM4Q/640?wx_fmt=gif",
    ]
    images = [img.rstrip() for img in images if img not in invalid_imgs]
    update_time = re.findall(r'var t="\d+",n="\d+",s="(.*?)";', res.text)[0]
    data = {
        "url": url,
        "title": title,
        "article": article,
        "images": images,
        "update_time": update_time,
        "author": author,
        "id": fingerprint
    }
    data = json.dumps(data)
    print(data)
    completed.add(fingerprint)
    return data


def do_storage(data):
    """存储"""
    old_data = json.loads(data)
    try:
        select_id = 'SELECT id FROM json_info'
        cursor.execute(select_id)
        info_id = cursor.fetchall()
        ids = [a[0] for a in info_id]
        if old_data["id"] in ids:
            print("已存在：{}".format(old_data["id"]))
            return
        insert_sql = 'INSERT INTO json_info(id,info) VALUE ("{}","{}")'.format(old_data["id"],data.replace('"', "'"))
        cursor.execute(insert_sql)
        connect.commit()
        print("提交成功")
    except Exception as e:
        connect.rollback()
        print('事务处理失败', e)


def main():
    for page in range(23, 275):
        data = {
            "token": "自己的token",
            "f": "json",
            "random": random.random(),
            "action": "list_ex",
            "begin": page*5,
            "count": "5",
            "fakeid": "MjM5MDA1MTA1MQ==",#公众号识别ID
            "type": 9,
            "lang": "zh_CN",
            "ajax": 1
        }
        res = request_url(data=data)
        #进入子页面
        for detail_res in get_detail_url(res):
            data = get_parse_detail(detail_res)
            if not data:
                continue
            do_storage(data)
        print("休息10秒")
        time.sleep(10)


if __name__ == "__main__":
    connect = pymysql.Connect(host=MYSQL_SETTING["host"],
                         user=MYSQL_SETTING["user"],
                         passwd=MYSQL_SETTING["password"],
                         db=MYSQL_SETTING["db"],
                         port=MYSQL_SETTING["port"],
                         charset=MYSQL_SETTING["charset"])
    cursor = connect.cursor()
    # create_tables()
    main()
    connect.close()