#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fullme UI窗口模块
提供简单的接口供其他模块调用，用于打开Fullme验证码窗口
"""

import sys
import threading
from PyQt5 import QtWidgets, QtCore, QtGui
from fullme_window_ui import Ui_fullme_window
from utils.image_fetcher import ImageFetcher


class FullmeWindowManager:
    """Fullme窗口管理器类，提供窗口管理功能"""

    _instance = None
    _window = None
    _app = None

    def __new__(cls):
        """单例模式，确保只有一个窗口管理器实例"""
        if cls._instance is None:
            cls._instance = super(FullmeWindowManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._window = None
            self._app = None
            self._thread = None

    def open_window(self, captcha_url="http://fullme.pkuxkx.net/robot"):
        """
        打开Fullme验证码窗口

        Args:
            captcha_url: 验证码URL，默认为PKUXKX的验证码地址

        Returns:
            bool: 是否成功打开窗口
        """
        if self._window is not None and self._window.isVisible():
            # 窗口已经打开，将其置顶
            self._window.activateWindow()
            self._window.raise_()
            
            # 延迟0.5秒后取消置顶
            QtCore.QTimer.singleShot(500, self._cancel_window_topmost)
            
            return True

        # 在新线程中打开窗口
        self._thread = threading.Thread(
            target=self._open_window_thread,
            args=(captcha_url,),
            daemon=True
        )
        self._thread.start()
        
        # 延迟0.5秒后取消置顶（等待窗口创建完成）
        QtCore.QTimer.singleShot(500, self._cancel_window_topmost)
        
        return True

    def _open_window_thread(self, captcha_url):
        """在新线程中打开窗口的内部方法"""
        try:
            # 创建QApplication实例（每个线程需要独立的QApplication）
            self._app = QtWidgets.QApplication.instance()
            if self._app is None:
                self._app = QtWidgets.QApplication(sys.argv)

            # 创建窗口
            self._window = FullmeWindow(captcha_url)
            # 连接窗口关闭信号到线程结束处理
            self._window.destroyed.connect(self._on_window_destroyed)
            self._window.show()

            # print("Fullme验证码窗口已打开")

            # 运行事件循环
            self._app.exec_()

        except Exception as e:
            # print(f"打开Fullme窗口失败: {e}")
            pass
    
    def _on_window_destroyed(self):
        """窗口销毁时的回调函数，清理资源并结束线程"""
        # 清理窗口引用
        self._window = None
        # 退出应用程序事件循环
        if self._app:
            self._app.quit()
        # 清理线程引用
        self._thread = None

    def _cancel_window_topmost(self):
        """取消窗口置顶状态"""
        if self._window is not None and self._window.isVisible():
            # 取消窗口置顶标志
            self._window.setWindowFlags(self._window.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
            self._window.show()
            # print("窗口已取消置顶")

    def close_window(self):
        """关闭Fullme窗口

        Returns:
            bool: 是否成功关闭窗口
        """
        if self._window is not None:
            # 在关闭窗口前获取fetcher对象以便清理图片
            fetcher = self._window.fetcher if hasattr(self._window, 'fetcher') else None

            self._window.close()
            self._window = None
            # print("Fullme验证码窗口已关闭")

            # 清理下载的图片文件
            if fetcher:
                deleted_count = fetcher.cleanup_images()
                # print(f"清理完成，共删除 {deleted_count} 个临时图片文件")
            
            # 退出应用程序事件循环
            if self._app:
                self._app.quit()
            # 清理线程引用
            self._thread = None

            return True
        return False

    def is_window_open(self):
        """检查窗口是否打开

        Returns:
            bool: 窗口是否打开
        """
        return self._window is not None and self._window.isVisible()

    def set_captcha_url(self, captcha_url):
        """设置验证码URL（如果窗口已打开，需要重新打开窗口生效）

        Args:
            captcha_url: 新的验证码URL

        Returns:
            bool: 是否成功设置
        """
        if self.is_window_open():
            self.close_window()
        # URL将在下次打开窗口时使用
        return True


class FullmeWindow(QtWidgets.QWidget):
    """Fullme窗口类，实现图片下载和显示功能"""

    def __init__(self, captcha_url):
        super().__init__()
        self.ui = Ui_fullme_window()
        self.ui.setupUi(self)
        self.setWindowTitle("Fullme验证码窗口")
        self.captcha_url = captcha_url

        # 创建图片获取器实例
        self.fetcher = ImageFetcher()

        # 设置窗口置顶
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

        # 窗口显示后启动下载线程
        self.showEvent = self.on_show
        
        # 设置窗口关闭时清理资源
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    
    def closeEvent(self, event):
        """窗口关闭事件，清理资源"""
        # 清理图片获取器资源
        if hasattr(self, 'fetcher') and self.fetcher:
            self.fetcher.cleanup_images()
        event.accept()

    def on_show(self, event):
        """窗口显示事件，启动图片下载并模拟键盘事件"""
        super().showEvent(event)

        # 启动4个下载线程（下载4张验证码图片）
        for i in range(1, 5):
            self.fetcher.fetch_threaded(self.captcha_url)
            # print(f"启动下载线程 {i}")

        # 延迟1秒后加载图片到窗口
        QtCore.QTimer.singleShot(1000, self.load_images)
        
        # 延迟0秒后模拟按下Ctrl+L组合键
        QtCore.QTimer.singleShot(1000, self.simulate_ctrl_l)
    
    def simulate_ctrl_l(self):
        """
        模拟按下Ctrl+L组合键
        
        功能说明：
        1. 使用pyautogui模拟键盘事件
        2. 发送Ctrl键按下事件
        3. 发送L键按下事件
        4. 发送L键释放事件
        5. 发送Ctrl键释放事件
        """
        try:
            # 导入pyautogui模块
            import pyautogui
            
            # 模拟Ctrl+L组合键
            pyautogui.keyDown('ctrl')  # 按下Ctrl键
            pyautogui.press('l')       # 按下并释放L键
            pyautogui.keyUp('ctrl')    # 释放Ctrl键
            
            # print("已使用pyautogui模拟按下Ctrl+L组合键")
            
        except Exception as e:
            # 回退到原来的PyQt5实现
            self.session.error(f"失败：pyautogui模拟按下Ctrl+L组合键")
            pass

    def load_images(self):
        """
        加载下载的图片到窗口标签
        
        功能说明：
        1. 获取图片获取器下载的非Fullme图片列表
        2. 检查图片数量是否足够（至少4张）
        3. 如果图片足够，将图片加载到对应的UI标签中
        4. 如果图片不足或加载失败，使用默认图片作为备用
        5. 支持错误处理，确保程序稳定性
        """
        try:
            # 获取下载的图片文件列表
            non_fullme_images = self.fetcher.get_non_fullme_images()

            # 检查是否有足够的图片（需要4张图片对应4个标签）
            if len(non_fullme_images) >= 4:
                # print(f"找到 {len(non_fullme_images)} 张图片，开始加载到窗口")

                # 遍历4个图片标签，将下载的图片设置到对应的标签中
                for i in range(1, 5):
                    # 获取对应的图片标签控件
                    img_label = getattr(self.ui, f'label_fullme_{i}')
                    
                    # 检查索引是否在有效范围内
                    if i-1 < len(non_fullme_images):
                        # 创建QPixmap对象并设置到标签中
                        pixmap = QtGui.QPixmap(non_fullme_images[i-1])
                        img_label.setPixmap(pixmap)
                        # print(f"图片 {i} 加载成功: {non_fullme_images[i-1]}")
                    else:
                        # 索引超出范围，跳过此标签
                        # print(f"图片 {i} 索引超出范围")
                        pass
            else:
                # 图片数量不足，使用默认图片作为备用方案
                # print(f"图片数量不足，只找到 {len(non_fullme_images)} 张图片")
                self.load_default_images()

        except Exception as e:
            # 捕获所有异常，确保程序不会因图片加载失败而崩溃
            # print(f"加载图片失败: {e}")
            # 出错时加载默认图片作为容错处理
            self.load_default_images()

    def load_default_images(self):
        """加载默认图片（如果下载失败）"""
        try:
            # 尝试加载images/fullme目录下的默认图片
            for i in range(1, 5):
                img_label = getattr(self.ui, f'label_fullme_{i}')
                default_image = f"resource/fullme/fullme{i}.jpg"
                try:
                    pixmap = QtGui.QPixmap(default_image)
                    img_label.setPixmap(pixmap)
                    # print(f"加载默认图片: {default_image}")
                except:
                    # print(f"默认图片 {default_image} 加载失败")
                    pass
        except Exception as e:
            # print(f"加载默认图片失败: {e}")
            pass


# 创建全局实例
_window_manager = FullmeWindowManager()


def open_fullme_window(captcha_url="http://fullme.pkuxkx.net/robot"):
    """
    打开Fullme验证码窗口（全局函数）

    Args:
        captcha_url: 验证码URL，默认为PKUXKX的验证码地址

    Returns:
        bool: 是否成功打开窗口
    """
    return _window_manager.open_window(captcha_url)


def close_fullme_window():
    """
    关闭Fullme验证码窗口（全局函数）

    Returns:
        bool: 是否成功关闭窗口
    """
    return _window_manager.close_window()


def is_fullme_window_open():
    """
    检查Fullme窗口是否打开（全局函数）

    Returns:
        bool: 窗口是否打开
    """
    return _window_manager.is_window_open()


def set_fullme_captcha_url(captcha_url):
    """
    设置验证码URL（全局函数）

    Args:
        captcha_url: 新的验证码URL

    Returns:
        bool: 是否成功设置
    """
    return _window_manager.set_captcha_url(captcha_url)


# 提供简单的别名函数
open_window = open_fullme_window
close_window = close_fullme_window
is_open = is_fullme_window_open
set_url = set_fullme_captcha_url


def main():
    """主函数（保持向后兼容）"""
    app = QtWidgets.QApplication(sys.argv)

    # 创建Fullme窗口
    window = FullmeWindow("http://fullme.pkuxkx.net/robot")
    window.show()

    # print("窗口已打开，开始下载验证码图片...")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()