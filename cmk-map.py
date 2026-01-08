import os
import requests
from PIL import Image
import sys
import re

# ================= 配置区域 =================
WORK_DIR = os.path.join(os.getcwd(), "downloaded_tiles") # 图片下载存放的文件夹
# ===========================================

def print_instructions():
    """
    打印使用说明 (还原简洁版)
    """
    print("="*80)
    print("获取cm高清大地图专用脚本")
    print("首先开发者模式找到小块图的链接，类似:")
    print("https://webcatpublicj07.blob.core.windows.net/c107map-tiles/200/Day1-w12_w/0-1.png?sv=2016-05-31&sr=c&sig=4D9lXSwXqJyhteXQB%2BGMIrVHmBi7%2F85N7OZBWtu48ag%3D&se=2026-01-07T09%3A30%3A59Z&sp=r")
    print("（c107 Day1 w12 200倍大地图左上第一张）")
    print("后输入想要下载的范围如 6-26（获取7列27行为止的小图），全下载就填最大数字")
    print("="*80)
    print("")

def parse_url(full_url):
    """
    从完整链接中提取 base_url 和 sas_token
    """
    # 正则匹配类似于 0-1.png 或 12-5.png 的部分
    pattern = r"(.*?)(\d+-\d+\.png)(.*)"
    match = re.match(pattern, full_url)
    
    if match:
        base_url = match.group(1)
        sas_token = match.group(3)
        return base_url, sas_token
    else:
        print("❌ 错误: 无法解析链接格式。请确保链接包含类似于 '0-0.png' 的文件名。")
        return None, None

def download_images(base_url, sas_token, max_x, max_y):
    """
    步骤 1: 下载所有切片图片
    """
    # 总数量
    total_cols = max_x + 1
    total_rows = max_y + 1
    
    print(f"\n--- 步骤 1: 开始下载任务 ---")
    print(f"目标目录: {WORK_DIR}")
    print(f"下载范围: {total_cols} 列 x {total_rows} 行 (共 {total_cols * total_rows} 张)")
    
    os.makedirs(WORK_DIR, exist_ok=True)

    success_count = 0
    skip_count = 0
    fail_count = 0

    # 遍历顺序: 先列后行
    for x in range(total_cols):
        for y in range(total_rows):
            # 文件名格式: Col-Row.png (X-Y.png)
            file_name = f"{x}-{y}.png"
            save_path = os.path.join(WORK_DIR, file_name)
            
            if os.path.exists(save_path):
                skip_count += 1
                continue

            file_url = f"{base_url}{file_name}{sas_token}"
            
            try:
                # 使用 \r 覆盖当前行，制作简单的进度显示
                print(f"[下载中] {file_name} ...", end="\r")
                response = requests.get(file_url, stream=True, timeout=10)
                if response.status_code == 200:
                    with open(save_path, "wb") as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    success_count += 1
                else:
                    if response.status_code != 404:
                        print(f"\n[下载失败] {file_name} 状态码: {response.status_code}")
                    fail_count += 1
            except Exception as e:
                print(f"\n[下载错误] {file_name}: {e}")
                fail_count += 1
    
    # 清除最后一行进度条，换行
    print(f"\n--- 下载完成: 新下载 {success_count}, 跳过 {skip_count}, 失败/缺失 {fail_count} ---")

def stitch_images(max_x, max_y, output_filename):
    """
    步骤 2: 将下载的切片拼接成大图
    """
    print(f"\n--- 步骤 2: 开始拼接任务 ---")
    
    # 1. 寻找一张存在的图片来获取尺寸
    first_img_path = None
    total_cols = max_x + 1
    total_rows = max_y + 1
    
    for x in range(total_cols):
        for y in range(total_rows):
            p = os.path.join(WORK_DIR, f"{x}-{y}.png")
            if os.path.exists(p):
                first_img_path = p
                break
        if first_img_path: break
    
    if not first_img_path:
        print("❌ 错误: 目录下没有找到任何图片，无法拼接。")
        return

    first_image = Image.open(first_img_path)
    tile_width, tile_height = first_image.size
    
    # 2. 创建空白大画布
    canvas_width = total_cols * tile_width
    canvas_height = total_rows * tile_height
    
    print(f"单张尺寸: {tile_width}x{tile_height} -> 目标大图: {canvas_width}x{canvas_height}")
    
    result_image = Image.new('RGB', (canvas_width, canvas_height))

    # 3. 遍历拼接
    count = 0
    print("正在拼接...", end=" ")
    
    for x in range(total_cols):
        # 简单的进度展示，每完成一列打印一个点
        if x % 5 == 0:
            print(".", end="", flush=True)
            
        for y in range(total_rows):
            file_name = f"{x}-{y}.png"
            file_path = os.path.join(WORK_DIR, file_name)
            
            if os.path.exists(file_path):
                try:
                    img = Image.open(file_path)
                    pos_x = x * tile_width
                    pos_y = y * tile_height
                    result_image.paste(img, (pos_x, pos_y))
                    count += 1
                except Exception as e:
                    print(f"\n读取图片出错 {file_name}: {e}")

    # 4. 保存
    print("\n保存文件中 (请稍候)...")
    if not output_filename.endswith('.png'):
        output_filename += '.png'
        
    save_full_path = os.path.join(os.getcwd(), output_filename)
    result_image.save(save_full_path)
    print(f"✅ 成功! 共拼接 {count} 张切片")
    print(f"📁 已保存: {save_full_path}")

def main():
    # 1. 打印说明
    print_instructions()

    # 2. 获取 URL
    raw_url = input("1. 请输入链接: ").strip()
    if not raw_url:
        print("未输入链接，退出。")
        return

    base_url, sas_token = parse_url(raw_url)
    if not base_url: return

    # 3. 获取范围
    range_str = input("2. 请输入下载范围 (例如 6-26): ").strip()
    try:
        parts = re.split(r'[^\d]+', range_str)
        max_col = int(parts[0]) # X
        max_row = int(parts[1]) # Y
    except:
        print("❌ 格式错误！请输入类似于 '6-26' 的格式。")
        return

    # 4. 获取文件名
    out_name = input("3. 输出文件名 (默认 map_result): ").strip()
    if not out_name: out_name = "map_result.png"

    # 5. 执行
    download_images(base_url, sas_token, max_col, max_row)
    stitch_images(max_col, max_row, out_name)

if __name__ == "__main__":
    try:
        import requests
        from PIL import Image
    except ImportError:
        print("缺少库，请运行: pip install requests pillow")
        sys.exit(1)

    main()