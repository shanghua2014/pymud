import sys
import os
from PyQt5 import QtWidgets
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTimer

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入pymud_screen_ui模块
from pymud_screen_ui import Ui_MainWindow

class PyMudScreenUI(QtWidgets.QMainWindow):
    """PyMUD屏幕UI主类"""
    
    def __init__(self):
        super().__init__()
        
        # 设置UI界面
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # 窗口高度状态
        self.normal_height = 420  # 正常高度
        self.max_height = 860  # 最大高度（比正常高度大）
        self.is_max_height = False  # 初始状态为正常高度
        
        # 立即移除窗口的固定尺寸限制，允许调整高度
        self.setMinimumSize(self.normal_height, self.normal_height)  # 最小宽度420，最小高度400
        self.setMaximumSize(self.normal_height, self.max_height)  # 移除最大高度限制，使用Qt的默认最大值
        
        # 设置窗口标题
        self.setWindowTitle("PyMUD 状态监控")
        
        # 倒计时相关初始化（移到init_ui_data之前）
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_seconds = 0  # 当前倒计时秒数
        self.countdown_total = 10  # 总倒计时时间（180秒）
        
        # 初始化UI数据
        self.init_ui_data()
        
        # 为pushButton_kook添加点击事件
        self.ui.pushButton_kook.clicked.connect(self.windowMaxHeight)
        
        # 设置窗口初始大小
        self.resize(420, self.normal_height)
    
    def windowMaxHeight(self):
        """将窗口高度设置为最大值"""
        try:
            if not self.is_max_height:
                # 保存当前高度作为正常高度
                self.normal_height = self.height()
                
                # 设置窗口为最大高度
                self.resize(self.width(), self.max_height)
                self.is_max_height = True

                # 更换label_fullme_1的图片地址
                self.ui.label_fullme_1.setPixmap(QPixmap("resource/fullme\\b2evo_captcha_9FCBF2C98A283873CCFF663CB6AE5ABB.jpg"))
                
                # 启动180秒倒计时
                self.start_countdown()

                print(f"窗口高度已设置为最大值: {self.max_height}px")
                return True
            else:
                print("窗口已经是最大高度")
                return False
                
        except Exception as e:
            print(f"设置窗口最大高度时出错: {e}")
            return False
    
    def start_countdown(self):
        """启动倒计时"""
        self.countdown_seconds = self.countdown_total
        self.update_countdown()
        self.countdown_timer.start(1000)  # 每秒触发一次
    
    def update_countdown(self):
        """更新倒计时显示"""
        if self.countdown_seconds > 0:
            self.ui.label_fullme_cd.setText(str(self.countdown_seconds))
            self.countdown_seconds -= 1
        else:
            self.countdown_timer.stop()
            self.ui.label_fullme_cd.setText("0")
    
    def windowNormal(self):
        """将窗口高度恢复为正常值"""
        try:
            if self.is_max_height:
                # 停止倒计时
                self.countdown_timer.stop()
                self.ui.label_fullme_cd.setText("0")
                
                # 恢复窗口为正常高度
                self.resize(self.width(), self.normal_height)
                self.is_max_height = False
                
                print(f"窗口高度已恢复为正常值: {self.normal_height}px")
                return True
            else:
                print("窗口已经是正常高度")
                return False
                
        except Exception as e:
            print(f"恢复窗口正常高度时出错: {e}")
            return False
    
    def toggleWindowHeight(self):
        """切换窗口高度状态"""
        if self.is_max_height:
            return self.windowNormal()
        else:
            return self.windowMaxHeight()
    
    def init_ui_data(self):
        """初始化UI数据"""
        # 设置默认值
        self.ui.label_pot.setText("0")
        self.ui.label_exp.setText("0")
        self.ui.label_name.setText("未连接")
        self.ui.label_family.setText("未知")
        self.ui.label_shifu.setText("未知")
        self.ui.label_loyalty.setText("0")
        self.ui.label_morality.setText("0")
        self.ui.label_balance.setText("0")
        
        # 设置进度条默认值
        self.ui.progressBarQixue.setValue(50)
        self.ui.progressBarNeili.setValue(30)
        self.ui.progressBarJing.setValue(70)
        self.ui.progressBarJingli.setValue(60)
        self.ui.progressBarFood.setValue(80)
        self.ui.progressBarWater.setValue(40)
        
        # 初始化倒计时显示
        self.ui.label_fullme_cd.setText(str(self.countdown_total))

def main():
    """主函数：启动UI应用程序"""
    print("启动PyMUD屏幕UI...")
    
    try:
        # 创建QApplication实例
        app = QtWidgets.QApplication(sys.argv)
        
        # 创建主窗口
        window = PyMudScreenUI()
        
        # 显示窗口
        window.show()
        
        print("UI界面启动成功！")
        
        # 测试最大高度
        window.windowMaxHeight()
        print("2. 当前窗口高度:", window.height())
        
        # 运行应用程序
        sys.exit(app.exec_())

    except ImportError as e:
        print(f"导入模块失败: {e}")
        print("请确保已安装PyQt5: pip install PyQt5")
    except Exception as e:
        print(f"启动UI时出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()