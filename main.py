import threading
import time
import cv2
import keyboard
import numpy as np
import pyautogui
import pygetwindow as gw
from PIL import ImageGrab


class PVZAutoBot:
    def __init__(self):
        """
        初始化自动化机器人
        """
        # 基础参数
        self.game_window = None
        self.templates = {}

        # 防抢鼠标机制初始化
        self.original_pos = None  # 保存原始鼠标位置
        self.mouse_move_threshold = 10  # 鼠标移动中断阈值（像素）

        # 热键Debug相关
        self.flag_save_screenshot = False
        self.hotkey_thread = None

        # 加载模板
        self.load_templates()

    def start_hotkey_listener(self):
        """启动热键监听线程"""
        self.hotkey_thread = threading.Thread(target=self.hotkey_listener, daemon=True)
        self.hotkey_thread.start()

    def hotkey_listener(self):
        """热键监听线程"""
        while True:
            # 等待F10按键
            keyboard.wait('F10')
            print("检测到F10按键")
            self.flag_save_screenshot = True
            time.sleep(0.1)  # 防止重复触发

    def load_templates(self):
        """
        加载模板图片（这里需要你准备好模板图片）
        """
        # 阳光模板
        try:
            self.sun_template = cv2.imread('template/2560_1600/sun.png', cv2.IMREAD_COLOR)
            if self.sun_template is None:
                print("错误: 找不到阳光模板 (template/2560_1600/sun.png)")
        except:
            print("警告: 无法加载阳光模板")

        # 银币模板
        try:
            self.silver_coin_template = cv2.imread('template/2560_1600/silver_coin.png', cv2.IMREAD_COLOR)
            if self.silver_coin_template is None:
                print("错误: 找不到银币模板 (template/2560_1600/silver_coin.png)")
        except:
            print("警告: 无法加载银币模板")

    def find_game_window(self):
        """
        查找游戏窗口，自动处理全屏和窗口模式
        """
        print("正在查找游戏窗口...")

        try:
            # 通过标题查找窗口
            windows = gw.getWindowsWithTitle('Plants vs. Zombies')

            if windows:
                window = windows[0]
                window.activate()
                window.maximize()

                self.game_window = {
                    'left': window.left,
                    'top': window.top,
                    'width': window.width,
                    'height': window.height,
                }

                print(f"找到游戏窗口: {self.game_window}")
                return True
            else:
                print("未找到游戏窗口，请确保游戏已启动")
                return False

        except Exception as e:
            print(f"自动查找窗口失败: {e}")
            return False

    def capture_game_screen(self):
        """
        捕获游戏窗口截图
        """

        if self.game_window is None:
            # 如果没有设置窗口，截全屏
            screenshot = ImageGrab.grab()
        else:
            region = (
                self.game_window['left'],
                self.game_window['top'],
                self.game_window['left'] + self.game_window['width'],
                self.game_window['top'] + self.game_window['height']
            )
            screenshot = ImageGrab.grab(bbox=region)

        # debug保存截图用
        if self.flag_save_screenshot:
            screenshot.save(f'debug-{int(time.time())}.png')
            self.flag_save_screenshot = False
            print("保存截图")

        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    def find_template(self, template, threshold=0.7):
        """
        在游戏窗口中查找模板

        参数:
            template: 模板图像
            threshold: 匹配阈值 (0-1)

        返回:
            匹配到的中心坐标列表 [(x, y), ...]
        """
        if template is None:
            return []

        # 捕获游戏屏幕
        screenshot = self.capture_game_screen()

        # 模板匹配
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)

        # 找到匹配位置
        locations = np.where(result >= threshold)

        # 获取模板尺寸
        h, w = template.shape[:2]

        # 收集中心坐标
        centers = []
        matches = []  # 用于去重

        for pt in zip(*locations[::-1]):  # 注意: locations是(y, x)，需要反转
            center_x = pt[0] + w // 2 + self.game_window['left']
            center_y = pt[1] + h // 2 + self.game_window['top']

            # 去重：检查是否与已找到的匹配太近
            too_close = False
            for match in matches:
                distance = np.sqrt((center_x - match[0]) ** 2 + (center_y - match[1]) ** 2)
                if distance < 20:  # 如果距离小于20像素，认为是同一个
                    too_close = True
                    break

            if not too_close:
                matches.append((center_x, center_y))
                centers.append((center_x, center_y))

        return centers

    def collect(self, template):
        """
        点击所需收集的物品

        参数:
            template: 模板图像
        """
        self.original_pos = pyautogui.position()
        recently_pos = self.original_pos

        if template is None:
            print("未输入模板")
            return False

        # 查找物品中心位置
        centers = self.find_template(template, threshold=0.7)

        if not centers:
            return False
        #print("检测到收集品")

        # 点击
        for center in centers:
            # 放抢鼠标机制：检测是否人工移动鼠标
            current_pos = pyautogui.position()
            distance = abs(current_pos.x - recently_pos.x) + abs(current_pos.y - recently_pos.y)
            if distance > self.mouse_move_threshold:
                return False

            pyautogui.click(center[0], center[1])
            recently_pos = pyautogui.position()
            print("收集+1")

            time.sleep(0.05)  # 短暂延迟

        # 鼠标归位
        pyautogui.moveTo(self.original_pos.x, self.original_pos.y)

        return True

    def Run(self):
        print("先打开游戏再打开此软件")
        print("阳光菇会帮你自动收集阳光和银币！")

        self.find_game_window()
        if self.game_window is None:
            return False

        # 启动热键监听
        self.start_hotkey_listener()

        print("一切就绪")
        try:
            while True:
                self.collect(self.sun_template)
                self.collect(self.silver_coin_template)
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("停止运行")

def main():
    # 创建自动化机器人实例
    bot = PVZAutoBot()

    # 测试运行
    bot.Run()

if __name__ == "__main__":
    main()