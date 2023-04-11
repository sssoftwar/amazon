import asyncio,re,time
from playwright.async_api import async_playwright
from amazoncaptcha import AmazonCaptcha
alive_page = []

# 凡是goto和点击了按钮的后面都要处理亚马逊图片验证码
# 如果无法正常跳转，获取验证页面中的图片网址
async def validate(page):
    img_link = await page.get_attribute('div.a-row:nth-child(2) > img:nth-child(1)', 'src')
    print(img_link)
    captcha = AmazonCaptcha.fromlink(img_link)
    solution = captcha.solve()
    await page.locator('#captchacharacters').fill(solution)
    await page.keyboard.press('Enter')
    return solution
# async def run(playwright):
async def get_merchant_addr_by_asin(playwright, asin):
    proxy={
        "server": "http://127.0.0.1:7890"
    }
    # browser = await playwright.firefox.launch(headless=False, proxy=proxy)
    browser = await playwright.chromium.launch(headless=False, proxy=proxy)
    page = await browser.new_page()
    alive_page.append(page)
    # page.route('**/*.{png,jpeg}',lambda route: route.abort())
    # await page.route(re.compile(r"(\.png)|(\.jpeg)"), cancel_request)
    # 设置收货地址，因为有些商品无法显示某些地区的卖家
    await page.goto('https://www.amazon.com/')
    res_html = await page.content()
    # print(res_html)
    if 'Enter the characters you see below' in res_html:
        print('需要验证')
        validate(page)
        print('验证完成')
        await page.reload()
    # 等待页面加载完成
    await page.wait_for_load_state('domcontentloaded')
    if await page.locator('#glow-ingress-block').count() > 0:
        print('点击地区按钮')
        await page.locator('#glow-ingress-block').click()
    else:
        print('没有地区按钮，需要刷新')
        await page.reload()
    location = await page.locator('#glow-ingress-line2').inner_text()
    while not 'United Kingdom' in location and not '英国' in location:
    # while not 'United Kingdom' in await page.locator('#glow-ingress-line2').inner_text() and not '英国' in await page.locator('#glow-ingress-line2').inner_text():
        choose_country_btn_count = await page.locator('#GLUXCountryValue').count()
        if choose_country_btn_count == 0:
            location = await page.locator('#glow-ingress-line2').inner_text()
            print('选择地区的按钮是0，刷新页面')
            print('当前地址:%s'%location)
            # print(await page.locator('#glow-ingress-line2').count())
            # await page.locator('#glow-ingress-line2').click()
            # await page.reload()
            await page.wait_for_timeout(1 * 1000)
            # continue
        await page.locator('#GLUXCountryValue').click()
        await page.locator('#GLUXCountryList_6').click()
        print('选择了United Kingdom')
        if 'United Kingdom' in await page.locator('#GLUXCountryValue').inner_text() or '英国' in await page.locator('#GLUXCountryValue').inner_text():
            await page.locator('#a-popover-1 > div > div.a-popover-footer > span').click()
            break
    # 初始化卖家数据结构
    merchant_info = {'asin':asin}
    print('当前已打开的标签数量:%d' % len(alive_page))
    if len(alive_page) > 1:
        print('标签数量竟然大于1了：%s' % alive_page)
        # close_tag()
    if len(alive_page) == 0:
        print('先打开浏览器...')
        # async with async_playwright() as playwright:
        #     await run(playwright)
        # time.sleep(1000)
    # page = await alive_page[0]
    # print(page)
    # 设置禁止图片加载
    # page.route(re.compile(r"(\.png)|(\.jpeg)"), cancel_request)
    # page.route(re.compile(r"(\.png)|(\.jpg)|(\.jpeg)"), route.aobrt())
    try:
        await page.goto(f"https://www.amazon.com/dp/{asin}")
        # print(response)
        html_text = await page.locator('html').nth(0).inner_text()
        if 'Enter the characters you see below' in html_text:
            print('需要验证')
            validate(page)
            print('验证完成')
        # page.goto(f"https://www.amazon.com/led-tactical-flashlight-rechargable/dp/{asin}/")
        # 根据官网，试试这样
        # await page.wait_for_load_state('domcontentloaded')
        # 有时候需要先点一下这个东西才能展开卖家链接
        if await page.locator('#newAccordionRow_1').count()> 0:
            print('需要点击展开卖家')
            await page.locator('#newAccordionRow_1').nth(0).click()
        seller_btn_count = await page.locator('#sellerProfileTriggerId').count()
        print('是否有卖家按钮:%d' % seller_btn_count)
        if seller_btn_count == 0:
            print('没有地址')
            title = await page.title().lower()
            if 'error' in title:
                print('需要提交验证码，暂时先终止程序')
                merchant_info['name'] = -1
                merchant_info['address'] = -1
                return merchant_info
            merchant_info['name'] = 'None'
            merchant_info['address'] = 'None'
            return merchant_info
        # 保存好页面1，当出故障时方便找原因
        # print(page.content().text())
        # if await page.locator('#sellerProfileTriggerId').nth(0).is_enabled():
        # 进入卖家页面
        await page.locator('#sellerProfileTriggerId').nth(0).click()
        print('点击了卖家链接')
        # 保存好页面2，当出故障时方便找原因
        res_html = await page.content()
        if 'Enter the characters you see below' in res_html:
            print('需要验证')
            validate(page)
            print('验证完成')
        # 可能会出现Sorry页面，刷新就行了
        while 'orry' in await page.title():
            print('出错了')
            res_html = await page.content()
            with open('Sorry.html', 'w', encoding='utf-8') as p:
                p.write(res_html)
            # 保存好页面3，当出故障时方便找原因
            await page.reload()
            time.sleep(10)
            print('睡眠结束')
        await page.wait_for_timeout(500)
        print(await page.locator('#page-section-detail-seller-info').count())
        while await page.locator('#page-section-detail-seller-info').count() ==0 :
            print('没有：#page-section-detail-seller-info，需要刷新页面')
            res_html = await page.content()
            with open('page-section-detail-seller-info.html', 'w', encoding='utf-8') as p:
                p.write(res_html)
            # 保存好页面4，当出故障时方便找原因
            # await page.reload()
            # await page.wait_for_timeout(10 * 1000)
            # print('睡眠结束')
        seller_row_text = await page.locator('#page-section-detail-seller-info').nth(0).inner_text()
        # print(seller_row_text)
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
        # close_tag()
        # await page.wait_for_timeout(5000)
        print(merchant_info)
        return merchant_info
    except Exception as e:
        print('错误信息：')
        print(e)
        print('将错误页面保存再退出')


def close_tag():
    print('关闭除首页外的所有标签页')
    global alive_page
    while len(alive_page) > 1:
        print('还有%d个标签页，关闭一个' % len(alive_page))
        alive_page[-1].close()
        alive_page.pop(-1)
    print('现在只剩首页了')

async def main(asin):
    async with async_playwright() as playwright:
        # await run(playwright)
        await get_merchant_addr_by_asin(playwright, asin)
    print('%s协程工作完毕'%asin)
async def all():
    start_time = time.time()
    task_list = []
    # for i in ['B0B6SS47TW']:
    for i in ['B0B6SS47TW', 'B06ZXWZNMG', 'B07YSP6YS5']:
        print('启动了')
        task_list.append(asyncio.create_task(main(i)))
    await asyncio.gather(*task_list)
    end_time = time.time()
    now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))
    used_sec = int(end_time - start_time)
    print('用时%d秒，当前时间%s' %(used_sec, now))
# asyncio.run(main())
asyncio.run(all())
if __name__ == '__main__':
    # asin = 'B0B6SS47TW'  # 有地址
    # print(asin)
    pass