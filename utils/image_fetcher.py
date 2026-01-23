import requests
from bs4 import BeautifulSoup
import threading
import os
import glob


class ImageFetcher:
    """图片获取器类"""

    def __init__(self):
        self.images_dir = "images/fullme"
        self._ensure_dir()
        self.active_threads = set()  # 跟踪活跃线程

    def _ensure_dir(self):
        """确保images目录存在"""
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
            print(f"创建目录: {self.images_dir}")

    def fetch_image(self, captcha_url, thread_id):
        """获取验证码图片"""
        try:
            response = requests.get(captcha_url)
            if response.status_code == 200:
                # 解析HTML内容，提取图片URL
                soup = BeautifulSoup(response.text, 'html.parser')
                img_tag = soup.find('img')
                if img_tag:
                    captcha_img_url = img_tag['src']
                    # 完整URL
                    full_img_url = f"http://fullme.pkuxkx.net/{captcha_img_url.lstrip('./')}"
                    # 下载图片放到 images 目录下
                    img_response = requests.get(full_img_url)
                    if img_response.status_code == 200:
                        filename = captcha_img_url.split('/')[-1]
                        filepath = os.path.join(self.images_dir, filename)
                        with open(filepath, 'wb') as f:
                            f.write(img_response.content)
                        # print(f"验证码图片已保存到 {filepath}")
                        return filepath
                    else:
                        print(f"下载验证码图片失败，状态码: {img_response.status_code}")
                else:
                    print("未找到验证码图片标签")
            else:
                print(f"获取验证码图片失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"获取验证码图片时出错: {e}")
        finally:
            # 任务完成后从活跃线程集合中移除
            if thread_id in self.active_threads:
                self.active_threads.remove(thread_id)
                # print(f"线程 {thread_id} 已完成任务并关闭")

        return None

    def fetch_threaded(self, captcha_url):
        """在线程中获取验证码图片，完成后自动关闭线程"""
        thread_id = f"ImgFetcher_{len(self.active_threads) + 1}"

        thread = threading.Thread(
            target=self.fetch_image,
            args=(captcha_url, thread_id),
            daemon=True,
            name=thread_id
        )

        # 添加到活跃线程集合
        self.active_threads.add(thread_id)
        # print(f"启动线程 {thread_id} 下载图片")

        thread.start()
        return thread

    def cleanup_images(self):
        """清理images/fullme目录下除了fullme*以外的所有图片"""
        # 获取目录下所有文件
        all_files = glob.glob(os.path.join(self.images_dir, "*"))

        # 筛选出不以"fullme"开头的图片文件
        files_to_delete = []
        for file_path in all_files:
            if os.path.isfile(file_path):
                filename = os.path.basename(file_path)
                # 检查是否是图片文件且不以"fullme"开头
                if (filename.lower().endswith(('.jpg')) and
                        not filename.lower().startswith('fullme')):
                    files_to_delete.append(file_path)

        # 删除文件
        deleted_count = 0
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                # print(f"已删除图片: {file_path}")
                deleted_count += 1
            except Exception as e:
                print(f"删除图片失败 {file_path}: {e}")
        # print(f"清理完成，共删除 {deleted_count} 个图片文件")
        return deleted_count


    def get_non_fullme_images(self):
        """查找images/fullme目录下除了fullme*以外的所有图片，返回带目录的文件名列表"""
        # 获取目录下所有文件
        all_files = glob.glob(os.path.join(self.images_dir, "*"))

        # 筛选出不以"fullme"开头的图片文件
        non_fullme_images = []
        for file_path in all_files:
            if os.path.isfile(file_path):
                filename = os.path.basename(file_path)
                # 检查是否是图片文件且不以"fullme"开头
                if (filename.lower().endswith(('.jpg')) and
                    not filename.lower().startswith('fullme')):
                    non_fullme_images.append(file_path)

        # 按文件名排序，确保顺序一致
        non_fullme_images.sort()

        # print(f"找到 {len(non_fullme_images)} 个非fullme图片")
        return non_fullme_images
