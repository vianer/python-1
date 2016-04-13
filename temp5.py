#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Created on:2016/2/23 18:35
# Project:suning_base
# Author:yangmingsong

from pyspider.libs.base_handler import *
from ms_spider_fw.DBSerivce import DBService
import time
import json
import re

# config_text
# when start a spider,you should modify the next config text first

db_name = 'platform_data'  # database name for store data , string
table_name = 'suning_base'  # table name for store data , string
table_title = 'url,detail,crawl_time'  # table title for store data , should be string separated by ','
url_start = 'http://www.suning.com/emall/pgv_10052_10051_1_.html'  # start url for crawl,string
# connect string , usually no need to modify
connect_dict = {'host': '10.118.187.12', 'user': 'admin', 'passwd': 'admin', 'charset': 'utf8'}

# now,the next is spider script
db_server = DBService(dbName=db_name, tableName=table_name, **connect_dict)
# if create table for store result in mysql , no need to be changed
if not db_server.isTableExist():
    db_server.createTable(tableTitle=table_title.split(','))

pat_pagenumbers = re.compile('param.pageNumbers = "(\d+?)";')


class Handler(BaseHandler):
    crawl_config = {
        'proxy': '10.10.10.10:80',
        'headers': {
            'User-Agent': 'User-Agent:Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1'
        }
    }

    @every(minutes=24 * 60)
    def on_start(self):
        self.crawl(url_start, callback=self.step_first, proxy=False, retries=10)

    @config(age=2 * 24 * 60 * 60)
    def step_first(self, response):
        d = response.doc
        for t in d('.listLeft dd a').items():
            id_t = t.attr('id')
            cate = {'category_name': t.text(), 'category_id': id_t}
            url = 'http://list.suning.com/emall/showProductList.do?ci=' + id_t + \
                  '&pg=03&cp=0&il=0&iy=0&n=1&cityId=9051'
            self.crawl(url, callback=self.step_second, save=cate, retries=100)

    @config(age=15 * 24 * 60 * 60)
    def step_second(self, response):
        d = response.doc
        # page_sum = int(d('#pageLast').text())
        # rebuild on 2016-04-13
        try:
            page_sum = int(re.findall(pat_pagenumbers, response.text)[0])
        except Exception:
            page_sum = 1
        print page_sum
        id_t = response.save['category_id']
        url_s = 'http://list.suning.com/emall/showProductList.do?ci='
        url_m = '&pg=03&cp='
        url_e = '&il=0&iy=0&n=1&cityId=9051'
        urls = map(lambda x: url_s + id_t + url_m + str(x) + url_e, range(page_sum))
        for url in urls:
            self.crawl(url, callback=self.my_result, save=response.save, retries=100)

    @config(priority=2)
    def my_result(self, response):
        d = response.doc
        temp = list(d('.wrap').items())
        cate = {'category': response.save}
        detail = {}
        for t in temp:
            dict_t = {
                # rebuild on 2016-04-13
                'title': t('.sellPoint').attr('title'),
                'href': t('.sellPoint').attr('href'),
                'img_src': t('.search-loading').attr('src2'),
                'sku': t('.prive.price').attr('datasku'),
                'comment_sum': t('.com-cnt a').text(),
                'val': t('.b-small').attr('val'),
                'seller_count': re.findall(r'\d+', t('.seller>a').text())[0]
                if t('.seller>a').text() else '',
                'sellers_page_url': t('.seller>a').attr('href')
            }
            detail[temp.index(t)] = dict_t
        detail_ok = dict(detail.items() + cate.items())
        crawl_time = time.strftime('%Y-%m-%d %X', time.localtime())
        return [
            response.url,
            json.dumps(detail_ok),
            crawl_time
        ]

    # over ride method for result store to mysql
    def on_result(self, result):
        if result:
            db_server.data2DB(data=result)
        else:
            print u'result-->return None'
