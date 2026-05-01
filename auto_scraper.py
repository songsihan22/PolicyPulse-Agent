#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知乎全自动爬虫 - 增强版 (含评论采集 + JSON存储)
1. 深度采集（捕获详细统计、完整内容、API监听）
2. 一级评论 + 二级楼中楼评论采集
3. 历史记录去重（爬过的不再爬）
4. 智能话题轮换（多领域全自动覆盖）
5. JSON格式层级存储（清晰易读，支持嵌套评论结构）
"""

import asyncio
from playwright.async_api import async_playwright
import json
import re
import random
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# ==========================================
# 话题矩阵 - 极速扩展版
# ==========================================
TOPIC_KEYWORDS = {
    "AI/数码": ["AI", "大模型", "AIGC", "ChatGPT", "Claude", "Transformer", "深度学习", "强化学习", "PyTorch", "数据分析", "芯片", "显卡", "苹果", "华为", "小米", "折叠屏", "自动驾驶", "机器人"],
    "编程/开发": ["Python", "Java", "C++", "Golang", "Rust", "前端", "后端", "微服务", "架构师", "程序员", "面试技巧", "GitHub", "LeetCode", "云计算", "Docker", "K8s", "数据库", "Redis", "分布式"],
    "经济/商业": ["宏观经济", "股市", "理财", "基金", "量化交易", "创业", "融资", "互联网", "电商", "拼多多", "美团", "阿里", "腾讯", "字节跳动", "华为", "全球贸易", "通货膨胀", "美联储"],
    "职场/升学": ["找工作", "简历", "面试", "公考", "考研", "留学", "高考", "专业选择", "升职加薪", "裁员", "35岁中年危机", "职业规划", "MBA", "保研", "调剂"],
    "社会/时政": ["国际局势", "乌克兰局势", "中东", "出生率", "人口老龄化", "延迟退休", "房价", "土地财政", "地方债", "法治教育", "公平正义", "婚姻观", "独生子女", "养老问题"],
    "生活/健康": ["健身", "减脂", "瑜伽", "中医", "皮肤护理", "抑郁症", "心理学", "失眠", "饮食健康", "抗衰老", "过敏", "近视", "脊柱健康", "牙医", "体检"],
    "人文/社科": ["历史", "考古", "哲学", "社会学", "女性主义", "心理学", "人类学", "文学", "诗歌", "艺术史", "古典音乐", "现代绘画", "翻译", "语言学"],
    "科学/科普": ["量子力学", "宇宙学", "航天", "生物演化", "脑科学", "材料科学", "可控核聚变", "超导", "数学模拟", "物理竞赛", "地理学", "气象学"],
    "艺术/审美": ["摄影", "短视频剪辑", "UI设计", "原画", "建筑设计", "室内装修", "潮玩", "盲盒", "香水", "腕表", "时尚穿搭", "奢侈品"],
    "娱乐/游戏": ["黑神话悟空", "原神", "英雄联盟", "Steam", "任天堂", "电影推荐", "美剧", "韩剧", "纪录片", "悬疑小说", "B站", "周杰伦", "乐评人"]
}

# 动态扩展词库
ADDITIONAL_SEEDS = ["为什么", "如何评价", "如何看待", "大家觉得", "有哪些", "有什么推荐", "怎么办", "逻辑", "真相", "深度解析"]

HISTORY_FILE = "scrape_history.json"

# 过往热榜归档目录
ARCHIVES_DIR = Path('./zhihu-trending-top-search/archives')

# 过滤条件
MIN_VISIT_COUNT = 50000  # 只爬取 question_visit_count > 此值的问题

# 风控保护
MAX_CONSECUTIVE_EMPTY = 5   # 连续N个问题爬不到任何回答时，自动停止（疑似风控）

# 延迟倍率（降低风控风险）
# 1.0 = 原始速度, 2.0 = 所有延迟翻倍, 3.0 = 三倍延迟
DELAY_MULTIPLIER = 1.5

# 评论采集配置
GET_ROOT_COMMENTS_NUM = 20      # 每个回答爬取多少条一级评论
GET_CHILD_COMMENTS = True       # 是否爬取二级评论(楼中楼)

# ==========================================
# 基础工具函数
# ==========================================

async def delay(low, high=None):
    """统一延迟函数，自动乘以 DELAY_MULTIPLIER"""
    if high is None:
        high = low
    await asyncio.sleep(random.uniform(low * DELAY_MULTIPLIER, high * DELAY_MULTIPLIER))

async def delay_fixed(seconds):
    """固定延迟，自动乘以 DELAY_MULTIPLIER"""
    await asyncio.sleep(seconds * DELAY_MULTIPLIER)

def clean_html(text):
    """清洗HTML标签"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip().replace("\n", " ").replace("\r", "")

def load_history():
    """加载已爬取记录"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"questions": [], "keywords": []}
    return {"questions": [], "keywords": []}

def save_history(history):
    """保存爬取记录"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

def update_history(question_id=None, keyword=None):
    """更新记录"""
    history = load_history()
    if "questions" not in history: history["questions"] = []
    if "keywords" not in history: history["keywords"] = []
    
    if question_id and str(question_id) not in history["questions"]:
        history["questions"].append(str(question_id))
    if keyword and keyword not in history["keywords"]:
        history["keywords"].append(keyword)
    save_history(history)

def parse_cookie_string(cookie_str, domain=".zhihu.com"):
    """将cookie字符串转换为Playwright格式"""
    cookies = []
    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            parts = item.split('=', 1)
            if len(parts) == 2:
                name, value = parts
                cookies.append({
                    "name": name.strip(), 
                    "value": value.strip(), 
                    "domain": domain, 
                    "path": "/"
                })
    return cookies

def save_session_json(filepath, data):
    """保存JSON数据到文件（每次覆盖，保证数据完整性）"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"   💾 已实时保存至: {Path(filepath).name}")

def parse_archive_file(filepath):
    """解析过往热榜归档文件，提取搜索关键词列表
    格式示例: 1. [标题](https://www.zhihu.com/search?q=关键词)
    返回: [(标题, 关键词), ...]
    """
    from urllib.parse import unquote, urlparse, parse_qs
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        # 匹配 [标题](URL) 格式
        pattern = r'\[([^\]]+)\]\((https?://[^)]+)\)'
        for match in re.finditer(pattern, content):
            title = match.group(1)
            url = match.group(2)
            # 从URL中提取 q= 参数
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            keyword = qs.get('q', [None])[0]
            if keyword:
                keyword = unquote(keyword)
                results.append((title, keyword))
    except Exception as e:
        print(f"   ⚠️ 解析归档文件失败 {filepath}: {e}")
    return results

# ==========================================
# 评论采集模块
# ==========================================

async def fetch_comments(context, question_id, answer_id):
    """
    获取一个回答的一级评论和二级楼中楼评论。
    返回: 一级评论列表（每条一级评论内嵌 child_comments 字段）
    """
    if GET_ROOT_COMMENTS_NUM <= 0:
        return []

    root_list = []
    url = (
        f"https://www.zhihu.com/api/v4/answers/{answer_id}/root_comments"
        f"?order=normal&limit={GET_ROOT_COMMENTS_NUM}&offset=0&status=open"
    )

    try:
        await delay(0.2, 0.5)
        response = await context.request.get(url)
        if response.status != 200:
            return []

        data = await response.json()
        for item in data.get('data', []):
            root_id = str(item.get('id'))

            root_comment = {
                "comment_id": root_id,
                "author": item.get('author', {}).get('member', {}).get('name', '匿名'),
                "content": clean_html(item.get('content', '')),
                "vote_count": item.get('vote_count', 0),
                "child_count": item.get('child_comment_count', 0),
                "created_time": datetime.fromtimestamp(
                    item.get('created_time', 0)
                ).strftime('%Y-%m-%d %H:%M'),
                "child_comments": []
            }

            # 获取二级楼中楼评论
            if GET_CHILD_COMMENTS and item.get('child_comment_count', 0) > 0:
                c_url = (
                    f"https://www.zhihu.com/api/v4/comments/{root_id}/child_comments"
                    f"?order=ts&limit=20&offset=0&status=open"
                )
                try:
                    await delay(0.1, 0.3)
                    c_resp = await context.request.get(c_url)
                    if c_resp.status == 200:
                        c_data = await c_resp.json()
                        for c_item in c_data.get('data', []):
                            root_comment["child_comments"].append({
                                "comment_id": str(c_item.get('id')),
                                "author": c_item.get('author', {}).get('member', {}).get('name', '匿名'),
                                "reply_to": c_item.get('reply_to_author', {}).get('member', {}).get('name', ''),
                                "content": clean_html(c_item.get('content', '')),
                                "vote_count": c_item.get('vote_count', 0),
                                "created_time": datetime.fromtimestamp(
                                    c_item.get('created_time', 0)
                                ).strftime('%Y-%m-%d %H:%M')
                            })
                except Exception:
                    pass

            root_list.append(root_comment)

    except Exception:
        pass

    return root_list

# ==========================================
# 核心获取逻辑
# ==========================================

async def auto_get_question_ids_from_hot(page, count=20) -> List[str]:
    """从知乎热榜自动获取问题ID"""
    print("\n🔥 自动获取知乎热榜问题...")
    try:
        await page.goto("https://www.zhihu.com/hot", wait_until="domcontentloaded", timeout=30000)
        await delay_fixed(3)
        
        question_ids = []
        for _ in range(10):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await delay_fixed(2)
            
            links = await page.locator('a[href*="/question/"]').all()
            for link in links:
                href = await link.get_attribute('href')
                if href and '/question/' in href:
                    match = re.search(r'/question/(\d+)', href)
                    if match:
                        qid = match.group(1)
                        if qid not in question_ids:
                            question_ids.append(qid)
                            if len(question_ids) >= count: break
            if len(question_ids) >= count: break
        
        print(f"✅ 获取了 {len(question_ids)} 个热门问题ID")
        return question_ids
    except Exception as e:
        print(f"❌ 获取热榜失败: {e}")
        return []

async def auto_get_question_ids_from_search(page, keyword, count=30) -> List[str]:
    """从搜索结果自动获取问题ID"""
    print(f"\n🔍 自动搜索: {keyword}")
    try:
        from urllib.parse import quote
        url = f"https://www.zhihu.com/search?type=content&q={quote(keyword)}"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await delay_fixed(3)
        
        question_ids = []
        for _ in range(5):
            links = await page.locator('a[href*="/question/"]').all()
            for link in links:
                href = await link.get_attribute('href')
                if href:
                    match = re.search(r'/question/(\d+)', href)
                    if match and match.group(1) not in question_ids:
                        question_ids.append(match.group(1))
            
            if len(question_ids) >= count: break
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await delay_fixed(2)
        
        print(f"✅ 获取了 {len(question_ids[:count])} 个问题ID")
        return question_ids[:count]
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        return []

async def scrape_single_question(page, context, question_id, max_answers=100) -> Dict:
    """爬取单个问题 - 含回答 + 一级评论 + 二级楼中楼评论"""
    all_answers = []
    question_info = {'question_id': question_id, 'title': '未知', 'tags': [], 'related_qids': []}
    api_captured = 0
    
    print(f"   📄 访问页面...")
    
    async def handle_response(response):
        nonlocal api_captured, question_info

        # 只处理JSON响应
        if "application/json" not in response.headers.get("content-type", ""):
            return

        # 1. 捕获统计数据 - 监听所有与该问题相关的API
        if str(question_id) in response.url:
            try:
                data = await response.json()

                # 打印所有相关API用于调试
                url_short = response.url.split('?')[0][-80:]
                print(f"   🔍 API: {url_short}")

                if isinstance(data, dict):
                    # 尝试从不同位置提取统计数据
                    stats_found = False

                    # 情况1: 直接在根级别
                    if 'follower_count' in data or 'visit_count' in data:
                        question_info.update({
                            'follower_count': data.get('follower_count', 0),
                            'visit_count': data.get('visit_count', 0),
                        })
                        stats_found = True

                    # 情况2: 在 question 字段中
                    elif 'question' in data and isinstance(data['question'], dict):
                        q = data['question']
                        if 'follower_count' in q or 'visit_count' in q:
                            question_info.update({
                                'follower_count': q.get('follower_count', 0),
                                'visit_count': q.get('visit_count', 0),
                            })
                            stats_found = True

                    # 情况3: 在 data 数组的第一项
                    elif 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                        first = data['data'][0]
                        if isinstance(first, dict):
                            # 检查是否有 question 字段
                            if 'question' in first and isinstance(first['question'], dict):
                                q = first['question']
                                if 'follower_count' in q or 'visit_count' in q:
                                    question_info.update({
                                        'follower_count': q.get('follower_count', 0),
                                        'visit_count': q.get('visit_count', 0),
                                    })
                                    stats_found = True
                            # 直接检查第一项
                            elif 'follower_count' in first or 'visit_count' in first:
                                question_info.update({
                                    'follower_count': first.get('follower_count', 0),
                                    'visit_count': first.get('visit_count', 0),
                                })
                                stats_found = True

                    if stats_found:
                        print(f"   ✅ 统计数据: 关注={question_info.get('follower_count', 0)}, 浏览={question_info.get('visit_count', 0)}")

            except Exception as e:
                pass  # 忽略非JSON响应
        
        # 2. 捕获回答内容
        if f"/questions/{question_id}/feeds" in response.url or f"/questions/{question_id}/answers" in response.url:
            try:
                data = await response.json()
                items = data.get('data', [])
                for item in items:
                    answer_item = item.get('target', item)
                    if answer_item.get('type') != 'answer': continue

                    # 提取时间字段（多种时间格式）
                    created_time = answer_item.get('created_time', 0)
                    updated_time = answer_item.get('updated_time', 0)

                    # 转换时间戳为可读格式（可选）
                    created_date = ''
                    if created_time:
                        try:
                            from datetime import datetime
                            created_date = datetime.fromtimestamp(created_time).strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            created_date = str(created_time)

                    content = answer_item.get('content', answer_item.get('excerpt', ''))
                    answer_data = {
                        "question_id": str(question_id),
                        "answer_id": str(answer_item.get('id', '')),
                        "author_name": answer_item.get('author', {}).get('name', '匿名用户'),
                        "voteup_count": answer_item.get('voteup_count', 0),
                        "comment_count": answer_item.get('comment_count', 0),
                        "created_time": created_time,
                        "created_date": created_date,
                        "updated_time": updated_time,
                        "content": content
                    }
                    if not any(a['answer_id'] == answer_data['answer_id'] for a in all_answers):
                        all_answers.append(answer_data)
            except Exception as e:
                print(f"   ⚠️ 解析回答API失败: {e}")

    page.on("response", handle_response)

    try:
        await page.goto(f"https://www.zhihu.com/question/{question_id}", wait_until="domcontentloaded", timeout=45000)
        await delay_fixed(1)

        # 【关键】不要点击任何按钮！直接滚动加载回答
        # 知乎的"查看全部"按钮会导致页面跳转，所以不使用
        print(f"   ℹ️ 跳过按钮点击，直接通过滚动加载回答")

        # 等待回答加载（无论是否点击了按钮）
        print(f"   ⏳ 等待回答加载...")
        await delay_fixed(1)

        # 获取标题和标签（确保页面加载完成）
        try:
            # 等待标题元素出现
            await page.wait_for_selector('h1.QuestionHeader-title', timeout=10000)
            title = await page.locator('h1.QuestionHeader-title').first.inner_text()
            question_info['title'] = title
            print(f"   ✅ 获取标题: {title[:30]}...")

            # 从DOM中提取标签作为备份
            if not question_info['tags']:
                try:
                    tag_locs = await page.locator('.QuestionHeader-topics .Tag-content').all()
                    question_info['tags'] = [await t.inner_text() for t in tag_locs]
                    print(f"   ✅ 获取标签: {question_info['tags']}")
                except:
                    print(f"   ⚠️ 无法获取标签")

            # 【关键】从DOM中提取统计数据（API中没有！）
            try:
                # 方法1: 从NumberBoard-value元素中提取（纯数字）
                value_elements = await page.locator('.NumberBoard-value').all()
                print(f"   🔍 找到 {len(value_elements)} 个NumberBoard-value元素")

                if len(value_elements) >= 2:
                    # 获取所有数字值
                    numbers = []
                    for elem in value_elements[:10]:  # 只看前10个
                        try:
                            text = await elem.inner_text()
                            print(f"      - {text}")
                            # 提取纯数字
                            num = int(re.sub(r'[^\d]', '', text))
                            numbers.append(num)
                        except:
                            continue

                    print(f"   🔍 提取到的数字: {numbers}")

                    # 通常第一个数字是关注数，最后一个大数字是浏览数
                    if len(numbers) >= 2:
                        # 排序后，较小的通常是关注数，较大的是浏览数
                        sorted_nums = sorted(numbers)
                        # 取第二小的作为关注数（避免异常值），取最大的作为浏览数
                        if len(sorted_nums) >= 2:
                            question_info['follower_count'] = sorted_nums[1] if sorted_nums[1] < 100000 else sorted_nums[0]
                            question_info['visit_count'] = sorted_nums[-1]
                            print(f"   ✅ DOM提取统计: 关注={question_info['follower_count']}, 浏览={question_info['visit_count']}")
                else:
                    # 方法2: 从QuestionFollowStatus解析完整文本
                    try:
                        status_elem = page.locator('.QuestionFollowStatus').first
                        full_text = await status_elem.inner_text()
                        print(f"   🔍 QuestionFollowStatus文本: {full_text[:100]}")

                        # 使用正则提取所有数字（包括逗号）
                        number_strings = re.findall(r'[\d,]+', full_text)
                        all_numbers = []
                        for ns in number_strings:
                            # 移除逗号并转换为整数
                            try:
                                all_numbers.append(int(ns.replace(',', '')))
                            except:
                                continue

                        print(f"   🔍 提取到的数字: {all_numbers}")

                        if len(all_numbers) >= 2:
                            # 同样的逻辑：较小的关注，较大的浏览
                            all_numbers.sort()
                            question_info['follower_count'] = all_numbers[0]
                            question_info['visit_count'] = all_numbers[-1]
                            print(f"   ✅ DOM提取统计: 关注={question_info['follower_count']}, 浏览={question_info['visit_count']}")
                    except Exception as e2:
                        print(f"   ⚠️ 方法2失败: {e2}")
            except Exception as e:
                print(f"   ⚠️ DOM提取统计异常: {e}")

            # 【Mode 4 优化】低浏览量提前跳过，避免浪费时间滚动
            visit_count = question_info.get('visit_count', 0)
            if visit_count > 0 and visit_count < 50000:
                print(f"   ⏩ 浏览量 {visit_count} < 50000，跳过滚动加载")
                return {"question": question_info, "answers": [], "skipped_low_visit": True}

            # 提取"相关问题"的ID (大杀器：实现指数级路径覆盖)
            related_links = await page.locator('a[href*="/question/"]').all()
            for link in related_links:
                href = await link.get_attribute('href')
                match = re.search(r'/question/(\d+)', href)
                if match and match.group(1) != str(question_id):
                    question_info['related_qids'].append(match.group(1))

        except Exception as e:
            print(f"   ❌ 获取标题失败: {e}")

        # 【关键】滚动前确保已有回答加载
        print(f"   📊 当前已捕获 {len(all_answers)} 个回答")

        # 如果还没有回答，等待更长时间
        initial_wait = 0
        while len(all_answers) == 0 and initial_wait < 5:
            print(f"   ⏳ 等待回答加载... ({initial_wait + 1}/5)")
            await delay_fixed(1)
            initial_wait += 1

        print(f"   📊 初始加载完成，已捕获 {len(all_answers)} 个回答")

        # 智能滚动：提前停止机制
        no_new_answers_count = 0  # 连续没新回答的次数
        last_count = len(all_answers)

        for i in range(50):  # 最大滚动次数
            if len(all_answers) >= max_answers:
                print(f"   ✅ 已达到最大回答数: {len(all_answers)}")
                break

            # 滚动前记录当前回答数
            count_before_scroll = len(all_answers)

            # 【关键】模拟真实用户行为：随机滚动距离和方向
            current_y = await page.evaluate("window.scrollY")
            max_height = await page.evaluate("document.body.scrollHeight")

            # 随机滚动行为（增加向上滑动频率，更像真人）
            import random
            scroll_behavior = random.choice([
                'normal',        # 正常向下
                'small',         # 小幅向下
                'up_then_down',  # 向上再向下
                'up_then_down',  # 向上再向下（增加出现频率）
                'pause'          # 停顿
            ])

            if scroll_behavior == 'up_then_down' and i > 0:
                # 向上滚一点，再向下
                up_distance = random.randint(300, 800)
                await page.evaluate(f"window.scrollTo(0, {max(0, current_y - up_distance)})")
                await delay(1, 2)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            elif scroll_behavior == 'small':
                # 小幅滚动
                await page.evaluate(f"window.scrollTo(0, {current_y + random.randint(200, 500)})")
            elif scroll_behavior == 'pause':
                # 停顿一下，不滚动
                await delay(2, 4)
            else:
                # 正常向下滚动到底
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # 随机等待时间：模拟人类阅读速度（降低风控风险）
            wait_time = random.uniform(3 * DELAY_MULTIPLIER, 6 * DELAY_MULTIPLIER)
            await asyncio.sleep(wait_time)

            # 等待新内容加载：如果滚动后没有新回答，额外等待
            count_after_scroll = len(all_answers)
            if count_after_scroll == count_before_scroll:
                await delay(1, 3)
                count_after_scroll = len(all_answers)

            # 打印进度（每10次滚动）
            if i % 10 == 0:
                print(f"   🔄 滚动进度: {i+1}/50 | 当前回答: {len(all_answers)}")

            # 智能检测：如果连续5次滚动都没新回答，提前退出
            current_count = len(all_answers)
            if current_count == last_count:
                no_new_answers_count += 1
                if no_new_answers_count >= 5:
                    print(f"   ⚡ 智能停止: 已捕获 {current_count} 个回答，无更多新内容")
                    break
            else:
                no_new_answers_count = 0
                last_count = current_count

        print(f"   ✅ 滚动完成，共捕获 {len(all_answers)} 个回答")
                
    except Exception as e:
        print(f"   ❌ 爬取异常: {e}")
    
    page.remove_listener("response", handle_response)

    # ========== 采集评论 ==========
    final_answers = all_answers[:max_answers]
    if final_answers:
        comment_total_root = 0
        comment_total_child = 0
        print(f"\n   💬 开始采集评论 (共 {len(final_answers)} 个回答)...")
        for idx, ans in enumerate(final_answers, 1):
            if int(ans.get('comment_count', 0)) > 0:
                root_comments = await fetch_comments(context, question_id, ans['answer_id'])
                ans['root_comments'] = root_comments
                n_root = len(root_comments)
                n_child = sum(len(c.get('child_comments', [])) for c in root_comments)
                comment_total_root += n_root
                comment_total_child += n_child
                if n_root > 0:
                    print(f"   💬 [{idx}/{len(final_answers)}] {ans.get('author_name', '?')}: "
                          f"{n_root}条一级 + {n_child}条二级")
            else:
                ans['root_comments'] = []

            # 每处理10个回答稍微休息一下
            if idx % 10 == 0:
                await delay(0.5, 1.5)

        print(f"   ✅ 评论采集完成: 共{comment_total_root}条一级 + {comment_total_child}条二级")

    return {'question': question_info, 'answers': final_answers}

# ==========================================
# 流程控制
# ==========================================

MIN_VISIT_COUNT_ENABLED = True  # 是否启用浏览量过滤（全局开关）

async def full_auto_scrape_flow(page, context, source="hot", keyword=None,
                              num_questions=5, answers_per_question=100, mode="search"):
    """
    完整爬取工作流：回答 + 一级评论 + 二级评论，JSON格式存储

    Args:
        page: Playwright page 对象
        context: Playwright browser context（用于评论API请求）
        mode: "hot" (热搜) 或 "auto" (自动模式) 或 "search" (关键词搜索)
    """
    history = load_history()
    scraped_qids = set(history.get("questions", []))

    # 根据模式确定保存目录
    if mode == "hot":
        output_dir = './results/hotrankings'
    elif mode == "auto":
        output_dir = './results/auto'
    else:
        output_dir = './results/search'

    print(f"\n📋 配置: {'热榜' if source == 'hot' else f'搜索「{keyword}」'} | 目标 {num_questions} 问 | {answers_per_question} 答/问")
    
    # 1. 找ID
    raw_ids = []
    if source == "hot":
        raw_ids = await auto_get_question_ids_from_hot(page, num_questions * 3)
    else:
        raw_ids = await auto_get_question_ids_from_search(page, keyword, num_questions * 3)
    
    # 2. 过滤
    todo_ids = []
    for qid in raw_ids:
        if qid not in scraped_qids:
            todo_ids.append(qid)
            if len(todo_ids) >= num_questions: break
        else:
            print(f"   ⏩ 跳过已记录问题: {qid}")
            
    if not todo_ids:
        print("   ⚠️  无新问题可采集")
        return []

    # 3. 批量爬（增量保存：每爬一个问题立即保存JSON）
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # === 崩溃恢复：检查是否有上次未完成的 temp 文件 ===
    existing_temps = sorted(Path(output_dir).glob('*_temp.json'))
    session_start_time = None
    temp_json_file = None
    session_data = None

    if existing_temps:
        # 尝试恢复最近的 temp 文件
        last_temp = existing_temps[-1]
        try:
            with open(last_temp, 'r', encoding='utf-8') as f:
                recovered = json.load(f)
            # 校验是否属于相同模式/关键词
            if recovered.get('mode') == mode and recovered.get('keyword') == keyword:
                session_data = recovered
                session_start_time = recovered.get('session_time', last_temp.stem.replace('_temp', ''))
                temp_json_file = last_temp
                recovered_qids = {q['question_id'] for q in session_data.get('questions', [])}
                print(f"   🔄 恢复上次未完成会话: {last_temp.name} (已有 {len(recovered_qids)} 个问题)")
        except Exception:
            pass

    if session_data is None:
        session_start_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_json_file = Path(output_dir) / f'{session_start_time}_temp.json'
        session_data = {
            "session_time": session_start_time,
            "mode": mode,
            "keyword": keyword,
            "questions": []
        }

    session_results = []
    consecutive_empty = 0  # 连续空结果计数（风控检测）

    for idx, qid in enumerate(todo_ids, 1):
        # 风控检测：连续多次空结果则自动停止
        if consecutive_empty >= MAX_CONSECUTIVE_EMPTY:
            print(f"\n🚨 连续 {consecutive_empty} 个问题未获取到任何回答，疑似触发风控！")
            print(f"   自动停止采集，请稍后再试或更换Cookie")
            break

        print(f"\n[{idx}/{len(todo_ids)}] 正在爬取: {qid}")
        result = await scrape_single_question(page, context, qid, answers_per_question)

        if result['answers']:
            consecutive_empty = 0  # 成功拿到数据，重置计数
            # 丰富数据：将问题级别信息写入每个回答
            for ans in result['answers']:
                ans['question_title'] = result['question'].get('title', '')
                ans['question_follower_count'] = result['question'].get('follower_count', 0)
                ans['question_visit_count'] = result['question'].get('visit_count', 0)

            # 浏览量过滤：如果开启了过滤且浏览量不达标，跳过该问题
            visit_count = result['question'].get('visit_count', 0)
            if MIN_VISIT_COUNT_ENABLED and visit_count < MIN_VISIT_COUNT:
                print(f"   ⏩ 跳过低浏览量问题: {result['question'].get('title', qid)} (浏览量={visit_count} < {MIN_VISIT_COUNT})")
                # 仍然记录到历史，避免重复爬取
                update_history(question_id=qid)
                continue

            # 构建问题级JSON对象
            question_data = {
                "question_id": str(qid),
                "title": result['question'].get('title', ''),
                "follower_count": result['question'].get('follower_count', 0),
                "visit_count": result['question'].get('visit_count', 0),
                "tags": result['question'].get('tags', []),
                "answers": result['answers']
            }
            session_data["questions"].append(question_data)

            print(f"   ✅ 已收集 {len(result['answers'])} 个回答(含评论)")

            # 每爬完一个问题立即覆盖保存JSON（防止中断丢失数据）
            save_session_json(temp_json_file, session_data)

            update_history(question_id=qid)
            session_results.append(result)

        else:
            consecutive_empty += 1
            print(f"   ⚠️ 未获取到回答 (连续空结果: {consecutive_empty}/{MAX_CONSECUTIVE_EMPTY})")
            update_history(question_id=qid)

        # 随机间歇（降低风控风险）
        if idx < len(todo_ids):
            wait = random.randint(int(10 * DELAY_MULTIPLIER), int(20 * DELAY_MULTIPLIER))
            print(f"   ⏰ 休息 {wait} 秒...")
            await asyncio.sleep(wait)

    # 4. 重命名为最终文件
    if session_data["questions"]:
        total_questions = len(session_data["questions"])
        total_answers = sum(len(q["answers"]) for q in session_data["questions"])
        final_json_filename = f'{session_start_time}_{total_questions}questions_{total_answers}answers.json'
        final_json_file = Path(output_dir) / final_json_filename

        temp_json_file.rename(final_json_file)
        print(f"\n✅ 最终保存: {total_questions}个问题, {total_answers}个回答(含评论) -> {final_json_file}")
    else:
        print(f"\n⚠️ 没有收集到任何回答")
        # 删除空的临时文件
        if temp_json_file.exists():
            temp_json_file.unlink()

    return session_results

async def archive_hot_scrape_mode(cookie_str):
    """
    爬取过往热榜模式：
    从 zhihu-trending-top-search/archives 目录读取每日热搜归档，
    提取关键词进行搜索，按日期保存到 results/archive_hot/{日期}.json，
    已爬过的问题不重复保存。
    """
    async with async_playwright() as p:
        print("\n" + "📜" * 25)
        print("🗂️  知乎过往热榜深度挖掘模式 (Archive Hot)")
        print("   📦 数据格式: JSON | 按日期分文件 | 含评论")
        print("📜" * 25)

        if not ARCHIVES_DIR.exists():
            print(f"❌ 归档目录不存在: {ARCHIVES_DIR}")
            return

        # 列出所有可用的归档日期
        archive_files = sorted(ARCHIVES_DIR.glob("*.md"))
        if not archive_files:
            print("❌ 归档目录中没有md文件")
            return

        date_range = f"{archive_files[0].stem} ~ {archive_files[-1].stem}"
        print(f"\n📅 可用归档范围: {date_range} (共 {len(archive_files)} 天)")

        # 用户选择日期范围
        start_date = input(f"请输入起始日期 (如 2024-01-01，回车默认最早): ").strip()
        end_date = input(f"请输入结束日期 (如 2024-12-31，回车默认最晚): ").strip()

        if not start_date:
            start_date = archive_files[0].stem
        if not end_date:
            end_date = archive_files[-1].stem

        # 过滤在范围内的文件
        selected_files = [f for f in archive_files if start_date <= f.stem <= end_date]
        if not selected_files:
            print(f"⚠️ 日期范围 {start_date} ~ {end_date} 内没有归档文件")
            return

        print(f"📋 将处理 {len(selected_files)} 天的热搜数据")

        # 每个问题爬多少回答
        answers_per = int(input("每个问题爬多少个回答？(默认50): ").strip() or "50")

        # 启动浏览器
        browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(user_agent="Mozilla/5.0")
        await context.add_cookies(parse_cookie_string(cookie_str))
        page = await context.new_page()

        output_base = Path('./results/archive_hot')
        output_base.mkdir(parents=True, exist_ok=True)

        history = load_history()
        scraped_qids = set(history.get("questions", []))
        # 跟踪已处理的归档日期（避免重复处理同一天）
        processed_dates = set(history.get("archive_dates", []))

        total_questions_scraped = 0
        consecutive_empty = 0  # 连续空结果计数（风控检测）
        rate_limited = False   # 风控标记

        for file_idx, archive_file in enumerate(selected_files, 1):
            if rate_limited:
                break

            date_str = archive_file.stem  # 如 2024-01-15

            if date_str in processed_dates:
                print(f"\n⏩ [{file_idx}/{len(selected_files)}] 跳过已处理日期: {date_str}")
                continue

            print(f"\n{'█' * 60}")
            print(f"📅 [{file_idx}/{len(selected_files)}] 处理日期: {date_str}")
            print(f"{'█' * 60}")

            # 解析该日期的热搜关键词
            entries = parse_archive_file(archive_file)
            if not entries:
                print(f"   ⚠️ 未找到关键词，跳过")
                continue

            print(f"   🔑 发现 {len(entries)} 个热搜关键词")

            # === 崩溃恢复：检查该日期是否有未完成的 temp 文件 ===
            temp_json_file = output_base / f'{date_str}_temp.json'
            date_session = None
            if temp_json_file.exists():
                try:
                    with open(temp_json_file, 'r', encoding='utf-8') as f:
                        date_session = json.load(f)
                    recovered_qids = {q['question_id'] for q in date_session.get('questions', [])}
                    scraped_qids.update(recovered_qids)
                    print(f"   🔄 恢复未完成数据: {temp_json_file.name} (已有 {len(recovered_qids)} 个问题)")
                except Exception:
                    date_session = None

            if date_session is None:
                date_session = {
                    "date": date_str,
                    "total_hot_topics": len(entries),
                    "questions": []
                }

            for kw_idx, (title, keyword) in enumerate(entries, 1):
                print(f"\n   🔍 [{kw_idx}/{len(entries)}] 热搜: {title} -> 搜索「{keyword}」")

                # 搜索该关键词获取问题ID
                try:
                    raw_ids = await auto_get_question_ids_from_search(page, keyword, count=5)
                except Exception as e:
                    print(f"   ❌ 搜索失败: {e}")
                    continue

                # 过滤已爬过的
                new_ids = [qid for qid in raw_ids if qid not in scraped_qids]
                if not new_ids:
                    print(f"   ⏩ 所有问题都已爬过，跳过")
                    continue

                print(f"   📝 发现 {len(new_ids)} 个新问题")

                for q_idx, qid in enumerate(new_ids[:3], 1):  # 每个关键词最多3个问题
                    # 风控检测
                    if consecutive_empty >= MAX_CONSECUTIVE_EMPTY:
                        print(f"\n🚨 连续 {consecutive_empty} 个问题未获取到任何回答，疑似触发风控！")
                        print(f"   自动停止采集，请稍后再试或更换Cookie")
                        rate_limited = True
                        break

                    print(f"\n   [{q_idx}/{min(len(new_ids), 3)}] 正在爬取问题: {qid}")
                    result = await scrape_single_question(page, context, qid, max_answers=answers_per)

                    # 低浏览量跳过（不计入风控检测）
                    if result.get('skipped_low_visit'):
                        print(f"   ⏩ 低浏览量跳过，不计入连续空结果")
                        update_history(question_id=qid)
                        scraped_qids.add(qid)
                        continue

                    if result['answers']:
                        consecutive_empty = 0  # 成功，重置计数
                        for ans in result['answers']:
                            ans['question_title'] = result['question'].get('title', '')
                            ans['question_follower_count'] = result['question'].get('follower_count', 0)
                            ans['question_visit_count'] = result['question'].get('visit_count', 0)

                        # 浏览量过滤
                        visit_count = result['question'].get('visit_count', 0)
                        if MIN_VISIT_COUNT_ENABLED and visit_count < MIN_VISIT_COUNT:
                            print(f"   ⏩ 跳过低浏览量: {result['question'].get('title', qid)} "
                                  f"(浏览量={visit_count} < {MIN_VISIT_COUNT})")
                            update_history(question_id=qid)
                            scraped_qids.add(qid)
                            continue

                        question_data = {
                            "question_id": str(qid),
                            "title": result['question'].get('title', ''),
                            "follower_count": result['question'].get('follower_count', 0),
                            "visit_count": result['question'].get('visit_count', 0),
                            "tags": result['question'].get('tags', []),
                            "hot_topic_title": title,
                            "hot_topic_keyword": keyword,
                            "answers": result['answers']
                        }
                        date_session["questions"].append(question_data)
                        total_questions_scraped += 1

                        # 实时保存
                        save_session_json(temp_json_file, date_session)

                    else:
                        consecutive_empty += 1
                        print(f"   ⚠️ 未获取到回答 (连续空结果: {consecutive_empty}/{MAX_CONSECUTIVE_EMPTY})")

                    update_history(question_id=qid)
                    scraped_qids.add(qid)

                    # 随机间歇
                    wait = random.randint(int(8 * DELAY_MULTIPLIER), int(15 * DELAY_MULTIPLIER))
                    print(f"   ⏰ 休息 {wait} 秒...")
                    await asyncio.sleep(wait)

                if rate_limited:
                    break

                # 关键词之间也休息
                await asyncio.sleep(random.randint(int(3 * DELAY_MULTIPLIER), int(8 * DELAY_MULTIPLIER)))

            # 该日期处理完毕，重命名文件
            if date_session["questions"]:
                n_q = len(date_session["questions"])
                n_a = sum(len(q["answers"]) for q in date_session["questions"])
                final_file = output_base / f'{date_str}_{n_q}questions_{n_a}answers.json'
                if temp_json_file.exists():
                    temp_json_file.rename(final_file)
                print(f"\n   ✅ 日期 {date_str} 完成: {n_q}个问题, {n_a}个回答 -> {final_file.name}")
            else:
                print(f"\n   ⚠️ 日期 {date_str} 无有效数据")
                if temp_json_file.exists():
                    temp_json_file.unlink()

            # 记录该日期已处理
            history = load_history()
            if "archive_dates" not in history:
                history["archive_dates"] = []
            if date_str not in history["archive_dates"]:
                history["archive_dates"].append(date_str)
            save_history(history)

            print(f"\n📊 累计已爬取: {total_questions_scraped} 个问题")

            # 日期之间的冷却
            if file_idx < len(selected_files):
                wait = random.randint(int(15 * DELAY_MULTIPLIER), int(30 * DELAY_MULTIPLIER))
                print(f"💤 日期切换冷却 ({wait}s)...")
                await asyncio.sleep(wait)

        await browser.close()
        print(f"\n🎉 过往热榜爬取完成！共爬取 {total_questions_scraped} 个问题")
        print(f"   数据保存在: {output_base}/")

async def smart_rotate_mode(cookie_str):
    """进入无限轮换模式：基于关键词+关联发现（JSON存储 + 评论采集）"""
    async with async_playwright() as p:
        print("\n" + "🚀" * 25)
        print("🌟 知乎无限数据挖掘引擎 (Infinite Discovery) 🌟")
        print("   📦 数据格式: JSON | 含一级评论 + 二级楼中楼")
        print("🚀" * 25)

        max_keywords = 5
        user_limit = input(f"\n🔢 最多爬取多少个关键词？(默认{max_keywords}, 输入0表示无限制): ").strip()
        if user_limit:
            max_keywords = int(user_limit)

        browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(user_agent="Mozilla/5.0")
        await context.add_cookies(parse_cookie_string(cookie_str))
        page = await context.new_page()

        history = load_history()
        already_used_keys = set(history.get("keywords", []))

        categories = list(TOPIC_KEYWORDS.keys()) + ["ADDITIONAL_SEEDS"]
        random.shuffle(categories)

        total_captured = 0
        keywords_processed = 0
        consecutive_empty = 0  # 连续空结果计数
        rate_limited = False

        for cat in categories:
            print(f"\n" + "█" * 60)
            print(f"📡 正在激活领域种子: 【{cat}】")
            print("█" * 60)

            seeds = TOPIC_KEYWORDS.get(cat, ADDITIONAL_SEEDS)
            random.shuffle(seeds)

            for keyword in seeds:
                if keyword in already_used_keys:
                    continue

                if max_keywords > 0 and keywords_processed >= max_keywords:
                    print(f"\n✅ 已达到最大关键词数量限制 ({max_keywords})，停止采集")
                    break

                if rate_limited:
                    print(f"\n🚫 检测到连续 {MAX_CONSECUTIVE_EMPTY} 次空结果，疑似风控，自动停止")
                    break

                keywords_processed += 1
                print(f"\n💎 深度挖掘关键词: 《{keyword}》 ({keywords_processed}/{max_keywords if max_keywords > 0 else '∞'})")
                results = await full_auto_scrape_flow(
                    page, context, source="search", keyword=keyword,
                    num_questions=15, answers_per_question=100, mode="auto"
                )

                if results:
                    consecutive_empty = 0  # 重置连续空结果计数
                    update_history(keyword=keyword)
                    total_captured += len(results)

                    # 关联发现逻辑
                    discovery_qids = []
                    new_tags = []
                    for r in results:
                        discovery_qids.extend(r['question'].get('related_qids', []))
                        new_tags.extend(r['question'].get('tags', []))

                    # 递归挖掘"相关问题"
                    discovery_qids = list(set(discovery_qids))[:8]
                    if discovery_qids:
                        print(f"   🔗 触发关联追踪: 发现 {len(discovery_qids)} 个深度关联问题...")
                        for dqid in discovery_qids:
                            history = load_history()
                            if str(dqid) in history.get("questions", []):
                                continue

                            print(f"   ↳ 追踪关联问题: {dqid}")
                            res = await scrape_single_question(page, context, dqid, max_answers=100)
                            if res['answers']:
                                for ans in res['answers']:
                                    ans['question_title'] = res['question'].get('title', '')
                                    ans['question_follower_count'] = res['question'].get('follower_count', 0)
                                    ans['question_visit_count'] = res['question'].get('visit_count', 0)

                                json_file = Path('./results/auto') / f'question_{dqid}.json'
                                Path('./results/auto').mkdir(parents=True, exist_ok=True)
                                question_data = {
                                    "question_id": str(dqid),
                                    "title": res['question'].get('title', ''),
                                    "follower_count": res['question'].get('follower_count', 0),
                                    "visit_count": res['question'].get('visit_count', 0),
                                    "tags": res['question'].get('tags', []),
                                    "answers": res['answers']
                                }
                                save_session_json(json_file, question_data)
                                update_history(question_id=dqid)
                                total_captured += 1
                                await asyncio.sleep(random.randint(int(5 * DELAY_MULTIPLIER), int(10 * DELAY_MULTIPLIER)))

                    # 挖掘"新标签"
                    new_tags = [t for t in new_tags if t and t not in seeds and t not in already_used_keys][:3]
                    if new_tags:
                        print(f"   🏷️  发现新话题标签: {new_tags}，已加入未来拓扑池")
                        for nt in new_tags:
                            update_history(keyword=nt)
                else:
                    consecutive_empty += 1
                    print(f"   ⚠️ 关键词 [{keyword}] 无结果 (连续空结果: {consecutive_empty}/{MAX_CONSECUTIVE_EMPTY})")
                    update_history(keyword=keyword)
                    if consecutive_empty >= MAX_CONSECUTIVE_EMPTY:
                        rate_limited = True
                        print(f"\n🚫 连续 {MAX_CONSECUTIVE_EMPTY} 次空结果，疑似风控，自动停止")
                        break

                print(f"📊 当前会话累计采集: {total_captured} 个问题")

                wait = random.randint(int(30 * DELAY_MULTIPLIER), int(60 * DELAY_MULTIPLIER))
                print(f"💤 防屏蔽冷却中 ({wait}s)...")
                await asyncio.sleep(wait)

                if max_keywords > 0 and keywords_processed >= max_keywords:
                    print(f"\n✅ 已完成 {keywords_processed} 个关键词的采集")
                    break

            if rate_limited:
                break

        await browser.close()

# ==========================================
# 入口函数
# ==========================================

async def main():
    print("=" * 60)
    print(" " * 10 + "🚀 知乎数据采集大师 (Enhanced + 评论)")
    print("   📦 数据格式: JSON | 含一级评论 + 二级楼中楼")
    print("=" * 60)

    # 读取Cookie
    try:
        with open('cookie.txt', 'r', encoding='utf-8') as f:
            cookie_str = f.read().strip()
            print("✅ 已加载 cookie.txt")
    except:
        print("❌ 错误: 未找到 cookie.txt")
        return

    print("\n请选择采矿模式:")
    print("  1. 全自动智能轮换 (多领域、全自动、话题发现) ⭐")
    print("  2. 指定关键词搜索 (单次任务)")
    print("  3. 全球热榜实时采集 (单次任务)")
    print("  4. 爬取过往热榜 (按日期归档) 📜")
    print("  0. 退出")

    choice = input("\n请选择 (1/2/3/4/0): ").strip()

    if choice == "1":
        await smart_rotate_mode(cookie_str)
    elif choice == "4":
        await archive_hot_scrape_mode(cookie_str)
    elif choice == "0":
        return
    else:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
            context = await browser.new_context()
            await context.add_cookies(parse_cookie_string(cookie_str))
            page = await context.new_page()

            if choice == "2":
                kw = input("\n请输入搜索关键词: ").strip()
                n = int(input("爬取多少个问题？(默认15): ") or "15")
                await full_auto_scrape_flow(page, context, source="search", keyword=kw, num_questions=n, mode="search")
            elif choice == "3":
                n = int(input("\n爬取多少个热榜问题？(默认15): ") or "15")
                await full_auto_scrape_flow(page, context, source="hot", num_questions=n, mode="hot")

            await browser.close()
            print("\n✅ 任务完成！数据已保存为JSON格式")

if __name__ == "__main__":
    asyncio.run(main())
