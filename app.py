from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # 设置密钥，用于session

# 登录验证装饰器
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
        # 修改验证逻辑，使用固定的测试账号
        if username == 'admin' and password == '123':  # 修改为指定的账号密码
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='用户名或密码错误')
    return render_template('login.html')

@app.route('/')
@login_required
def home():
    if 'guide_read' not in session:
        show_guide = True
        session['guide_read'] = False
    else:
        show_guide = False
    return render_template('index.html', show_guide=show_guide)

@app.route('/confirm_guide', methods=['POST'])
def confirm_guide():
    session['guide_read'] = True
    return jsonify({'status': 'success'})

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
        # 这里是示例返回，后续可以替换为实际的检测逻辑
        return jsonify({
            'status': 'success',
            'message': '检测功能待实现'
        })

if __name__ == '__main__':
    app.run(debug=True)