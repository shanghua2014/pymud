import sys, ctypes, winreg,warnings

# 忽略sip相关的废弃警告
warnings.filterwarnings("ignore", category=DeprecationWarning, message="sipPyTypeDict.*deprecated")
# 忽略依赖冲突警告
warnings.filterwarnings("ignore", category=UserWarning, message=".*dependency conflicts.*")

from PyQt5.QtGui import QPixmap,QGuiApplication
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from pymud_screen_ui import Ui_MainWindow
from pymud import IConfig
import pygetwindow as gw
from PyQt5 import QtWidgets

from utils.image_fetcher import ImageFetcher

# 创建实例
fetcher = ImageFetcher()


def _safe_log(session, msg):
    """session 可能为空，统一安全日志"""
    if session:
        session.info(msg)
    else:
        print(msg)


class UIUpdater(QObject):
    """用于跨线程安全更新 UI 的信号桥"""
    status_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()


class ExternalUI(IConfig):
    """外置UI窗口类"""
    
    def __init__(self, session, status_queue=None):
        super().__init__(self.__class__.__name__)
        self.session = session
        self.status_queue = status_queue
        self.ws = session.application.get_globals("ws_client") if session else None
        self.qt_app = None
        self.main_window = None
        self.ui = None
        self.running = False
        self.updater = None  # 跨线程信号桥
        self.target_window = None
        self.target_ui_position = None
        self.last_window_position = None  # 记录上次窗口位置
        self.window_monitor_timer = None  # 窗口监控定时器
        self.bindPYMUDWindow()

    def close(self):
        """关闭窗口"""
        if self.main_window:
            self.stop_window_monitor()  # 停止窗口监控
            self.main_window.close()
            self.running = False

    def bindPYMUDWindow(self):
        """绑定PYMUD窗口"""
        windows = gw.getAllTitles()
        for title in windows:
            # 使用find方法（区分大小写）
            if title.find('PYMUD') != -1:
                try:
                    target_windows = gw.getWindowsWithTitle(title)
                    self.target_window = target_windows[0]

                    # 获取屏幕缩放比例
                    self.get_screen_scale_factor()

                    # 获取目标窗口属性，应用实际缩放比例
                    target_top = self.target_window.top
                    target_left = self.target_window.left
                    target_width = self.target_window.width

                    # 计算UI窗口位置
                    ui_left = target_left + target_width
                    ui_top = target_top

                    self.target_ui_position = ((ui_left - 10), (ui_top + 43))
                    self.last_window_position = (target_left, target_top)  # 记录初始位置
                    break

                except Exception as e:
                    _safe_log(self.session, f"绑定窗口出错: {e}")

    def setup_ui(self):
        """设置UI界面"""
        try:
            # 确保QApplication实例唯一
            self.qt_app = QtWidgets.QApplication.instance()
            if self.qt_app is None:
                self.qt_app = QtWidgets.QApplication(sys.argv)

            # 初始化主窗口
            self.main_window = QtWidgets.QMainWindow()
            self.ui = Ui_MainWindow()
            self.ui.setupUi(self.main_window)
            self.main_window.setWindowTitle("PyMUD外置窗口")

            if hasattr(self, 'target_ui_position'):
                ui_left, ui_top = self.target_ui_position
                self.main_window.setGeometry(ui_left, ui_top, 0, 0)

            # 设置进度条样式
            self.setup_progress_bars()

            # 跨线程信号桥：从其他线程发出信号，再在 GUI 线程更新 UI
            self.updater = UIUpdater()
            self.updater.status_signal.connect(self._apply_status_update)

            # 如果有跨进程/线程队列，则轮询拉取状态
            if self.status_queue:
                self.queue_timer = QTimer()
                self.queue_timer.timeout.connect(self._drain_status_queue)
                self.queue_timer.start(100)  # 100ms 拉取一次

            # 启动窗口监控定时器
            self.start_window_monitor()

            self.running = True
            return True
        except Exception as e:
            print(f"UI设置出错: {e}")
            return False

    def start_window_monitor(self):
        """启动窗口位置监控"""
        if self.window_monitor_timer is None:
            self.window_monitor_timer = QTimer()
            self.window_monitor_timer.timeout.connect(self.check_window_position)
            self.window_monitor_timer.start(500)  # 每500ms检查一次窗口位置

    def stop_window_monitor(self):
        """停止窗口位置监控"""
        if self.window_monitor_timer:
            self.window_monitor_timer.stop()
            self.window_monitor_timer = None

    def check_window_position(self):
        """检查PYMUD窗口位置是否发生变化，如果变化则跟随移动"""
        try:
            if not self.target_window or not self.main_window:
                return

            # 获取当前窗口位置
            current_left = self.target_window.left - 10
            current_top = self.target_window.top

            # 检查位置是否发生变化
            if self.last_window_position != (current_left, current_top):
                # _safe_log(self.session, f"PYMUD窗口位置变化: {self.last_window_position} -> ({current_left}, {current_top})")

                # 更新UI窗口位置
                target_width = self.target_window.width
                ui_left = current_left + target_width
                ui_top = current_top

                # 移动UI窗口
                self.main_window.move(ui_left, ui_top)

                # 更新记录的位置
                self.last_window_position = (current_left, current_top)
                self.target_ui_position = (ui_left, ui_top)

        except Exception as e:
            _safe_log(self.session, f"窗口位置监控出错: {e}")

    def update_ui_height(self, status):
        """设置外置UI窗口的高度"""
        try:
            if self.main_window:
                # 获取当前窗口的宽度
                current_width = self.main_window.width()
    
                # 根据验证状态设置不同的高度
                if status.get('fullme'):
                    # 验证通过，设置全屏高度
                    height = 860
                    
                    # 1. 启动4个下载线程（下载4张验证码图片）
                    for i in range(1, 5):
                        fetcher.fetch_threaded(status['fullme'])
                    
                    # 2. 定义图片加载函数，用于延迟执行
                    def load_images():
                        try:
                            # 获取下载的图片文件列表
                            non_fullme_images = fetcher.get_non_fullme_images()
                            
                            # 检查是否有足够的图片
                            if len(non_fullme_images) >= 4:
                                # 3. 更换UI中的图片路径
                                for i in range(1, 5):
                                    img = getattr(self.ui, f'label_fullme_{i}')
                                    img.setPixmap(QPixmap(non_fullme_images[i-1]))
                            else:
                                _safe_log(self.session, f"图片数量不足，只找到 {len(non_fullme_images)} 张图片")
                        except Exception as e:
                            _safe_log(self.session, f"加载图片失败: {e}")
                    
                    # 使用QTimer延迟1秒后执行图片加载，避免卡住UI
                    QTimer.singleShot(1000, load_images)
    
                else:
                    # 输入fullme成功，设置常规高度
                    height = 420
                    fetcher.cleanup_images()
    
                # 设置窗口高度限制：最小高度420，最大高度860
                self.main_window.setMinimumHeight(height)
                self.main_window.setMaximumHeight(height)
    
                # 使用resize方法设置窗口大小，保持当前宽度，只改变高度
                self.main_window.resize(current_width, height)
    
    
        except Exception as e:
            _safe_log(self.session, f"设置窗口高度失败: {e}")
            return False

    def post_status(self, status):
        """线程安全地请求更新 UI 状态（可从任意线程调用）"""
        if self.updater:
            self.updater.status_signal.emit(status)

    def get_screen_scale_factor(self):
        """获取屏幕缩放比例（多种方法）"""
        # 方法1: 使用Windows API获取DPI
        try:
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            hdc = user32.GetDC(0)
            dpi_x = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
            user32.ReleaseDC(0, hdc)

            scale_factor = dpi_x / 96.0
            return scale_factor
        except Exception as e:
            _safe_log(self.session, f"Windows API获取DPI失败: {e}")

        # 方法2: 使用PyQt5获取屏幕信息（需要QApplication实例）
        try:
            # 尝试获取现有的QApplication实例
            app = QtWidgets.QApplication.instance()
            if app:
                screen = QGuiApplication.primaryScreen()
                if screen:
                    logical_dpi = screen.logicalDotsPerInch()
                    scale_factor = logical_dpi / 96.0
                    return scale_factor
        except Exception as e:
            _safe_log(self.session, f"PyQt5获取DPI失败: {e}")

        # 方法3: 使用tkinter获取屏幕信息
        try:
            import tkinter as tk
            root = tk.Tk()
            dpi = root.winfo_fpixels('1i')
            root.destroy()
            scale_factor = dpi / 96.0
            return scale_factor
        except Exception as e:
            _safe_log(self.session, f"tkinter获取DPI失败: {e}")

        # 方法4: 使用注册表获取DPI设置（Windows）
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Control Panel\Desktop\WindowMetrics")
            value, _ = winreg.QueryValueEx(key, "AppliedDPI")
            winreg.CloseKey(key)
            scale_factor = value / 96.0
            return scale_factor
        except Exception as e:
            _safe_log(self.session, f"注册表获取DPI失败: {e}")

        # 方法5: 使用pygetwindow获取窗口信息来推断缩放比例
        try:
            # 获取当前屏幕上的窗口信息
            windows = gw.getAllTitles()
            if windows:
                # 尝试获取当前进程的窗口
                current_pid = gw.getActiveWindow()
                if current_pid:
                    # 使用窗口的实际位置和大小来推断缩放
                    scale_factor = 1.5  # 默认值
                    return scale_factor
        except Exception as e:
            _safe_log(self.session, f"窗口推断缩放比例失败: {e}")

        # 所有方法都失败，使用默认值
        _safe_log(self.session, "所有方法都失败，使用默认缩放比例1.0")
        return 1.0

    def setup_progress_bars(self):
        """设置所有进度条的样式"""
        progress_bar_styles = {
            'progressBarQixue': {
                'color': 'white',
                'background': 'red'
            },
            'progressBarNeili': {
                'color': 'white',
                'background': 'blue'
            },
            'progressBarFood': {
                'color': '#505050',
                'background': 'YellowGreen'
            },
            'progressBarJing': {
                'color': 'white',
                'background': 'Orchid'
            },
            'progressBarJingli': {
                'color': 'white',
                'background': '#00aaff'
            },
            'progressBarDrink': {
                'color': '#505050',
                'background': 'YellowGreen'
            }
        }

        for progress_bar_name, style in progress_bar_styles.items():
            progress_bar = getattr(self.ui, progress_bar_name, None)
            if progress_bar:
                progress_bar.setStyleSheet(f"""
                    #{progress_bar_name}{{
                        color: {style['color']};
                    }}
                    #{progress_bar_name}:chunk{{
                        background: {style['background']};
                    }}
                """)
                # 初始化进度条值为0
                progress_bar.setValue(0)

    def show(self):
        """显示窗口"""
        if self.main_window:
            self.main_window.show()

    def hide(self):
        """隐藏窗口"""
        if self.main_window:
            self.main_window.hide()

    def _apply_status_update(self, status: dict):
        """在 GUI 线程中真正更新控件"""
        try:
            if 'fullme' in status:
                self.update_ui_height(status)

            if 'qi' in status and 'max_qi' in status:
                self.update_progress('progressBarQixue', status['qi'], status['max_qi'])

            if 'neili' in status and 'max_neili' in status:
                self.update_progress('progressBarNeili', status['neili'], status['max_neili'])

            if 'food' in status:
                self.update_progress('progressBarFood', status['food'], 350)

            if 'jing' in status and 'max_jing' in status:
                self.update_progress('progressBarJing', status['jing'], status['max_jing'])

            if 'jingli' in status and 'max_jingli' in status:
                self.update_progress('progressBarJingli', status['jingli'], status['max_jingli'])

            if 'water' in status:
                self.update_progress('progressBarWater', status['water'], 350)

            if 'potential' in status:
                self.update_label('label_pot', status['potential'])

            if 'combat_exp' in status:
                self.update_label('label_exp', status['combat_exp'])

            if 'name' in status:
                self.update_label('label_name', status['name'])

            if 'family/family_name' in status:
                self.update_label('label_family', status['family/family_name'])

            if 'shifu' in status:
                self.update_label('label_shifu', status['shifu'])

            # 门忠
            if 'loyalty' in status:
                self.update_label('label_loyalty', status['loyalty'])
            # 道德
            if 'morality' in status:
                self.update_label('label_morality', status['morality'])
            # 声望
            if 'prestige' in status:
                self.update_label('label_prestige', status['prestige'])
            # 职业
            if 'career' in status:
                self.update_label('label_career', status['career'])
            # 存款
            if 'balance' in status:
                self.update_label('label_balance', status['balance'])

        except Exception as e:
            _safe_log(self.session, f"更新UI数据出错: {e}")

    def _drain_status_queue(self):
        """从队列中批量拉取状态并更新"""
        if not self.status_queue:
            return
        try:
            while not self.status_queue.empty():
                status = self.status_queue.get_nowait()
                if isinstance(status, dict) and status.get("__exit__"):
                    if self.qt_app:
                        self.qt_app.quit()
                    return
                self.post_status(status)
        except Exception as e:
            _safe_log(self.session, f"拉取UI队列出错: {e}")

    def update_progress(self, progress_bar_name, value, maximum=100):
        """更新进度条值"""
        if self.ui and hasattr(self.ui, progress_bar_name):
            progress_bar = getattr(self.ui, progress_bar_name)
            progress_bar.setValue(value)
            if maximum:
                progress_bar.setMaximum(maximum)

    def update_label(self, label_name, text):
        """更新标签文本"""
        if self.ui and hasattr(self.ui, label_name):
            label = getattr(self.ui, label_name)
            label.setText(str(text))
        else:
            _safe_log(self.session, f"标签 {label_name} 不存在")

    def run(self):
        """运行UI事件循环"""
        if self.qt_app:
            self.qt_app.exec_()


def run_external_ui_process(status_queue):
    """独立进程运行 UI：在该进程的主线程创建 QApplication，避免警告"""
    ui = ExternalUI(session=None, status_queue=status_queue)
    if ui.setup_ui():
        ui.show()
        ui.run()