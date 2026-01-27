#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fullme UI窗口模块
提供简单的接口供其他模块调用，用于打开Fullme验证码窗口
"""

import sys
import warnings
import threading
import os
from PyQt5 import QtWidgets, QtCore, QtGui
from fullme_window_ui import Ui_fullme_window
from utils.image_fetcher import ImageFetcher

# 更全面的警告屏蔽设置
def suppress_qt_warnings():
    """屏蔽Qt相关的警告"""
    # 屏蔽所有PyQt相关的警告
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="PyQt5")
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="PyQt5")
    warnings.filterwarnings("ignore", category=UserWarning, module="PyQt5")
    
    # 屏蔽sip相关的废弃警告
    warnings.filterwarnings("ignore", category=DeprecationWarning, message="sipPyTypeDict.*deprecated")
    
    # 屏蔽QApplication不在主线程创建的警告
    warnings.filterwarnings("ignore", category=RuntimeWarning, message="QApplication was not created in the main.*thread")
    warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*QApplication.*main.*thread")
    
    # 屏蔽其他常见的Qt警告
    warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*QWidget.*parent.*")
    warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*QPixmap.*")
    
    # 设置环境变量屏蔽Qt警告
    os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.*=false"
    os.environ["QT_MESSAGE_PATTERN"] = ""

# 调用警告屏蔽函数
suppress_qt_warnings()

# 原有的警告屏蔽代码（保持兼容）
# 忽略sip相关的废弃警告
warnings.filterwarnings("ignore", category=DeprecationWarning, message="sipPyTypeDict.*deprecated")

# 忽略QApplication不在主线程创建的警告
warnings.filterwarnings("ignore", category=RuntimeWarning, message="QApplication was not created in the main() thread")


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
            return True

        # 在新线程中打开窗口
        self._thread = threading.Thread(
            target=self._open_window_thread,
            args=(captcha_url,),
            daemon=True
        )
        self._thread.start()
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
            self._window.show()

            # print("Fullme验证码窗口已打开")

            # 运行事件循环
            self._app.exec_()

        except Exception as e:
            # print(f"打开Fullme窗口失败: {e}")
            pass

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

    def on_show(self, event):
        """窗口显示事件，启动图片下载"""
        super().showEvent(event)

        # 启动4个下载线程（下载4张验证码图片）
        for i in range(1, 5):
            self.fetcher.fetch_threaded(self.captcha_url)
            # print(f"启动下载线程 {i}")

        # 延迟1秒后加载图片到窗口
        QtCore.QTimer.singleShot(1000, self.load_images)

    def load_images(self):
        """加载下载的图片到窗口标签"""
        try:
            # 获取下载的图片文件列表
            non_fullme_images = self.fetcher.get_non_fullme_images()

            # 检查是否有足够的图片
            if len(non_fullme_images) >= 4:
                # print(f"找到 {len(non_fullme_images)} 张图片，开始加载到窗口")

                # 更换UI中的图片路径
                for i in range(1, 5):
                    img_label = getattr(self.ui, f'label_fullme_{i}')
                    if i-1 < len(non_fullme_images):
                        pixmap = QtGui.QPixmap(non_fullme_images[i-1])
                        img_label.setPixmap(pixmap)
                        # print(f"图片 {i} 加载成功: {non_fullme_images[i-1]}")
                    else:
                        # print(f"图片 {i} 索引超出范围")
                        pass
            else:
                # print(f"图片数量不足，只找到 {len(non_fullme_images)} 张图片")
                # 如果没有下载到足够的图片，使用默认图片
                self.load_default_images()

        except Exception as e:
            # print(f"加载图片失败: {e}")
            # 出错时加载默认图片
            self.load_default_images()

    def load_default_images(self):
        """加载默认图片（如果下载失败）"""
        try:
            # 尝试加载images/fullme目录下的默认图片
            for i in range(1, 5):
                img_label = getattr(self.ui, f'label_fullme_{i}')
                default_image = f"images/fullme/fullme{i}.jpg"
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

    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.key() == QtCore.Qt.Key_F11:
            # F11键切换窗口置顶状态
            if self.windowFlags() & QtCore.Qt.WindowStaysOnTopHint:
                self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
                # print("取消窗口置顶")
            else:
                self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
                # print("设置窗口置顶")
            self.show()

        elif event.key() == QtCore.Qt.Key_Escape:
            # ESC键关闭窗口
            self.close()
            # print("窗口已关闭")


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