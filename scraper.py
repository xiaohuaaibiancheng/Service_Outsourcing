import os
import requests
from newspaper import Article
from urllib.parse import urlparse
import time
from PIL import Image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import logging
from bs4 import BeautifulSoup

class NewsScraper:
    def __init__(self, url, output_dir='output'):
        self.url = url
        self.output_dir = output_dir
        self.text_dir = os.path.join(self.output_dir, 'text')
        self.image_dir = os.path.join(self.output_dir, 'images')
        self.video_dir = os.path.join(self.output_dir, 'videos')
        self.article = None
        self.downloaded_images = set()  # 用于存储已下载图片的哈希值，避免重复下载
        self.downloaded_videos = set()  # 用于存储已下载视频的哈希值，避免重复下载

        # 创建目录
        os.makedirs(self.text_dir, exist_ok=True)
        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.video_dir, exist_ok=True)

        # 配置日志
        self._setup_logging()

    def _setup_logging(self):
        """设置日志记录"""
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def scrape(self):
        """启动爬取流程"""
        logging.info("开始下载并解析文章内容...")
        self._download_article()

        if self.article:
            logging.info("文章解析完成，开始保存文本...")
            self._save_text()
            logging.info("开始下载图片...")
            self._download_images()
            logging.info("开始下载视频...")
            self._download_videos()

    def _download_article(self):
        """下载并解析文章内容"""
        try:
            article = Article(self.url)
            article.download()
            article.parse()
            self.article = article
            logging.info(f"文章内容已解析: {self.article.title}")
        except Exception as e:
            logging.error(f"下载和解析文章时出错: {e}")

    def _save_text(self):
        """保存文章文本内容"""
        try:
            article_title = self.article.title
            article_text = self.article.text

            # 生成文件名
            article_filename = os.path.join(self.text_dir, f"{self._sanitize_filename(article_title)}.txt")

            # 保存文本内容
            with open(article_filename, 'w', encoding='utf-8') as text_file:
                text_file.write(article_title + '\n\n')
                text_file.write(article_text)
            logging.info(f"文本已保存到: {article_filename}")
        except Exception as e:
            logging.error(f"保存文本时出错: {e}")

    def _download_images(self):
        """并发下载并保存文章中的所有图片"""
        image_urls = list(set(self.article.images))  # 去重
        image_count = 0

        with ThreadPoolExecutor(max_workers=10) as executor:  # 根据需求增大最大线程数
            future_to_url = {executor.submit(self._download_image, img_url): img_url for img_url in image_urls}

            for future in as_completed(future_to_url):
                img_url = future_to_url[future]
                try:
                    img_filename = future.result()
                    if img_filename:
                        image_count += 1
                except Exception as e:
                    logging.error(f"无法下载图片: {img_url}, 错误: {e}")

        if image_count == 0:
            logging.info("未找到任何图片。")

    def _download_videos(self):
        """并发下载并保存文章中的所有视频"""
        video_urls = self._extract_video_urls()
        video_count = 0

        with ThreadPoolExecutor(max_workers=10) as executor:  # 根据需求增大最大线程数
            future_to_url = {executor.submit(self._download_video, video_url): video_url for video_url in video_urls}

            for future in as_completed(future_to_url):
                video_url = future_to_url[future]
                try:
                    video_filename = future.result()
                    if video_filename:
                        video_count += 1
                except Exception as e:
                    logging.error(f"无法下载视频: {video_url}, 错误: {e}")

        if video_count == 0:
            logging.info("未找到任何视频。")

    def _extract_video_urls(self):
        """从文章中提取视频链接"""
        video_urls = []
        try:
            soup = BeautifulSoup(self.article.html, 'html.parser')
            # 查找 <video> 标签
            for video_tag in soup.find_all('video'):
                src = video_tag.get('src')
                if src:
                    video_urls.append(self._resolve_image_url(src))
            # 查找 <iframe> 标签（通常用于嵌入外部视频）
            for iframe_tag in soup.find_all('iframe'):
                src = iframe_tag.get('src')
                if src and 'youtube' in src:  # 示例：处理YouTube视频
                    video_urls.append(src)
        except Exception as e:
            logging.error(f"提取视频链接时出错: {e}")
        return video_urls

    def _download_video(self, video_url):
        """下载并保存单个视频"""
        try:
            # 处理相对路径视频URL
            video_url = self._resolve_image_url(video_url)

            # 下载视频
            video_data = self._get_video_data(video_url)
            if video_data is None:
                return None

            # 计算视频的哈希值，避免重复下载
            video_hash = hashlib.md5(video_data).hexdigest()
            if video_hash in self.downloaded_videos:
                logging.info(f"跳过重复视频: {video_url}")
                return None
            self.downloaded_videos.add(video_hash)

            # 创建视频的文件名
            video_filename = self._save_video(video_data)

            return video_filename

        except Exception as e:
            logging.error(f"无法下载视频: {video_url}, 错误: {e}")
            return None

    def _get_video_data(self, video_url):
        """获取视频数据"""
        try:
            video_data = requests.get(video_url).content
            return video_data
        except Exception as e:
            logging.error(f"下载视频失败: {video_url}, 错误: {e}")
            return None

    def _save_video(self, video_data):
        """保存视频到本地"""
        try:
            video_filename = os.path.join(self.video_dir, f'video_{len(self.downloaded_videos)}.mp4')

            with open(video_filename, 'wb') as video_file:
                video_file.write(video_data)
            return video_filename
        except Exception as e:
            logging.error(f"保存视频失败: {e}")
            return None

    def _download_image(self, img_url):
        """下载并保存单个图片"""
        try:
            # 处理相对路径图片URL
            img_url = self._resolve_image_url(img_url)

            # 过滤掉包含特定关键词的图片URL
            if self._is_unwanted_image(img_url):
                logging.info(f"跳过无关图片: {img_url}")
                return None

            # 下载图片
            img_data = self._get_image_data(img_url)
            if img_data is None:
                return None

            # 检查图片尺寸
            if not self._is_large_enough(img_data):
                logging.info(f"跳过小尺寸图片: {img_url}")
                return None

            # 计算图片的哈希值，避免重复下载
            img_hash = hashlib.md5(img_data).hexdigest()
            if img_hash in self.downloaded_images:
                logging.info(f"跳过重复图片: {img_url}")
                return None
            self.downloaded_images.add(img_hash)

            # 创建图片的文件名
            img_filename = self._save_image(img_data)

            return img_filename

        except Exception as e:
            logging.error(f"无法下载图片: {img_url}, 错误: {e}")
            return None

    def _get_image_data(self, img_url):
        """获取图片数据"""
        try:
            img_data = requests.get(img_url).content
            return img_data
        except Exception as e:
            logging.error(f"下载图片失败: {img_url}, 错误: {e}")
            return None

    def _save_image(self, img_data):
        """保存图片到本地"""
        try:
            img_format = self._get_image_format(img_data)
            img_filename = os.path.join(self.image_dir, f'image_{len(self.downloaded_images)}.{img_format}')

            with open(img_filename, 'wb') as img_file:
                img_file.write(img_data)
            return img_filename
        except Exception as e:
            logging.error(f"保存图片失败: {e}")
            return None

    def _sanitize_filename(self, filename):
        """清理文件名中的非法字符"""
        return "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in filename)

    def _resolve_image_url(self, img_url):
        """处理相对路径的图片URL"""
        if not img_url.startswith('http'):
            base_url_parsed = urlparse(self.url)
            img_url = f"{base_url_parsed.scheme}://{base_url_parsed.netloc}{img_url}"
        return img_url

    def _is_unwanted_image(self, img_url):
        """判断图片是否为无关图标"""
        unwanted_keywords = ['logo', 'icon', 'ad', 'banner', 'sponsor']
        return any(keyword in img_url.lower() for keyword in unwanted_keywords)

    def _is_large_enough(self, img_data):
        """判断图片尺寸是否足够大"""
        try:
            img = Image.open(BytesIO(img_data))
            width, height = img.size
            return width >= 100 and height >= 100
        except Exception as e:
            logging.warning(f"无法检查图片尺寸: {e}")
            return False

    def _get_image_format(self, img_data):
        """获取图片的格式"""
        try:
            img = Image.open(BytesIO(img_data))
            return img.format.lower() if img.format else 'jpg'
        except Exception as e:
            logging.warning(f"无法获取图片格式: {e}")
            return 'jpg'


# 外部调用示例
def main():
    url = 'https://www.chinaqw.com/qwxs/2025/01-23/389335.shtml'  # 替换为要爬取的网页URL
    scraper = NewsScraper(url)
    scraper.scrape()  # 开始爬取

if __name__ == '__main__':
    main()