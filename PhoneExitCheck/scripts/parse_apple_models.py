import requests
from bs4 import BeautifulSoup
import json
import os
import random
import time
import argparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 随机User-Agent列表
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

def create_session():
    """
    创建带有重试机制和持久连接的session
    """
    session = requests.Session()
    
    # 设置重试策略
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session

def get_random_headers():
    """
    生成随机请求头
    """
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'DNT': '1',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"macOS"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://www.google.com/'
    }

def parse_html_content(html_content):
    """
    解析HTML内容，提取设备信息
    
    Args:
        html_content: HTML字符串
        
    Returns:
        dict: 以 identifier 为 Key 的设备信息 Map
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    device_map = {}
    
    # 查找所有表格
    tables = soup.find_all('table')
    print(f"找到 {len(tables)} 个表格")
    
    for table in tables:
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue
            
        headers = []
        
        # 获取表头
        header_row = rows[0]
        for th in header_row.find_all(['th', 'td']):
            headers.append(th.get_text(strip=True))
        
        # 检查是否是设备数据表格
        if 'Identifier' not in headers or len(headers) < 5:
            continue
        
        # 记录跨行合并的单元格值
        span_values = {}
        
        # 遍历数据行
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) == 0:
                continue
                
            device_info = {}
            identifier = None
            identifier_column_value = None
            
            # 如果数据列数少于表头列数，说明有跨行合并的单元格
            # 需要从之前的行继承值
            col_index = 0
            for i, header in enumerate(headers):
                # 检查当前列是否有跨行合并的值
                if i in span_values and span_values[i]['remaining'] > 0:
                    device_info[header] = span_values[i]['value']
                    # 检查Identifier列
                    if header == 'Identifier':
                        identifier_column_value = span_values[i]['value']
                    span_values[i]['remaining'] -= 1
                elif col_index < len(cells):
                    cell = cells[col_index]
                    value = cell.get_text(strip=True)
                    device_info[header] = value
                    
                    # 记录Identifier列的值
                    if header == 'Identifier':
                        identifier_column_value = value
                    
                    # 检查是否有 rowspan
                    rowspan = cell.get('rowspan')
                    if rowspan:
                        span_values[i] = {'value': value, 'remaining': int(rowspan) - 1}
                    
                    col_index += 1
                    
                    # 识别 identifier（通常包含逗号，如 iPhone1,1）
                    if ',' in value and (value.startswith('iPhone') or value.startswith('iPad') or value.startswith('iPod') or value.startswith('AppleTV') or value.startswith('Watch') or value.startswith('AudioAccessory')):
                        identifier = value
            
            # 跳过Identifier列值为Unknown的行
            if identifier_column_value == "Unknown":
                continue
                
            if identifier:
                device_map[identifier] = device_info
                print(f"添加设备: {identifier} -> {device_info.get('Model', 'Unknown')}")
    
    print(f"\n解析完成，共找到 {len(device_map)} 个设备")
    return device_map

def fetch_webpage_with_session(url):
    """
    使用session尝试获取网页内容
    """
    session = create_session()
    headers = get_random_headers()
    
    try:
        print(f"正在获取网页内容: {url}")
        print(f"使用User-Agent: {headers['User-Agent'][:50]}...")
        
        # 随机延迟，模拟人类行为
        time.sleep(random.uniform(1, 3))
        
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"网页获取成功，状态码: {response.status_code}")
        print(f"响应大小: {len(response.content)} 字节")
        
        return response.text
        
    except requests.exceptions.RequestException as e:
        print(f"获取网页失败: {e}")
        return None

def fetch_with_curl(url):
    """
    使用curl命令获取网页内容
    """
    import subprocess
    
    user_agent = random.choice(USER_AGENTS)
    
    cmd = [
        'curl',
        '-A', user_agent,
        '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        '-H', 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8',
        '-H', 'Accept-Encoding: gzip, deflate, br',
        '-H', 'Connection: keep-alive',
        '-H', 'Cache-Control: max-age=0',
        '-H', 'DNT: 1',
        '-H', 'Upgrade-Insecure-Requests: 1',
        '-H', 'Referer: https://www.google.com/',
        '--compressed',
        '-L',
        '-m', '30',
        url
    ]
    
    try:
        print(f"正在使用curl获取网页: {url}")
        print(f"使用User-Agent: {user_agent[:50]}...")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"curl获取成功，响应大小: {len(result.stdout)} 字节")
            return result.stdout
        else:
            print(f"curl获取失败，错误: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("curl请求超时")
        return None
    except Exception as e:
        print(f"curl执行失败: {e}")
        return None

def fetch_webpage(url):
    """
    尝试多种方法获取网页内容
    """
    # 方法1: 使用requests session
    print("方法1: 使用requests session...")
    content = fetch_webpage_with_session(url)
    if content:
        return content
    
    # 方法2: 使用curl命令
    print("\n方法2: 使用curl命令...")
    content = fetch_with_curl(url)
    if content:
        return content
    
    return None

def load_from_file(filepath):
    """
    从本地文件加载HTML内容
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"成功从文件加载内容: {filepath}")
        return content
    except Exception as e:
        print(f"加载文件失败: {e}")
        return None

def get_fallback_data():
    """
    提供备用数据（基于公开的Apple设备型号信息）
    """
    print("使用备用数据源...")
    
    fallback_data = {
        # iPad
        "iPad1,1": {"Model": "iPad", "Identifier": "iPad1,1"},
        "iPad2,1": {"Model": "iPad 2 (WiFi)", "Identifier": "iPad2,1"},
        "iPad2,2": {"Model": "iPad 2 (GSM)", "Identifier": "iPad2,2"},
        "iPad2,3": {"Model": "iPad 2 (CDMA)", "Identifier": "iPad2,3"},
        "iPad2,4": {"Model": "iPad 2 (Mid 2012)", "Identifier": "iPad2,4"},
        "iPad3,1": {"Model": "iPad (3rd generation) WiFi", "Identifier": "iPad3,1"},
        "iPad3,2": {"Model": "iPad (3rd generation) CDMA", "Identifier": "iPad3,2"},
        "iPad3,3": {"Model": "iPad (3rd generation) GSM", "Identifier": "iPad3,3"},
        "iPad3,4": {"Model": "iPad (4th generation) WiFi", "Identifier": "iPad3,4"},
        "iPad3,5": {"Model": "iPad (4th generation) GSM", "Identifier": "iPad3,5"},
        "iPad3,6": {"Model": "iPad (4th generation) Global", "Identifier": "iPad3,6"},
        "iPad4,1": {"Model": "iPad Air WiFi", "Identifier": "iPad4,1"},
        "iPad4,2": {"Model": "iPad Air Cellular", "Identifier": "iPad4,2"},
        "iPad4,3": {"Model": "iPad Air China", "Identifier": "iPad4,3"},
        "iPad4,4": {"Model": "iPad mini 2 WiFi", "Identifier": "iPad4,4"},
        "iPad4,5": {"Model": "iPad mini 2 Cellular", "Identifier": "iPad4,5"},
        "iPad4,6": {"Model": "iPad mini 2 China", "Identifier": "iPad4,6"},
        "iPad4,7": {"Model": "iPad mini 3 WiFi", "Identifier": "iPad4,7"},
        "iPad4,8": {"Model": "iPad mini 3 Cellular", "Identifier": "iPad4,8"},
        "iPad4,9": {"Model": "iPad mini 3 China", "Identifier": "iPad4,9"},
        "iPad5,1": {"Model": "iPad mini 4 WiFi", "Identifier": "iPad5,1"},
        "iPad5,2": {"Model": "iPad mini 4 Cellular", "Identifier": "iPad5,2"},
        "iPad5,3": {"Model": "iPad Air 2 WiFi", "Identifier": "iPad5,3"},
        "iPad5,4": {"Model": "iPad Air 2 Cellular", "Identifier": "iPad5,4"},
        "iPad6,3": {"Model": "iPad Pro (9.7-inch) WiFi", "Identifier": "iPad6,3"},
        "iPad6,4": {"Model": "iPad Pro (9.7-inch) Cellular", "Identifier": "iPad6,4"},
        "iPad6,7": {"Model": "iPad Pro (12.9-inch) WiFi", "Identifier": "iPad6,7"},
        "iPad6,8": {"Model": "iPad Pro (12.9-inch) Cellular", "Identifier": "iPad6,8"},
        "iPad6,11": {"Model": "iPad (5th generation) WiFi", "Identifier": "iPad6,11"},
        "iPad6,12": {"Model": "iPad (5th generation) Cellular", "Identifier": "iPad6,12"},
        "iPad7,1": {"Model": "iPad Pro (12.9-inch) (2nd generation) WiFi", "Identifier": "iPad7,1"},
        "iPad7,2": {"Model": "iPad Pro (12.9-inch) (2nd generation) Cellular", "Identifier": "iPad7,2"},
        "iPad7,3": {"Model": "iPad Pro (10.5-inch) WiFi", "Identifier": "iPad7,3"},
        "iPad7,4": {"Model": "iPad Pro (10.5-inch) Cellular", "Identifier": "iPad7,4"},
        "iPad7,5": {"Model": "iPad (6th generation) WiFi", "Identifier": "iPad7,5"},
        "iPad7,6": {"Model": "iPad (6th generation) Cellular", "Identifier": "iPad7,6"},
        "iPad7,11": {"Model": "iPad (7th generation) WiFi", "Identifier": "iPad7,11"},
        "iPad7,12": {"Model": "iPad (7th generation) Cellular", "Identifier": "iPad7,12"},
        "iPad8,1": {"Model": "iPad Pro (11-inch) WiFi", "Identifier": "iPad8,1"},
        "iPad8,2": {"Model": "iPad Pro (11-inch) WiFi 1TB", "Identifier": "iPad8,2"},
        "iPad8,3": {"Model": "iPad Pro (11-inch) Cellular", "Identifier": "iPad8,3"},
        "iPad8,4": {"Model": "iPad Pro (11-inch) Cellular 1TB", "Identifier": "iPad8,4"},
        "iPad8,5": {"Model": "iPad Pro (12.9-inch) (3rd generation) WiFi", "Identifier": "iPad8,5"},
        "iPad8,6": {"Model": "iPad Pro (12.9-inch) (3rd generation) WiFi 1TB", "Identifier": "iPad8,6"},
        "iPad8,7": {"Model": "iPad Pro (12.9-inch) (3rd generation) Cellular", "Identifier": "iPad8,7"},
        "iPad8,8": {"Model": "iPad Pro (12.9-inch) (3rd generation) Cellular 1TB", "Identifier": "iPad8,8"},
        "iPad8,9": {"Model": "iPad Pro (11-inch) (2nd generation) WiFi", "Identifier": "iPad8,9"},
        "iPad8,10": {"Model": "iPad Pro (11-inch) (2nd generation) Cellular", "Identifier": "iPad8,10"},
        "iPad8,11": {"Model": "iPad Pro (12.9-inch) (4th generation) WiFi", "Identifier": "iPad8,11"},
        "iPad8,12": {"Model": "iPad Pro (12.9-inch) (4th generation) Cellular", "Identifier": "iPad8,12"},
        "iPad11,1": {"Model": "iPad mini (5th generation) WiFi", "Identifier": "iPad11,1"},
        "iPad11,2": {"Model": "iPad mini (5th generation) Cellular", "Identifier": "iPad11,2"},
        "iPad11,3": {"Model": "iPad Air (3rd generation) WiFi", "Identifier": "iPad11,3"},
        "iPad11,4": {"Model": "iPad Air (3rd generation) Cellular", "Identifier": "iPad11,4"},
        "iPad11,6": {"Model": "iPad (8th generation) WiFi", "Identifier": "iPad11,6"},
        "iPad11,7": {"Model": "iPad (8th generation) Cellular", "Identifier": "iPad11,7"},
        "iPad12,1": {"Model": "iPad (9th generation) WiFi", "Identifier": "iPad12,1"},
        "iPad12,2": {"Model": "iPad (9th generation) Cellular", "Identifier": "iPad12,2"},
        "iPad13,1": {"Model": "iPad Air (4th generation) WiFi", "Identifier": "iPad13,1"},
        "iPad13,2": {"Model": "iPad Air (4th generation) Cellular", "Identifier": "iPad13,2"},
        "iPad13,4": {"Model": "iPad Pro (11-inch) (3rd generation) WiFi", "Identifier": "iPad13,4"},
        "iPad13,5": {"Model": "iPad Pro (11-inch) (3rd generation) Cellular", "Identifier": "iPad13,5"},
        "iPad13,6": {"Model": "iPad Pro (11-inch) (3rd generation) WiFi mmWave", "Identifier": "iPad13,6"},
        "iPad13,7": {"Model": "iPad Pro (11-inch) (3rd generation) Cellular mmWave", "Identifier": "iPad13,7"},
        "iPad13,8": {"Model": "iPad Pro (12.9-inch) (5th generation) WiFi", "Identifier": "iPad13,8"},
        "iPad13,9": {"Model": "iPad Pro (12.9-inch) (5th generation) Cellular", "Identifier": "iPad13,9"},
        "iPad13,10": {"Model": "iPad Pro (12.9-inch) (5th generation) WiFi mmWave", "Identifier": "iPad13,10"},
        "iPad13,11": {"Model": "iPad Pro (12.9-inch) (5th generation) Cellular mmWave", "Identifier": "iPad13,11"},
        "iPad13,16": {"Model": "iPad Air (5th generation) WiFi", "Identifier": "iPad13,16"},
        "iPad13,17": {"Model": "iPad Air (5th generation) Cellular", "Identifier": "iPad13,17"},
        "iPad13,18": {"Model": "iPad (10th generation) WiFi", "Identifier": "iPad13,18"},
        "iPad13,19": {"Model": "iPad (10th generation) Cellular", "Identifier": "iPad13,19"},
        "iPad14,1": {"Model": "iPad mini (6th generation) WiFi", "Identifier": "iPad14,1"},
        "iPad14,2": {"Model": "iPad mini (6th generation) Cellular", "Identifier": "iPad14,2"},
        "iPad14,3": {"Model": "iPad Pro (11-inch) (4th generation) WiFi", "Identifier": "iPad14,3"},
        "iPad14,4": {"Model": "iPad Pro (11-inch) (4th generation) Cellular", "Identifier": "iPad14,4"},
        "iPad14,5": {"Model": "iPad Pro (12.9-inch) (6th generation) WiFi", "Identifier": "iPad14,5"},
        "iPad14,6": {"Model": "iPad Pro (12.9-inch) (6th generation) Cellular", "Identifier": "iPad14,6"},
        
        # iPhone
        "iPhone1,1": {"Model": "iPhone", "Identifier": "iPhone1,1"},
        "iPhone1,2": {"Model": "iPhone 3G", "Identifier": "iPhone1,2"},
        "iPhone2,1": {"Model": "iPhone 3GS", "Identifier": "iPhone2,1"},
        "iPhone3,1": {"Model": "iPhone 4 (GSM)", "Identifier": "iPhone3,1"},
        "iPhone3,2": {"Model": "iPhone 4 (GSM 2012)", "Identifier": "iPhone3,2"},
        "iPhone3,3": {"Model": "iPhone 4 (CDMA)", "Identifier": "iPhone3,3"},
        "iPhone4,1": {"Model": "iPhone 4S", "Identifier": "iPhone4,1"},
        "iPhone5,1": {"Model": "iPhone 5 (GSM)", "Identifier": "iPhone5,1"},
        "iPhone5,2": {"Model": "iPhone 5 (Global)", "Identifier": "iPhone5,2"},
        "iPhone5,3": {"Model": "iPhone 5c (GSM)", "Identifier": "iPhone5,3"},
        "iPhone5,4": {"Model": "iPhone 5c (Global)", "Identifier": "iPhone5,4"},
        "iPhone6,1": {"Model": "iPhone 5s (GSM)", "Identifier": "iPhone6,1"},
        "iPhone6,2": {"Model": "iPhone 5s (Global)", "Identifier": "iPhone6,2"},
        "iPhone7,1": {"Model": "iPhone 6 Plus", "Identifier": "iPhone7,1"},
        "iPhone7,2": {"Model": "iPhone 6", "Identifier": "iPhone7,2"},
        "iPhone8,1": {"Model": "iPhone 6s", "Identifier": "iPhone8,1"},
        "iPhone8,2": {"Model": "iPhone 6s Plus", "Identifier": "iPhone8,2"},
        "iPhone8,4": {"Model": "iPhone SE (1st generation)", "Identifier": "iPhone8,4"},
        "iPhone9,1": {"Model": "iPhone 7 (Global)", "Identifier": "iPhone9,1"},
        "iPhone9,2": {"Model": "iPhone 7 Plus (Global)", "Identifier": "iPhone9,2"},
        "iPhone9,3": {"Model": "iPhone 7 (GSM)", "Identifier": "iPhone9,3"},
        "iPhone9,4": {"Model": "iPhone 7 Plus (GSM)", "Identifier": "iPhone9,4"},
        "iPhone10,1": {"Model": "iPhone 8 (Global)", "Identifier": "iPhone10,1"},
        "iPhone10,2": {"Model": "iPhone 8 Plus (Global)", "Identifier": "iPhone10,2"},
        "iPhone10,3": {"Model": "iPhone X (Global)", "Identifier": "iPhone10,3"},
        "iPhone10,4": {"Model": "iPhone 8 (GSM)", "Identifier": "iPhone10,4"},
        "iPhone10,5": {"Model": "iPhone 8 Plus (GSM)", "Identifier": "iPhone10,5"},
        "iPhone10,6": {"Model": "iPhone X (GSM)", "Identifier": "iPhone10,6"},
        "iPhone11,1": {"Model": "iPhone XR", "Identifier": "iPhone11,1"},
        "iPhone11,2": {"Model": "iPhone XS", "Identifier": "iPhone11,2"},
        "iPhone11,3": {"Model": "iPhone XS Max", "Identifier": "iPhone11,3"},
        "iPhone11,4": {"Model": "iPhone XS Max (China)", "Identifier": "iPhone11,4"},
        "iPhone11,5": {"Model": "iPhone XS (China)", "Identifier": "iPhone11,5"},
        "iPhone11,6": {"Model": "iPhone XS Max", "Identifier": "iPhone11,6"},
        "iPhone12,1": {"Model": "iPhone 11", "Identifier": "iPhone12,1"},
        "iPhone12,2": {"Model": "iPhone 11 Pro", "Identifier": "iPhone12,2"},
        "iPhone12,3": {"Model": "iPhone 11 Pro Max", "Identifier": "iPhone12,3"},
        "iPhone12,4": {"Model": "iPhone 11 Pro", "Identifier": "iPhone12,4"},
        "iPhone12,5": {"Model": "iPhone 11 Pro Max", "Identifier": "iPhone12,5"},
        "iPhone12,8": {"Model": "iPhone SE (2nd generation)", "Identifier": "iPhone12,8"},
        "iPhone13,1": {"Model": "iPhone 12 mini", "Identifier": "iPhone13,1"},
        "iPhone13,2": {"Model": "iPhone 12", "Identifier": "iPhone13,2"},
        "iPhone13,3": {"Model": "iPhone 12 Pro", "Identifier": "iPhone13,3"},
        "iPhone13,4": {"Model": "iPhone 12 Pro Max", "Identifier": "iPhone13,4"},
        "iPhone14,1": {"Model": "iPhone 13", "Identifier": "iPhone14,1"},
        "iPhone14,2": {"Model": "iPhone 13 Pro", "Identifier": "iPhone14,2"},
        "iPhone14,3": {"Model": "iPhone 13 Pro Max", "Identifier": "iPhone14,3"},
        "iPhone14,4": {"Model": "iPhone 13 mini", "Identifier": "iPhone14,4"},
        "iPhone14,5": {"Model": "iPhone 13", "Identifier": "iPhone14,5"},
        "iPhone14,6": {"Model": "iPhone SE (3rd generation)", "Identifier": "iPhone14,6"},
        "iPhone14,7": {"Model": "iPhone 14", "Identifier": "iPhone14,7"},
        "iPhone14,8": {"Model": "iPhone 14 Plus", "Identifier": "iPhone14,8"},
        "iPhone15,2": {"Model": "iPhone 14 Pro", "Identifier": "iPhone15,2"},
        "iPhone15,3": {"Model": "iPhone 14 Pro Max", "Identifier": "iPhone15,3"},
        "iPhone15,4": {"Model": "iPhone 15", "Identifier": "iPhone15,4"},
        "iPhone15,5": {"Model": "iPhone 15 Plus", "Identifier": "iPhone15,5"},
        "iPhone16,1": {"Model": "iPhone 15 Pro", "Identifier": "iPhone16,1"},
        "iPhone16,2": {"Model": "iPhone 15 Pro Max", "Identifier": "iPhone16,2"},
        
        # iPod touch
        "iPod1,1": {"Model": "iPod touch (1st generation)", "Identifier": "iPod1,1"},
        "iPod2,1": {"Model": "iPod touch (2nd generation)", "Identifier": "iPod2,1"},
        "iPod3,1": {"Model": "iPod touch (3rd generation)", "Identifier": "iPod3,1"},
        "iPod4,1": {"Model": "iPod touch (4th generation)", "Identifier": "iPod4,1"},
        "iPod5,1": {"Model": "iPod touch (5th generation)", "Identifier": "iPod5,1"},
        "iPod7,1": {"Model": "iPod touch (6th generation)", "Identifier": "iPod7,1"},
        "iPod9,1": {"Model": "iPod touch (7th generation)", "Identifier": "iPod9,1"},
        
        # Apple TV
        "AppleTV1,1": {"Model": "Apple TV (1st generation)", "Identifier": "AppleTV1,1"},
        "AppleTV2,1": {"Model": "Apple TV (2nd generation)", "Identifier": "AppleTV2,1"},
        "AppleTV3,1": {"Model": "Apple TV (3rd generation)", "Identifier": "AppleTV3,1"},
        "AppleTV3,2": {"Model": "Apple TV (3rd generation) Rev A", "Identifier": "AppleTV3,2"},
        "AppleTV5,3": {"Model": "Apple TV HD", "Identifier": "AppleTV5,3"},
        "AppleTV6,2": {"Model": "Apple TV 4K (1st generation)", "Identifier": "AppleTV6,2"},
        "AppleTV11,1": {"Model": "Apple TV 4K (2nd generation)", "Identifier": "AppleTV11,1"},
        "AppleTV14,1": {"Model": "Apple TV 4K (3rd generation)", "Identifier": "AppleTV14,1"},
        
        # Apple Watch
        "Watch1,1": {"Model": "Apple Watch (1st generation) 38mm", "Identifier": "Watch1,1"},
        "Watch1,2": {"Model": "Apple Watch (1st generation) 42mm", "Identifier": "Watch1,2"},
        "Watch2,6": {"Model": "Apple Watch Series 1 38mm", "Identifier": "Watch2,6"},
        "Watch2,7": {"Model": "Apple Watch Series 1 42mm", "Identifier": "Watch2,7"},
        "Watch2,1": {"Model": "Apple Watch Series 2 38mm", "Identifier": "Watch2,1"},
        "Watch2,2": {"Model": "Apple Watch Series 2 42mm", "Identifier": "Watch2,2"},
        "Watch3,1": {"Model": "Apple Watch Series 3 38mm GPS", "Identifier": "Watch3,1"},
        "Watch3,2": {"Model": "Apple Watch Series 3 42mm GPS", "Identifier": "Watch3,2"},
        "Watch3,3": {"Model": "Apple Watch Series 3 38mm GPS+Cellular", "Identifier": "Watch3,3"},
        "Watch3,4": {"Model": "Apple Watch Series 3 42mm GPS+Cellular", "Identifier": "Watch3,4"},
        "Watch4,1": {"Model": "Apple Watch Series 4 40mm GPS", "Identifier": "Watch4,1"},
        "Watch4,2": {"Model": "Apple Watch Series 4 44mm GPS", "Identifier": "Watch4,2"},
        "Watch4,3": {"Model": "Apple Watch Series 4 40mm GPS+Cellular", "Identifier": "Watch4,3"},
        "Watch4,4": {"Model": "Apple Watch Series 4 44mm GPS+Cellular", "Identifier": "Watch4,4"},
        "Watch5,1": {"Model": "Apple Watch Series 5 40mm GPS", "Identifier": "Watch5,1"},
        "Watch5,2": {"Model": "Apple Watch Series 5 44mm GPS", "Identifier": "Watch5,2"},
        "Watch5,3": {"Model": "Apple Watch Series 5 40mm GPS+Cellular", "Identifier": "Watch5,3"},
        "Watch5,4": {"Model": "Apple Watch Series 5 44mm GPS+Cellular", "Identifier": "Watch5,4"},
        "Watch6,1": {"Model": "Apple Watch Series 6 40mm GPS", "Identifier": "Watch6,1"},
        "Watch6,2": {"Model": "Apple Watch Series 6 44mm GPS", "Identifier": "Watch6,2"},
        "Watch6,3": {"Model": "Apple Watch Series 6 40mm GPS+Cellular", "Identifier": "Watch6,3"},
        "Watch6,4": {"Model": "Apple Watch Series 6 44mm GPS+Cellular", "Identifier": "Watch6,4"},
        "Watch7,1": {"Model": "Apple Watch Series 7 41mm GPS", "Identifier": "Watch7,1"},
        "Watch7,2": {"Model": "Apple Watch Series 7 45mm GPS", "Identifier": "Watch7,2"},
        "Watch7,3": {"Model": "Apple Watch Series 7 41mm GPS+Cellular", "Identifier": "Watch7,3"},
        "Watch7,4": {"Model": "Apple Watch Series 7 45mm GPS+Cellular", "Identifier": "Watch7,4"},
        "Watch8,1": {"Model": "Apple Watch Series 8 41mm GPS", "Identifier": "Watch8,1"},
        "Watch8,2": {"Model": "Apple Watch Series 8 45mm GPS", "Identifier": "Watch8,2"},
        "Watch8,3": {"Model": "Apple Watch Series 8 41mm GPS+Cellular", "Identifier": "Watch8,3"},
        "Watch8,4": {"Model": "Apple Watch Series 8 45mm GPS+Cellular", "Identifier": "Watch8,4"},
        "Watch9,1": {"Model": "Apple Watch Series 9 41mm GPS", "Identifier": "Watch9,1"},
        "Watch9,2": {"Model": "Apple Watch Series 9 45mm GPS", "Identifier": "Watch9,2"},
        "Watch9,3": {"Model": "Apple Watch Series 9 41mm GPS+Cellular", "Identifier": "Watch9,3"},
        "Watch9,4": {"Model": "Apple Watch Series 9 45mm GPS+Cellular", "Identifier": "Watch9,4"},
        "Watch10,1": {"Model": "Apple Watch Series 10 42mm GPS", "Identifier": "Watch10,1"},
        "Watch10,2": {"Model": "Apple Watch Series 10 46mm GPS", "Identifier": "Watch10,2"},
        "Watch10,3": {"Model": "Apple Watch Series 10 42mm GPS+Cellular", "Identifier": "Watch10,3"},
        "Watch10,4": {"Model": "Apple Watch Series 10 46mm GPS+Cellular", "Identifier": "Watch10,4"},
        
        # HomePod
        "AudioAccessory1,1": {"Model": "HomePod", "Identifier": "AudioAccessory1,1"},
        "AudioAccessory2,1": {"Model": "HomePod mini", "Identifier": "AudioAccessory2,1"},
        "AudioAccessory3,1": {"Model": "HomePod (2nd generation)", "Identifier": "AudioAccessory3,1"}
    }
    
    print(f"备用数据共包含 {len(fallback_data)} 个设备")
    return fallback_data

def save_to_json(data, filename):
    """
    将数据保存到 JSON 文件
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到: {filename}")
    except Exception as e:
        print(f"保存文件失败: {e}")

def main():
    parser = argparse.ArgumentParser(description='Apple设备型号解析脚本')
    parser.add_argument('--html', help='HTML文件路径')
    parser.add_argument('--output', help='输出JSON文件路径')
    args = parser.parse_args()
    
    # 使用命令行参数或默认值
    local_file = args.html if args.html else "/Users/computer/Desktop/NewPods/Models - The Apple Wiki.html"
    output_file = args.output if args.output else "apple_device_models.json"
    
    print("=" * 60)
    print("Apple 设备型号解析脚本")
    print("=" * 60)
    print(f"读取本地文件: {local_file}")
    print(f"输出文件: {output_file}")
    print("=" * 60)
    
    # 1. 尝试从本地文件加载
    html_content = load_from_file(local_file)
    
    # 2. 如果本地文件加载失败，使用备用数据（无交互模式）
    if not html_content:
        print("\n" + "=" * 60)
        print("无法加载本地HTML文件！")
        print("使用备用数据...")
        print("=" * 60)
        device_map = get_fallback_data()
    else:
        device_map = parse_html_content(html_content)
    
    # 保存到文件
    if device_map:
        save_to_json(device_map, output_file)
        
        # 打印统计信息
        print("\n" + "=" * 60)
        print("设备分类统计:")
        print("-" * 60)
        
        categories = {}
        for identifier in device_map.keys():
            if identifier.startswith('iPhone'):
                categories['iPhone'] = categories.get('iPhone', 0) + 1
            elif identifier.startswith('iPad'):
                categories['iPad'] = categories.get('iPad', 0) + 1
            elif identifier.startswith('iPod'):
                categories['iPod'] = categories.get('iPod', 0) + 1
            elif identifier.startswith('AppleTV'):
                categories['AppleTV'] = categories.get('AppleTV', 0) + 1
            elif identifier.startswith('Watch'):
                categories['Apple Watch'] = categories.get('Apple Watch', 0) + 1
            elif identifier.startswith('AudioAccessory'):
                categories['Apple TV Accessories'] = categories.get('Apple TV Accessories', 0) + 1
            else:
                categories['Other'] = categories.get('Other', 0) + 1
        
        for category, count in categories.items():
            print(f"{category}: {count} 个设备")
        
        print("=" * 60)
        
        # 示例：查找 iPad3,6
        if 'iPad3,6' in device_map:
            print(f"\niPad3,6 对应的设备信息:")
            print(f"  Model: {device_map['iPad3,6'].get('Model', 'Unknown')}")

if __name__ == "__main__":
    main()
