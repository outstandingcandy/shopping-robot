import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('../../../selenium/py')
sys.path.append('../')
sys.path.append('../../')
sys.path.append('bbzdm')

import re
import json
import time
import requests
import traceback
from urlparse import urlparse,urlunparse,parse_qs
import sqlite3
import ConfigParser

from scrapy import log
from scrapy.http import Request, FormRequest, Headers
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy_webdriver.http import WebdriverRequest
from scrapy_webdriver.selector import WebdriverXPathSelector

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

import items


class SmzdmSpider(CrawlSpider):
    name = "smzdm"
    allowed_domains = ["smzdm.com"]
    __url_pattern_xpath_dict = {}
    __smzdm_log_file = "../../../log/smzdm.log"
    __shopping_log_file = "../../../log/shopping.log"
    urls_seen = set()

    def __init__(self, category=None, *args, **kwargs):
        super(SmzdmSpider, self).__init__(*args, **kwargs)
        # webpage_database_path = "../../../data/smzdm"
        # self.webpage_database_name = webpage_database_path.split("/")[-1]
        # self.conn = sqlite3.connect(webpage_database_path)
        # self.c = self.conn.cursor()
        # for row in self.c.execute('''SELECT url FROM %s''' % (self.webpage_database_name)):
        #     self.urls_seen.add(row[0])

        self.formdata = {'create':'0',\
                'email':"13058770524", \
                'password':"koala1128",\
                }

    def start_requests(self):
        # logger = logging.getLogger(self.__smzdm_log_file)
        log.start(logfile=self.__smzdm_log_file, loglevel='INFO', logstdout=False)
        smzdm_config = ConfigParser.RawConfigParser()
        smzdm_config.read("configure/smzdm.ini")
        self.price_pattern = re.compile(smzdm_config.get("item_page", "price_pattern").decode("utf-8"))
        self.usd_price_pattern = re.compile(smzdm_config.get("item_page", "usd_price_pattern").decode("utf-8"))
        self.jpy_price_pattern = re.compile(smzdm_config.get("item_page", "jpy_price_pattern").decode("utf-8"))
        self.eur_price_pattern = re.compile(smzdm_config.get("item_page", "eur_price_pattern").decode("utf-8"))
        self.head_separator = smzdm_config.get("item_page", "head_separator_pattern").decode("utf-8")
        self.attachment_pattern = re.compile(smzdm_config.get("item_page", "attachment_pattern").decode("utf-8"))

        config_file_name = "configure/shopping_page.ini"
        shopping_config = ConfigParser.RawConfigParser()
        shopping_config.read(config_file_name)

        for section_name in shopping_config.sections():
            log.msg("Supported url pattern:\t%s" % (shopping_config.get(section_name, "url_pattern").decode('utf8')) , level=log.DEBUG, spider=SmzdmSpider)
            url_pattern = re.compile(shopping_config.get(section_name, "url_pattern").decode('utf8'))
            title_xpath = shopping_config.get(section_name, "title_xpath")
            price_xpath = shopping_config.get(section_name, "price_xpath")
            price_redudant_pattern = re.compile(shopping_config.get(section_name, "price_redudant_pattern").decode('utf8'))
            description_xpath = shopping_config.get(section_name, "description_xpath")
            description_img_xpath = shopping_config.get(section_name, "description_img_xpath")
            currency = shopping_config.get(section_name, "currency")
            title_img_xpath_list = shopping_config.get(section_name, "title_img_xpath").split(",")
            comment_xpath = shopping_config.get(section_name, "comment_xpath")
            vote_count_xpath = shopping_config.get(section_name, "vote_count_xpath")
            vote_score_xpath = shopping_config.get(section_name, "vote_score_xpath")
            self.__url_pattern_xpath_dict[url_pattern] = (title_xpath, \
                    price_xpath, price_redudant_pattern, description_xpath, \
                    description_img_xpath, currency, title_img_xpath_list, \
                    comment_xpath, vote_count_xpath, vote_score_xpath)

        log.msg("Start requests", level=log.INFO, spider=SmzdmSpider)
        # CrawlSpider.start_requests(self)
        for (category, urls) in smzdm_config.items("category"):
            break
            if category == "all_post":
                for url in urls.split(","):
                    for page_num in range(1700, 1800):
                        list_url = "%s/p%d" % (url, page_num)
                        yield WebdriverRequest(list_url, meta={'category': category}, callback=self.parse_smzdm_post_list_page)
            else:
                for url in urls.split(","):
                    yield WebdriverRequest(url, meta={'category': category}, callback=self.parse_smzdm_list_page)

        # yield WebdriverRequest('http://post.smzdm.com/p/306042/', meta={'category': 'all_post'}, callback=self.parse_smzdm_post_page)
        log.msg("Login Amazon", level=log.INFO, spider=SmzdmSpider)
        yield WebdriverRequest('http://associates.amazon.cn/gp/associates/network/main.html', callback=self.submit_login_info)
        log.msg("Login Amazon success", level=log.INFO, spider=SmzdmSpider)
        yield WebdriverRequest('http://www.smzdm.com/p/6009011/', meta={'category': 'lego'}, callback=self.parse_smzdm_item_page)
        # yield WebdriverRequest('http://haitao.smzdm.com/p/318307', meta={'category': 'camera'}, callback=self.parse_smzdm_item_page)

    def login(self):
        return WebdriverRequest('http://associates.amazon.cn/gp/associates/network/main.html', callback=self.submit_login_info)

    def submit_login_info(self, response):
        sel = WebdriverXPathSelector(response)
        sel.select('//*[@id="ap_email"]')[0].send_keys(self.formdata["email"])
        sel.select('//*[@id="ap_password"]')[0].send_keys(self.formdata["password"])
        sel.select('//*[@id="signInSubmit"]')[0].click()
        time.sleep(1)
        self.check_login(response)

    def check_login(self, response):
        self.download_page(response, "after_login.html")

    def download_page(self, response, filename):
        with open(filename, 'w') as f:
            f.write("%s\n%s\n%s\n" % (response.url, response.headers, response.body))

    def parse_smzdm_list_page(self, response):
        try:
            category = response.meta["category"]
            sel = WebdriverXPathSelector(response)
            item_url_sel_list = sel.select("/html/body/section//div[@class='listTitle']/h3[@class='itemName']/a/@href")
            for item_url_sel in item_url_sel_list:
                item_url = item_url_sel.extract()
                # if item_url not in self.urls_seen:
                yield WebdriverRequest(item_url, meta={'category': category}, callback=self.parse_smzdm_item_page)
                # else:
                #     raise StopIteration
                break
            next_page_xpath = "//li[@class='pagedown']/a/@href"
            next_page_url_sel_list = sel.select(next_page_xpath)
            for next_page_url_sel in next_page_url_sel_list:
                next_page_url = next_page_url_sel.extract()
                break
                yield WebdriverRequest(next_page_url, meta={'category': category}, callback=self.parse_smzdm_list_page)
        except:
            traceback.print_exc()
            log.msg("Smzdm list page parse failed:\t[%s]" % (response.url) , level=log.ERROR, spider=SmzdmSpider)
            raise StopIteration

    def parse_smzdm_item_page(self, response):
        try:
            category = response.meta["category"]
            sel = WebdriverXPathSelector(response)
            title_sel_list = sel.select('/html/body/section/div[1]/article//h1')
            attachment_sel_list = sel.select('/html/body/section/div[1]/article//h1/span')
            if len(title_sel_list):
                title = self.normalize_text(title_sel_list[0].extract())
                item_name = title
            else:
                log.msg("Smzdm title parse failed:\t[%s]" % (response.url) , level=log.ERROR, spider=SmzdmSpider)
                raise StopIteration
            all_attachment = ''
            for attachment_sel in attachment_sel_list:
                attachment = attachment_sel.extract()
                item_name = item_name.replace(attachment, '')
                all_attachment += attachment
            price, currency = self.parse_price(all_attachment)
            # item_shopping_url_sel_list = sel.select("/html/body/section/div[1]/article/div[2]/div/div/a/@href")
            item_shopping_url_sel_list = sel.select("/html/body/section/div[1]/article/div[1]/div[2]/div[2]/div/a/@href")
            if len(item_shopping_url_sel_list):
                item_shopping_url = item_shopping_url_sel_list[0].extract()
                if item_shopping_url not in self.urls_seen:
                    yield WebdriverRequest(item_shopping_url, meta={'referer': response.url}, callback=self.parse_shopping_item_page)
            else:
                log.msg("Smzdm shopping url parse failed:\t[%s]" % (response.url) , level=log.ERROR, spider=SmzdmSpider)
                raise StopIteration
            description_sel_list = sel.select('/html/body/section/div[1]/article/div[2]/p[@itemprop="description"]')
            description = ''
            img_src_list = []
            for description_sel in description_sel_list:
                description += self.normalize_text(description_sel.extract())
                img_src_sel_list = description_sel.select(".//img/@src")
                for img_src_sel in img_src_sel_list:
                    img_src = img_src_sel.extract()
                    if img_src:
                        img_src_list.append(img_src)
            try:
                worthy_vote = int(self.get_text_by_xpath(sel, "//span[@id='rating_worthy_num']/text()"))
            except:
                traceback.print_exc()
                worthy_vote = 0
            try:
                unworthy_vote = int(self.get_text_by_xpath(sel, "//span[@id='rating_unworthy_num']/text()"))
            except:
                traceback.print_exc()
                unworthy_vote = 0
            try:
                favorite_count = int(self.get_text_by_xpath(sel, "//a[@class='fav']/em/text()"))
            except:
                traceback.print_exc()
                favorite_count = 0
            try:
                comment_count = int(self.get_text_by_xpath(sel, "//a[@class='comment']/em/text()"))
            except:
                traceback.print_exc()
                comment_count = 0
            yield items.SmzdmItem(title=item_name, price=price, url=response.url, description=description, \
                                  image_urls=img_src_list, worthy_vote=worthy_vote, unworthy_vote=unworthy_vote, \
                                  favorite_count=favorite_count, comment_count=comment_count, category=category, currency=currency)
        except:
            traceback.print_exc()
            log.msg("Smzdm item page parse failed:\t[%s]" % (response.url) , level=log.ERROR, spider=SmzdmSpider)
            raise StopIteration

    def parse_shopping_item_page(self, response):
        try:
            sel = WebdriverXPathSelector(response)
            referer = response.meta["referer"]
            jd_jump_url_sel = sel.select("/html/body/div[5]/div/div/div[1]/div[2]/div[3]/a/@href")
            if jd_jump_url_sel:
                log.msg("JD jump url:\t[%s]" % (jd_jump_url_sel[0].extract()) , level=log.DEBUG, spider=SmzdmSpider)
                yield WebdriverRequest(jd_jump_url_sel[0].extract(), meta={'referer': referer}, callback=self.parse_shopping_item_page)
            else:
                img_src_list = []
                comment_list = []
                description = ""
                title = ""
                vote_count = ""
                vote_score = ""
                price = -1.0
                log.msg("Shopping url: %s" % (response.url), level=log.DEBUG, spider=SmzdmSpider)
                log.msg("Real shopping url: %s" % (response.webdriver.current_url), level=log.DEBUG, spider=SmzdmSpider)
                url = response.webdriver.current_url
                hostname = urlparse(url).hostname
                for url_pattern, (title_xpath, price_xpath, price_redudant_pattern, description_xpath, description_img_xpath, currency, title_img_xpath_list, comment_xpath, vote_count_xpath, vote_score_xpath) in self.__url_pattern_xpath_dict.items():
                    if url_pattern.match(url):
                        log.msg("Shopping url pattern is found", level=log.DEBUG, spider=SmzdmSpider)
                        title_sel_list = sel.select(title_xpath)
                        if len(title_sel_list):
                            title = self.normalize_text(title_sel_list[0].extract())
                        else:
                            log.msg("Shopping page error:\ttitle is not found", level=log.ERROR, spider=SmzdmSpider)
                            raise StopIteration
                            continue
                        price_sel_list = sel.select(price_xpath)
                        if len(price_sel_list):
                            price_text = price_sel_list[0].extract()
                            price_text = price_redudant_pattern.sub('', price_text)
                            try:
                                price = float(price_text)
                                if url.startswith("http://www.kiddies24.de"):
                                    price /= 100
                            except:
                                traceback.print_exc()
                                log.msg("Shopping page error:\tThis item is sold out, the price is %s" % (price), level=log.WARNING, spider=SmzdmSpider)
                        else:
                            log.msg("Shopping page error:\tprice is not found", level=log.WARNING, spider=SmzdmSpider)
                        title_img_sel_list = []
                        for title_img_xpath in title_img_xpath_list:
                            title_img_sel_list += sel.select(title_img_xpath)
                        title_img_src = ""
                        for title_img_sel in title_img_sel_list:
                            title_img_src = title_img_sel.extract()
                            if title_img_src:
                                img_src_list.append(title_img_src)
                                break
                        if hostname == "item.jd.com":
                            # sel.select_script("arguments[0].scrollIntoView(true);", sel.webdriver.find_element_by_xpath("//div[@id='comment-0']"))
                            # sel.select_script("arguments[0].scrollIntoView(true);", sel.webdriver.find_element_by_xpath("//div[@id='comment-2']"))
                            # sel.webdriver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            sel.webdriver.find_element_by_xpath("//li[@id='detail-tab-comm']/a").click()
                            time.sleep(2)
                        for comment_sel in sel.select(comment_xpath):
                            comment_list.append(comment_sel.extract())
                        vote_count_sel_list = sel.select(vote_count_xpath)
                        if len(vote_count_sel_list):
                            vote_count = vote_count_sel_list[0].extract()
                        else:
                            log.msg("Shopping page error:\tvote count is not found", level=log.ERROR, spider=SmzdmSpider)
                        vote_score_sel_list = sel.select(vote_score_xpath)
                        if len(vote_score_sel_list):
                            vote_score = vote_score_sel_list[0].extract()
                        else:
                            log.msg("Shopping page error:\tvote score is not found", level=log.ERROR, spider=SmzdmSpider)
                        log.msg("Shopping item: [%s] [%s] [%s] [%s] [%s]" % (title, description, price, url, referer) , level=log.DEBUG, spider=SmzdmSpider)
                        yield items.ShoppingItem(title=title, price=price, url=url, referer=referer, image_urls=img_src_list, \
                                title_image_url=title_img_src, description=description, currency=currency, \
                                comment_list=comment_list, vote_count=vote_count, vote_score=vote_score)
        except:
            traceback.print_exc()
            log.msg("Shopping item page parse failed:\t[%s]" % (response.url) , level=log.ERROR, spider=SmzdmSpider)
            raise StopIteration

    def parse_price(self, attachment):
        price = 0.0
        tokens = attachment.split(' ')
        for token in tokens:
            price_match = self.price_pattern.match(token)
            if price_match:
                price = float(price_match.group(1))
                return price, "CNY"
            price_match = self.usd_price_pattern.match(token)
            if price_match:
                price = float(price_match.group(1))
                return price, "USD"
            price_match = self.jpy_price_pattern.match(token)
            if price_match:
                price = float(price_match.group(1))
                return price, "JPY"
            price_match = self.eur_price_pattern.match(token)
            if price_match:
                price = float(price_match.group(1))
                return price, "EUR"
        return price, "CNY"

    def normalize_text(self, text):
        return text.strip().replace("\n", "").replace("\"", "")

    def get_element_by_xpath(self, sel, xpath):
        sel_list = sel.select(xpath)
        if len(sel_list):
            return sel_list[0]
        else:
            log.msg("Get element by xpath %s failed" % (xpath) , level=log.ERROR, spider=SmzdmSpider)

    def get_text_by_xpath(self, sel, xpath):
        sel_list = sel.select(xpath)
        if len(sel_list):
            return sel_list[0].extract().strip()
        else:
            log.msg("Get element by xpath %s failed" % (xpath) , level=log.ERROR, spider=SmzdmSpider)
            return ""
