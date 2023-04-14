import asyncio,re,time,os
from playwright.async_api import async_playwright
from amazoncaptcha import AmazonCaptcha
import main_async
alive_page = []
batch_size = 1
'''
    1.经验就是await page.wait_for_load_state('domcontentloaded')和await page.wait_for_timeout()搭配能
    确保标签如果有的话一定会被捕捉到（timeout时间会影响最终质量，但是这样做能节省整体时间）
'''

# 判断是否有卖家按钮
async def has_seller_info(page, asin):
    # 特殊情况1：需要点击这个按钮才展开卖家链接
    if await page.locator('#newAccordionRow_1').count()> 0:
        print('%s特殊情况1：需要点击展开卖家'%asin)
        await page.locator('#newAccordionRow_1').nth(0).click()
    # 特殊情况2：需要要转到指定店铺才有卖家按钮
    elif await page.locator('#cross-border-widget-redirection-button').count() > 0:
        print('%s特殊情况2：要跳转到其他商店'%asin)
        href = await page.locator('#cross-border-widget-redirection-button').nth(0).get_attribute('href')
        # print(href)
        href = re.split(re.compile('\\/ref'), href)[0]
        await page.goto(href)
        # await page.wait_for_timeout(3 * 1000)
        await page.wait_for_load_state('domcontentloaded')
        if await page.locator('#sp-cc-accept').count() > 0:
            await page.locator('#sp-cc-accept').nth(0).click()
    # 跳转页面之后要等待页面加载
    await page.wait_for_load_state('domcontentloaded')
    await page.wait_for_timeout(1 * 1000)
    if await page.locator('#sellerProfileTriggerId').count() > 0:
        # 进入卖家页面
        await page.locator('#sellerProfileTriggerId').nth(0).click()
        print('点击了卖家按钮，正在进入卖家详情页')
        # 返回1说明有卖家按钮，且已点击进入
        return 1
    # 特殊情况3：需要点击更多商品选项才能展开卖家链接
    # 此特殊情况下，处理完成后会直接到达卖家详情页面
    elif await page.locator('#buybox-see-all-buying-choices').count() > 0:
        print('%s特殊情况3：需要点击展开购物选项'%asin)
        await page.locator('#buybox-see-all-buying-choices').nth(0).click()
        await page.wait_for_timeout(1000)
        seller_detail_href_raw = await page.locator('#aod-offer-soldBy > div > div > div.a-fixed-left-grid-col.a-col-right > a').nth(0).get_attribute('href')
        # print(seller_detail_href_raw)
        seller_detail_href = 'https://www.amazon.com/sp?' + re.split(re.compile(r'\?'), seller_detail_href_raw)[-1]
        # print(seller_detail_href)
        # 使用goto在本页访问卖家详情页，而点击按钮的话会打开新的标签页
        await page.goto(seller_detail_href)
        # 0不需要跳转，已在详情页
        return 0
    else:
        # 返回-1说明没有卖家信息，可以切换地区试一下
        return -1

# 选择地区
async def select_location(page):
    while await page.locator('#glow-ingress-block').count() == 0:
        print('刚开始就出现了错误页面，需要刷新')
        await page.reload()
    location = await page.locator('#glow-ingress-line2').inner_text()
    print('当前收货地址：%s' % (location))
    while not 'United Kingdom' in await page.locator('#glow-ingress-line2').inner_text() and not '英国' in await page.locator('#glow-ingress-line2').inner_text():
    # while not 'United Kingdom' in await page.locator('#glow-ingress-line2').inner_text() and not '英国' in await page.locator('#glow-ingress-line2').inner_text():
        if await page.locator('#nav-global-location-data-modal-action').count() == 0:
            print('打开的首页没有选择地区的按钮，需要刷新')
            page.reload()
        if await page.locator('#glow-ingress-block').count() > 0:
            print('点击地区按钮1')
            await page.locator('#glow-ingress-block').click()
        choose_country_btn_count = await page.locator('#GLUXCountryValue').count()
        if choose_country_btn_count == 0:
            print('选择地区的按钮是0，刷新页面')
            # print(await page.locator('#glow-ingress-line2').count())
            # await page.locator('#glow-ingress-line2').click()
            # await page.reload()
            await page.wait_for_timeout(1 * 1000)
            # continue
        await page.locator('#GLUXCountryValue').click()
        await page.locator('#GLUXCountryList_6').click()
        print('选择了United Kingdom')
        # await page.wait_for_timeout(2000)
        if 'United Kingdom' in await page.locator('#GLUXCountryValue').inner_text() or '英国' in await page.locator('#GLUXCountryValue').inner_text():
            print('是不是选对了:%s' % await page.locator('#GLUXCountryValue').inner_text())
            # await page.locator('#a-popover-1 > div > div.a-popover-footer > span').click()
            # await page.locator('#a-popover-3 > div > div.a-popover-footer > span').click()
            # time.sleep(3)
            await page.wait_for_timeout(500)
            # print(page)
            page.on("dialog", lambda dialog: dialog.accept())
            await page.get_by_role("button", name=re.compile(r"Done|完成", re.IGNORECASE)).click()
            await page.wait_for_timeout(3000)
            break

# 凡是goto和点击了按钮的后面都要处理亚马逊图片验证码
# 如果无法正常跳转，获取验证页面中的图片网址
async def validate(page):
    img_link = await page.get_attribute('div.a-row:nth-child(2) > img:nth-child(1)', 'src')
    # print(img_link)
    captcha = AmazonCaptcha.fromlink(img_link)
    solution = captcha.solve()
    await page.locator('#captchacharacters').fill(solution)
    await page.keyboard.press('Enter')
    return solution
# async def run(playwright):
async def get_merchant_addr(playwright, merchant):
    proxy={
        "server": "http://127.0.0.1:7890"
    }
    browser = await playwright.firefox.launch(headless=True, proxy=proxy)
    # browser = await playwright.firefox.launch(headless=False, proxy=proxy)
    # browser = await playwright.chromium.launch(headless=False, proxy=proxy)
    page = await browser.new_page()
    # 不接受这些图片
    await page.route('**/*.{png,jpeg}',lambda route: route.abort())
    asin = merchant['asin']
    # alive_page.append(page)
    # page.route('**/*.{png,jpeg}',lambda route: route.abort())
    # await page.route(re.compile(r"(\.png)|(\.jpeg)"), cancel_request)
    # 设置收货地址，因为有些商品无法显示某些地区的卖家
    # await page.goto('https://www.amazon.com/')
    # print('开始获取商品页')
    await page.goto(f"https://www.amazon.com/dp/{asin}")
    res_html = await page.content()
    # print(res_html)
    if 'Enter the characters you see below' in res_html:
        print('%s需要验证' % asin)
        await validate(page)
        print('%s验证完成' % asin)
        # await page.reload()
    # 等待页面加载完成
    await page.wait_for_timeout(1000)
    # 现在改成如果页面有卖家按钮的话就不选地区了
    # 初始化卖家数据结构
    merchant_info = {'row_index': merchant['row_index'],'asin':asin}
    # 设置禁止图片加载
    # page.route(re.compile(r"(\.png)|(\.jpeg)"), cancel_request)
    # page.route(re.compile(r"(\.png)|(\.jpg)|(\.jpeg)"), route.aobrt())
    try:
        # await page.goto(f"https://www.amazon.com/dp/{asin}")
        # print(response)
        html_text = await page.locator('html').nth(0).inner_text()
        if 'Enter the characters you see below' in html_text:
            print('%s需要验证'%asin)
            validate(page)
            print('%s验证完成'%asin)
        # 最好等待一下，要等待下面的特殊情况中出现（如果有的话）
        # await page.wait_for_timeout(2000)
        await page.wait_for_load_state('domcontentloaded')
        await page.wait_for_timeout(1000)
        # while True:
        #     print(await page.locator('#cross-border-widget-redirection-button').count())
        #     time.sleep(1)
        has_seller = await has_seller_info(page, asin)
        if has_seller >= 0:
            print('有卖家信息，继续进行 ')
        else:
            print('暂时没有卖家按钮，切换地区试试')
            await select_location(page)
            if await has_seller_info(page, asin) == -1:
                print('%s没有卖家按钮，将会返会None数据'%asin)
                merchant_info['name'] = 'None'
                merchant_info['address'] = 'None'
                return merchant_info
        # 可能会出现Sorry页面，刷新就行了
        # print(await page.title())
        while 'orry' in await page.title() or 'Not Found' in await page.title():
            print('%s出错了1，将会刷新'%asin)
            res_html = await page.content()
            with open('Sorry1.html', 'w', encoding='utf-8') as p:
                p.write(res_html)
            # 保存好页面3，当出故障时方便找原因
            await page.reload()
            # time.sleep(3)
            await page.wait_for_load_state('domcontentloaded')
            print('%s睡眠结束'%asin)
        # search_seller_btn_count = 0
        # 最新：现在直接检查是否有#page-section-detail-seller-info标签，
        # 有则说明有卖家地址，没有则说明没卖家地址，都将返回各自的数据，不再检查sellerProfileTriggerId
        # 到这里的时候，确定了如果有卖家信息是有卖家按钮的，没卖家按钮除了特殊情况1外都是没卖家信息的，可以直接返回卖家数据了
        # 前一个判断条件保证了只在商品页面进行之后的代码，前一个条件为False的话说明当前已经是卖家详情页面了
        # while not clicked_seller and await page.locator('#sellerProfileTriggerId').count() == 0:
        '''
        if not clicked_seller and await page.locator('#sellerProfileTriggerId').count() == 0:
        elif await page.locator('#sellerProfileTriggerId').count() > 0:
            # 进入卖家页面
            await page.locator('#sellerProfileTriggerId').nth(0).click()
        '''
        # 等待一下，否则下面的详情页面count为0
        await page.wait_for_load_state('domcontentloaded')
        await page.wait_for_timeout(1 * 1000)
        print('%s卖家页面目标标签数量：%d' % (asin, await page.locator('#page-section-detail-seller-info').count()))
        while await page.locator('#page-section-detail-seller-info').count() ==0 :
            print('%s没有：#page-section-detail-seller-info，需要刷新页面'%asin)
            res_html = await page.content()
            with open('page-section-detail-seller-info.html', 'w', encoding='utf-8') as p:
                p.write(res_html)
            await page.reload()
            # await page.wait_for_timeout(10 * 1000)
            await page.wait_for_load_state('domcontentloaded')
            print('%s睡眠结束'%asin)
        seller_row_text = await page.locator('#page-section-detail-seller-info').nth(0).inner_text()
        if len(seller_row_text) < 70 and (not '地址' in seller_row_text or 'Address' in seller_row_text):
            print('大概是没数据了，返回None')
            merchant_info['name'] = '手动搜索看一下'
            merchant_info['address'] = '手动搜索看一下'
            return merchant_info
        # print(seller_row_text)
        # print(len(seller_row_text))
        # time.sleep(100000)
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
        # print(merchant_info)
        await page.close()
        return merchant_info
    except Exception as e:
        print('%s错误信息：'%asin)
        print(e)
        print('%s将错误页面保存再退出'%asin)


def close_tag():
    print('关闭除首页外的所有标签页')
    global alive_page
    while len(alive_page) > 1:
        print('还有%d个标签页，关闭一个' % len(alive_page))
        alive_page[-1].close()
        alive_page.pop(-1)
    print('现在只剩首页了')

async def main(merchant):
    async with async_playwright() as playwright:
        # await run(playwright)
        merchant_info = await get_merchant_addr(playwright, merchant)
    print('%s协程工作完毕'%merchant['asin'])
    return merchant_info
async def all():
    # 获取所有的卖家，开n个协程，每个协程对应一个卖家
    # 将一个卖家放入协程，队列中弹出此卖家，工作中的协程数+1  【此种方法不行，协程可以同时开多个，一个一个开的话只能等待前一个完成才会开启下一个】
    # 协程运行完毕，工作中的协程数-1，再将一个卖家放入协程...如此循环下去，直到所有卖家处理完
    task_list = []
    asin = 'B0B6SS47TW'  # 有地址
    global batch_size
    count = 0
    # 获取用户目录
    home_dir = os.path.expanduser('~')
    # 设置工作目录
    origin_dir = os.path.join(home_dir, 'Desktop', 'amazon_task')
    # 目录不存在就创建 
    if not os.path.exists(origin_dir):  
        print('{0:+^80}'.format('工作目录不存在，已创建：【%s】'%origin_dir))
        print('{0:+^50}'.format('先把要处理的Excel文件放到此目录中，再继续运行程序'))
        os.mkdir(origin_dir)
        print('{0:+^50}'.format('按回车继续'))
        input('')
    origin_file = main_async.select_file(origin_dir=origin_dir)
    print('源文件：%s' % origin_file)
    # 先读取excel，获得要处理的卖家列表，每个元素是个字典，其应包含：row_index,asin,name,address
    meta_data_list = main_async.need_to_search(file_path=origin_file)
    # print(len(meta_data_list))
    while len(meta_data_list) > 0:
        # 循环开始时间，用于计算每次循环的耗时
        start_time = time.time()
        work_list = []
        while len(work_list) < batch_size:
            work_list.append(meta_data_list.pop(0))
    # for i in ['B00L524GH0']:
    # for i in ['B0B6SS47TW']:
    # for i in ['B0B6SS47TW', 'B06ZXWZNMG', 'B07YSP6YS5']:
        for i in work_list:
            print('启动了第%d行的%s' % (i['row_index'],i['asin']))
            if len(i['asin']) < 5:
                continue
            task_list.append(asyncio.create_task(main(i)))
        print('放入协程后的work_list长度%d' % len(work_list))
        merchant_info_list = await asyncio.gather(*task_list)
        # print('协程返回的结果： ')
        # print(merchant_info_list)
        # write_index = int(-str(batch_size))
        merchant_ready_to_write = merchant_info_list[-batch_size:]
        # print(merchant_ready_to_write)
        count = 1
        for merchant in merchant_ready_to_write:
            print('第%d个'%count)
            # print('即将写入的数据：')
            # print(merchant)
            if merchant is None:
                continue
            result = main_async.write_to_excel(origin_file, merchant)
            if result == -1:
                print('数据对不齐，请检查')
                break
            elif result == 0:
                print('数据为空，暂跳过，不写入')
                continue
            else:
                print('已经把%d条数据写入了excel'%count)
                count += 1
        end_time = time.time()
        now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))
        used_sec = int(end_time - start_time)
        print('用时%d秒，当前时间%s' %(used_sec, now))
        # time.sleep(1000)
# asyncio.run(main())
asyncio.run(all())
if __name__ == '__main__':
    # asin = 'B0B6SS47TW'  # 有地址
    # print(asin)
    pass