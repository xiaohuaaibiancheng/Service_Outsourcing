from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
from functools import wraps
from werkzeug.utils import secure_filename
import os
import datetime
import validators
from openai import OpenAI  # Updated OpenAI import
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from flask_cors import CORS

# Initialize OpenAI client
openai_client = OpenAI(
    api_key='sk-GRq26cv5F72b4eS7I4VnBOGzDZK2sI5PT5fRSLuStEEHxnhC',
    base_url='https://api.chatanywhere.tech'
)

# Initialize LangChain's OpenAI model
llm = ChatOpenAI(
    api_key='sk-GRq26cv5F72b4eS7I4VnBOGzDZK2sI5PT5fRSLuStEEHxnhC',  # 替换为你的 OpenAI API 密钥
    base_url='https://api.chatanywhere.tech',  # 如果需要自定义 API 地址
    model_name="gpt-4o-mini",
    temperature=0.7  # 控制生成文本的随机性
)
conversation = ConversationChain(llm=llm, verbose=True)

# Directory to store conversations
CONVERSATION_DIR = 'conversations'
if not os.path.exists(CONVERSATION_DIR):
    os.makedirs(CONVERSATION_DIR)

app = Flask(__name__)
CORS(app)
app.secret_key = '123'  # Secret key for session

# File upload directories
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEXT_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'texts')
app.config['IMAGE_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'images')
app.config['VIDEO_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'videos')

# Allowed file extensions
app.config['ALLOWED_IMAGE_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['ALLOWED_VIDEO_EXTENSIONS'] = {'mp4', 'avi', 'mov'}
app.config['ALLOWED_TEXT_EXTENSIONS'] = {'txt'}

# Create directories if they don't exist
for folder in [app.config['TEXT_FOLDER'], app.config['IMAGE_FOLDER'], app.config['VIDEO_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Fixed test account for login
        if username == 'admin' and password == '123':
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='用户名或密码错误')
    return render_template('login.html')

@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/predict', methods=['POST'])
def predict():
    if request.method == 'POST':
        news_text = request.form['news_text']
        # Example response, replace with actual detection logic
        return jsonify({
            'status': 'success',
            'message': '检测功能待实现'
        })

def allowed_file(filename, file_type):
    """Check if the file type is allowed"""
    extension = filename.rsplit('.', 1)[1].lower()
    if file_type == 'image':
        return extension in app.config['ALLOWED_IMAGE_EXTENSIONS']
    elif file_type == 'video':
        return extension in app.config['ALLOWED_VIDEO_EXTENSIONS']
    elif file_type == 'text':
        return extension in app.config['ALLOWED_TEXT_EXTENSIONS']
    return False

def generate_filename(extension):
    """Generate a filename with the current timestamp"""
    current_time = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    return f"{current_time}.{extension}"

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def handle_upload():
    success = False  # Flag to indicate if upload was successful
    error_message = None  # Store error messages

    if request.method == 'POST':
        # Get uploaded text, images, videos, and URL
        text_input = request.form.get('text_input')
        image_files = request.files.getlist('image_input')
        video_files = request.files.getlist('video_input')
        url_input = request.form.get('url_input')

        if not text_input.strip() and not any(image.filename for image in image_files) and not any(video.filename for video in video_files) and not url_input.strip():
            error_message = "请至少上传一项内容：文本、图片、视频或网址。"
            success = False
        else:
            # Save text input
            if text_input:
                text_filename = generate_filename('txt')
                text_filepath = os.path.join(app.config['TEXT_FOLDER'], text_filename)
                with open(text_filepath, 'w', encoding='utf-8') as text_file:
                    text_file.write(text_input)

            # Save image files
            for image in image_files:
                if image and allowed_file(image.filename, 'image') and image.filename:
                    image_filename = generate_filename(image.filename.rsplit('.', 1)[1].lower())
                    image_filepath = os.path.join(app.config['IMAGE_FOLDER'], image_filename)
                    image.save(image_filepath)

            # Save video files
            for video in video_files:
                if video and allowed_file(video.filename, 'video') and video.filename:
                    video_filename = generate_filename(video.filename.rsplit('.', 1)[1].lower())
                    video_filepath = os.path.join(app.config['VIDEO_FOLDER'], video_filename)
                    video.save(video_filepath)

            # Process URL input
            if url_input:
                if not validators.url(url_input):
                    error_message = "请输入有效的网址！"
                    success = False
                else:
                    # Call scraping logic here
                    from scraper import NewsScraper
                    scraper = NewsScraper(url_input)
                    scraper.scrape()
                    success = True
            else:
                success = True

    return render_template('upload.html', success=success, error_message=error_message)

@app.route('/gpt')
def gpt():
    return render_template('gpt.html')

sessions = {}

def get_session_id():
    """生成唯一的会话 ID"""
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

def save_conversation(session_id, user_input, response):
    """将会话保存到文件中"""
    if not os.path.exists(CONVERSATION_DIR):
        os.makedirs(CONVERSATION_DIR)
    
    # 文件路径
    filepath = os.path.join(CONVERSATION_DIR, f"{session_id}.txt")
    
    # 追加保存对话
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(f"User: {user_input}\n")
        f.write(f"AI: {response}\n\n")

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form['user_input']
    print(f"User input: {user_input}")
    
    # 获取会话 ID
    session_id = session.get('session_id')
    if not session_id:
        session_id = get_session_id()
        session['session_id'] = session_id  # 保存会话 ID 到 session 中

        system_prompt = """你是一个专业的虚假新闻检测AI助手。你的任务是分析用户提供的内容，判断其是否为虚假新闻，并给出详细的分析结果和原因。请按照以下步骤进行分析：

1. 内容真实性：基于事实和可信来源，判断内容是否真实。
2. 信息来源：分析内容的来源是否可靠，是否存在偏见或不可信的情况。
3. 逻辑一致性：检查内容中的逻辑是否自洽，是否存在矛盾或不合常理的地方。
4. 情感倾向：分析内容是否带有强烈的情感倾向或煽动性语言。
5. 结论与建议：给出明确的结论（真实、虚假或存疑），并解释原因。如果可能，提供相关证据或可信来源。
6. 语言简洁精炼：每句回答不超过50个词。

请确保你的回答简洁、专业且易于理解。如果内容涉及复杂话题，请尽量用通俗的语言解释。"""
        conversation.predict(input=system_prompt)  # 初始化模型上下文    
    # 使用 ConversationChain 生成响应
    response = conversation.predict(input=user_input)
    # print(f"Generated response: {response}")
    
    # 保存对话
    save_conversation(session_id, user_input, response)
    
    # 返回响应
    return Response(response, content_type='text/plain;charset=utf-8')


if __name__ == '__main__':
    app.run(debug=True)