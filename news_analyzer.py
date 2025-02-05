import nltk
from textblob import TextBlob
from datetime import datetime
from urllib.parse import urlparse
import json
import logging
from newspaper import Article

class NewsAnalyzer:
    def __init__(self):
        # 加载可信域名列表
        self.trusted_domains = {
            'xinhuanet.com',
            'people.com.cn',
            'china.com.cn',
            'cctv.com',
        }
        
        # 加载敏感词列表
        self.sensitive_words = {
            '震惊',
            '惊爆',
            '爆料',
            '内幕',
            '揭秘',
        }

    def analyze_news(self, news_data):
        """分析新闻内容"""
        try:
            if 'url' in news_data:
                return self._analyze_from_url(news_data['url'])
            elif 'text' in news_data:
                return self._analyze_from_text(news_data['text'])
            else:
                return {'error': '无效的输入数据'}
        except Exception as e:
            logging.error(f"分析新闻时出错: {e}")
            return {'error': str(e)}

    def _analyze_from_url(self, url):
        """从URL分析新闻"""
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            return self._generate_analysis_result(
                text=article.text,
                title=article.title,
                url=url,
                authors=article.authors,
                publish_date=article.publish_date
            )
        except Exception as e:
            logging.error(f"从URL分析新闻时出错: {e}")
            return {'error': f"无法分析URL: {str(e)}"}

    def _analyze_from_text(self, text):
        """直接分析文本内容"""
        return self._generate_analysis_result(
            text=text,
            title=None,
            url=None,
            authors=None,
            publish_date=None
        )

    def _generate_analysis_result(self, text, title, url, authors, publish_date):
        """生成分析结果"""
        results = {
            'credibility_analysis': {
                'source_score': self._analyze_source(url) if url else 0.5,
                'content_score': self._analyze_content(text, title),
                'emotion_score': self._analyze_emotion(text),
            },
            'metadata': {
                'title': title,
                'url': url,
                'authors': authors,
                'publish_date': str(publish_date) if publish_date else None,
                'analysis_date': datetime.now().isoformat()
            }
        }
        
        # 计算总分
        scores = results['credibility_analysis']
        total_score = (
            scores['source_score'] * 0.3 +
            scores['content_score'] * 0.4 +
            scores['emotion_score'] * 0.3
        )
        
        results['final_score'] = round(total_score, 2)
        results['credibility_level'] = self._get_credibility_level(total_score)
        
        return results

    def _analyze_source(self, url):
        """分析来源可信度"""
        if not url:
            return 0.5
            
        domain = urlparse(url).netloc
        base_domain = '.'.join(domain.split('.')[-2:])
        return 1.0 if base_domain in self.trusted_domains else 0.5

    def _analyze_content(self, text, title):
        """分析内容质量"""
        score = 1.0
        
        # 检查敏感词
        sensitive_word_count = sum(1 for word in self.sensitive_words 
                                 if word in (title or '') or word in text)
        score -= sensitive_word_count * 0.1
        
        # 检查文本长度
        if len(text) < 100:
            score -= 0.3
        elif len(text) < 500:
            score -= 0.1
            
        return max(0.0, min(1.0, score))

    def _analyze_emotion(self, text):
        """分析情感倾向"""
        blob = TextBlob(text)
        # 返回0-1之间的分数，中性情感得分高
        return 1.0 - abs(blob.sentiment.polarity)

    def _get_credibility_level(self, score):
        """根据分数确定可信度级别"""
        if score >= 0.8:
            return "高度可信"
        elif score >= 0.6:
            return "比较可信"
        elif score >= 0.4:
            return "存疑"
        else:
            return "可能为虚假新闻" 