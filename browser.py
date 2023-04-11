from getpass import getuser
import time,re
import asyncio
import pyperclip
from playwright.sync_api import sync_playwright
from amazoncaptcha import AmazonCaptcha
# from playwright.async_api import async_playwright

# 当前激活页面
alive_page = []
# 验证码
code = ''

# 凡是goto和点击了按钮的后面都要处理亚马逊图片验证码
# 如果无法正常跳转，获取验证页面中的图片网址
def validate(page):
    img_link = page.get_attribute('div.a-row:nth-child(2) > img:nth-child(1)', 'src')
    print(img_link)
    captcha = AmazonCaptcha.fromlink(img_link)
    solution = captcha.solve()
    page.locator('#captchacharacters').fill(solution)
    page.keyboard.press('Enter')
    return solution


# 初始化浏览器
def init():
    global alive_page
    global code
    if len(alive_page) != 0:
        print('不必重复打开浏览器')
        return 0
    print('打开浏览器')
    playwright = sync_playwright().start()
    # playwright = async_playwright().start()
    __USER_DATA_DIR_PATH__ = f"C:\\Users\\{getuser()}\\AppData\Local\Google\Chrome\\User Data"
    # chrome.exe 的地址
    __EXECUTABLE_PATH__ = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    chrome_param = [
        '--disable-popup-blocking',
        '--disable-blink-features=AutomationControlled',
        '--disable-bundled-ppapi-flash',
        '--ignore-ssl-errors',
        '--ignore-certificate-errors',
        '--disable-gpu',
        '--disable-webrtc-encryption',
        '--disable_non_proxied_udp',
        'lang=en-us'
    ]
    '''
    browser = playwright.chromium.launch_persistent_context(
        # 指定本机用户缓存地址
        user_data_dir=__USER_DATA_DIR_PATH__,
        # 指定本机google客户端exe的路径
        executable_path=__EXECUTABLE_PATH__,
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
        ignore_default_args=['--enable-automation'],
        # 这个可以直接看函数内的列表参数说明
        chromium_sandbox=False,  # 禁用chrome的方式
        ignore_https_errors=True,
        # accept_downloads=True,
        # 设置不是无头模式
        headless=False,
        bypass_csp=True,
        slow_mo=10,
        # 跳过检测
        args=['--disable-blink-features=AutomationControlled']
    )
    '''
    proxy={
        "server": "http://127.0.0.1:7890"
    }
    # browser = playwright.webkit.launch(headless=False, proxy=proxy)
    browser = playwright.firefox.launch(headless=False, proxy=proxy)
    # browser = playwright.chromium.launch(headless=False, proxy=proxy)
    # browser = playwright.chromium.launch(headless=True, proxy=proxy)
    page = browser.new_page()
    page.route('**/*.{png,jpeg}',lambda route: route.abort())
    # page.route(re.compile(r"(\.png)|(\.jpeg)"), cancel_request)
    # 设置收货地址，因为有些商品无法显示某些地区的卖家
    page.goto('https://www.amazon.com/')
    # print(page.content())
    alive_page.append(page)
    if 'Enter the characters you see below' in page.locator('body').nth(0).inner_text():
        print('需要验证')
        code = validate(page)
        print('验证完成')
        # refresh()
        page.keyboard.press('F5')
    # print(page.locator('#glow-ingress-block').count())
    # with page.expect_event("popup") as page_info:
    #     print('点击它')
    # page.wait_for_load_state('domcontentloaded')
    page.wait_for_timeout(10 * 1000)
    if page.locator('#nav-global-location-data-modal-action').is_enabled():
        print('点击地区按钮')
        page.locator('#nav-global-location-data-modal-action').click()
    elif page.locator('#glow-ingress-block').is_enabled():
        print('点击地区按钮')
        page.locator('#glow-ingress-block').click()
    else:
        page.reload()
    # page.wait_for_load_state('domcontentloaded')
    while not 'United Kingdom' in page.locator('#glow-ingress-line2').inner_text() and not '英国' in page.locator('#glow-ingress-line2').inner_text():
        # page.locator('#glow-ingress-block').click()
        # print('点击了配送地区')
        print('选择地区按钮:%d'% (page.locator('#GLUXCountryValue').count()))
        # print(page.locator('#GLUXCountryValue').inner_text())
        if page.locator('#GLUXCountryValue').count() == 0:
            print('WTF，怎么会是0？')
            time.sleep(3)
            continue
        page.locator('#GLUXCountryValue').click()
        page.locator('#GLUXCountryList_6').click()
        print('选择了United Kingdom')
        if 'United Kingdom' in page.locator('#GLUXCountryValue').inner_text() or '英国' in page.locator('#GLUXCountryValue').inner_text():
            page.locator('#a-popover-1 > div > div.a-popover-footer > span').click()
            break

def cancel_request(route, request):
    route.abort()
def get_merchant_addr_by_asin(asin):
    global alive_page
    global code
    # 初始化卖家数据结构
    merchant_info = {'asin':asin}
    print('当前已打开的标签数量:%d' % len(alive_page))
    while len(alive_page) > 1:
        close_tag()
    if len(alive_page) == 0:
        print('先打开浏览器...')
        init()
    page = alive_page[0]
    # 设置禁止图片加载
    # page.route(re.compile(r"(\.png)|(\.jpeg)"), cancel_request)
    page.route(re.compile(r"(\.png)|(\.jpg)|(\.jpeg)"), cancel_request)
    try:
        print('前往%s商品页面'%asin)
        response = page.goto(f"https://www.amazon.com/dp/{asin}")
        if 'Enter the characters you see below' in page.locator('body').nth(0).inner_text():
            print('需要验证')
            code = validate(page)
            print('验证完成')
        # page.goto(f"https://www.amazon.com/led-tactical-flashlight-rechargable/dp/{asin}/")
        print('已打开%s商品页面'%asin)
        # 根据官网，试试这样
        # page.wait_for_load_state('domcontentloaded')
        print('是否有卖家按钮:%d' % page.locator('#sellerProfileTriggerId').count())
        if page.locator('#sellerProfileTriggerId').count() == 0:
            print('没有地址')
            if 'error' in page.title().lower():
                print('需要提交验证码，暂时先终止程序')
                merchant_info['name'] = -1
                merchant_info['address'] = -1
                return merchant_info
            merchant_info['name'] = 'None'
            merchant_info['address'] = 'None'
            return merchant_info
        # 有时候需要先点一下这个东西才能展开卖家链接
        if page.locator('#newAccordionRow_1').count() > 0:
            print('需要点击展开卖家')
            page.locator('#newAccordionRow_1').nth(0).click()
        # 保存好页面1，当出故障时方便找原因
        with open('product.html', 'w', encoding='utf-8') as p:
            p.write(response.text())
        # print(page.content().text())
        if page.locator('#sellerProfileTriggerId').nth(0).is_enabled():
            # 进入卖家页面
            page.locator('#sellerProfileTriggerId').nth(0).click()
        # 保存好页面2，当出故障时方便找原因
        with open('seller1.html', 'w', encoding='utf-8') as p:
            p.write(response.text())
        if 'Enter the characters you see below' in page.locator('body').nth(0).inner_text():
            print('需要验证')
            code = validate(page)
            print('验证完成')
        # 可能会出现Sorry页面，刷新就行了
        while 'orry' in page.title():
            print('出错了')
            # 保存好页面3，当出故障时方便找原因
            with open('seller2.html', 'w', encoding='utf-8') as p:
                p.write(page.content())
            page.keyboard.press('F5')
        if page.locator('#page-section-detail-seller-info').count() ==0 :
            print('怎么回事')
            # 保存好页面4，当出故障时方便找原因
            with open('seller3.html', 'w', encoding='utf-8') as p:
                p.write(page.content())
            # refresh()
            page.keyboard.press('F5')
        seller_row_text = page.locator('#page-section-detail-seller-info').nth(0).inner_text()
        # 公司名称
        name = ''
        # 公司地址
        address = ''
        if '地址' in seller_row_text:
            name = re.search(re.compile('名称:.(.+)\n公司'), seller_row_text).group(1)
            address = re.split(r'地址:\W+',seller_row_text)[-1]
        elif 'Business Address' in seller_row_text:
            name = re.search(re.compile('Name:.(.+)\nBusiness'), seller_row_text).group(1)
            address = re.split(r'Address:\W+',seller_row_text)[-1]
        merchant_info['name'] = name
        merchant_info['address'] = address
        close_tag()
        return merchant_info
    except Exception as e:
        print('错误信息：')
        print(e)
        print('将错误页面保存再退出')
        with open('error.html', 'w', encoding='utf-8') as p:
            p.write(page.content())


def close_tag():
    print('关闭除首页外的所有标签页')
    global alive_page
    while len(alive_page) > 1:
        print('还有%d个标签页，关闭一个' % len(alive_page))
        alive_page[-1].close()
        alive_page.pop(-1)
    print('现在只剩首页了')


def refresh():
    print('刷新页面')
    global alive_page
    alive_page[-1].reload()
    print('重新获取信息')


'''下载'''
'''
# 打开下载器
with page.expect_download() as download_info:
    # 找到你要下载的东西，找到点击的元素，点击
    downloadx = '//*[@id="_view_1545184311000"]/div[2]/div[4]/a[3]'
    page.click(downloadx)
    # 下载的东西
    download = download_info.value
    # 下载的路径
    print(download.path())
    # 下载的文件名
    print(download.suggested_filename)
'''

if __name__ == '__main__':
    asin = 'B0B6SS47TW'  # 有地址
    # asin = 'B08H1NTK82'  # 有地址
    # asin = 'B077BLB1DN'  # 没地址  
    info = get_merchant_addr_by_asin(asin)
    print(info)
    '''
    while True:
        time.sleep(10)

    '''
    # 加入协程
