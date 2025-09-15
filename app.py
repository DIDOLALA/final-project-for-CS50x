from flask import Flask, redirect, render_template, request, url_for, jsonify, session, flash
from database import db, User, Preference, Limitation, Itinerary
import json, requests, os
from dotenv import load_dotenv
from functools import wraps
import time, logging
from translations import TRANS


logging.basicConfig(level=logging.INFO)   

# 加载 .env 文件
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


def gettext(key, lang=None):
    """lang 为 None 则自动取 session['language']"""
    lang = lang or session.get('language', 'en')
    return TRANS.get(key, {}).get(lang, key)          # 找不到 key 直接回显 key
    print("【DEBUG】gettext used lang:", lang, "for key:", key)

# 配置 application
def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")  # 添加密钥用于session

    db.init_app(app)

    app.jinja_env.globals['_'] = gettext                # 模板里直接用 {{ _('btn_next') }}

    def login_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'uid' not in session:                      # 只要 session 没有 uid 就跳
                # 把当前想访问的 endpoint 和参数存到 next，登录后自动回来
                return redirect(url_for('login', next=f.__name__, **request.view_args))
            return f(*args, **kwargs)
        return decorated

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            u = request.form.get("username").strip()
            p = request.form.get("password")
            if not u or not p:
                flash("用户名和密码必填")
                return redirect(url_for("register"))
            if User.query.filter_by(username=u).first():
                flash("用户名已存在")
                return redirect(url_for("register"))
            new_user = User(username=u, name=u)  # name 默认用用户名
            new_user.set_password(p)
            db.session.add(new_user)
            db.session.commit()
            flash(gettext("reg_success"))
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            u = request.form.get("username").strip()
            p = request.form.get("password")
            user = User.query.filter_by(username=u).first()
            if user and user.check_password(p):
                session['uid'] = user.id
                session['uname'] = user.username
                session.pop('played_once', None)
                # 如果存在 next 参数则跳转
                next_endpoint = request.args.get("next")
                if next_endpoint:
                    return redirect(url_for(next_endpoint, **request.args.to_dict()))
                if session.get('after_login') == 'replay':
                    uid = session.pop('replay_uid', None)
                    session.pop('after_login', None)
                    if uid:
                        return redirect(url_for('preferences', user_id=uid))
                return redirect(url_for("index"))
            flash("用户名或密码错误")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.pop("uid", None)
        session.pop("uname", None)
        return redirect(url_for("index"))
    
    
    # 首页
    @app.route("/", methods=["GET", "POST"])
    def index():
        # 未登录且已玩过一轮 → 直接去登录
        if not session.get('uid') and session.get('played_once'):
            flash("您已完成一次测试，如需继续，请先登录")
            return redirect(url_for('login'))
        
        if request.method == "POST":
            name = request.form.get("name")
            language = request.form.get("language")
            if not name or language not in ("en", "zh"):
                return redirect("/")
            
            # 存储到session中，稍后在information页面创建用户时使用
            session['temp_name'] = name
            session['language'] = language 
            session.permanent = True 
            print("【DEBUG】language saved in session:", session['language'])
            
            return redirect(url_for("information"))
        return render_template("index.html")

    # 信息页
    @app.route("/information", methods=["GET", "POST"])
    def information():
        if request.method == "POST":
            user = User(
                name=session.get('temp_name', request.form.get("name")),
                gender=request.form.get("gender"),
                nationality=request.form.get("nationality"),
                language=session.get('language', 'en'),  
                age=request.form.get("age"),
                profession=request.form.get("profession"),
            )
            db.session.add(user)
            db.session.commit()         
            return redirect(url_for("preferences", user_id=user.id))
        return render_template("information.html", need_confirm=session.get('uid') is not None)

    # 偏好页 - 同时处理GET和POST
    @app.route("/preferences/<int:user_id>", methods=["GET", "POST"])
    def preferences(user_id):
        user = User.query.get_or_404(user_id)
        
        if request.method == "POST":
            # 处理表单提交
            data = request.form.to_dict()
            data['user_id'] = user_id
            
            pref = Preference(user_id=user_id, payload=json.dumps(data, ensure_ascii=False))
            db.session.add(pref)
            user.has_submitted_info = True
            db.session.commit()
            
            return redirect(url_for("result", user_id=user_id))
            
        return render_template("preferences.html", user=user, user_id=user_id)

    # 偏好 API (保留用于可能的AJAX实现)
    @app.route("/api/preferences", methods=["POST"])
    def api_preferences():
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")
        if not user_id:
            return jsonify({"ok": False, "msg": "user_id is required"}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({"ok": False, "msg": "User not found"}), 404

        pref = Preference(user_id=user_id, payload=json.dumps(data, ensure_ascii=False))
        db.session.add(pref)
        user.has_submitted_info = True
        db.session.commit()

        return jsonify({"ok": True, "msg": "Preferences saved", "next": url_for("result", user_id=user_id)})

    # 结果页 
    @app.route("/result/<int:user_id>")
    def result(user_id):
        user = User.query.get_or_404(user_id)
        pref = Preference.query.filter_by(user_id=user_id).order_by(Preference.id.desc()).first()

        if not pref:
            return "No preferences found for this user.", 404

        # 获取用户语言偏好
        user_language = user.language or session.get('language', 'en')
        prompt_language = "中文" if user_language == 'zh' else "English"

        # 构造 LLM Prompt
        prompt = f"""
        You are a senior Chinese travel advisor and itinerary planner, 
        recommending a dream travel destination in China for a foreign user 
        who is planning to visit China but is not very familiar with it. 
        Based on the personal information and preferences collected below,
        recommend the destination that best matches their needs. 
        Please respond in output format based on {prompt_language} and ensure that all outputted text is in {prompt_language},
        and make sure do not show the words in parentheses of output format.

        ### User Profile
        - Name: {user.name}
        - Gender: {user.gender}
        - Nationality: {user.nationality}
        - Language: {user.language}
        - Age: {user.age}
        - Profession: {user.profession}

        ### Travel Preferences
        {pref.payload}

        if {prompt_language} == "English", output format is:
            Dream Destination (≤20 chars, down to city/county/town):
            Best Season (≤10 chars):
            Reason for Recommendation (≤100 chars, highlight individuality):
            Must-visit Recommendations:
            · Attraction (≤20 chars):
            · Experience (≤20 chars):
            · Food (≤20 chars):
            Possible Challenges & Suggestions (≤20 chars):

        else {prompt_language} == "中文, output format is:
            梦想地点 (≤20 字, 具体到市、镇、乡等):
            最佳季节 (≤10 字):
            推荐理由 (≤100 字, 突出个性):
            必游推荐:
            · 景点 (≤20 字):
            · 体验 (≤20 字):
            · 美食 (≤20 字):
            可能的挑战及建议 (≤20 字):
        """

        # 调用 DeepSeek API
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            return "API key not configured.", 500
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-reasoner",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8
        }

        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code != 200:
                return f"DeepSeek API Error: {response.text}", 500

            data = response.json()
            if "choices" not in data or not data["choices"]:
                return f"Unexpected API response: {data}", 500
            
            result_text = data["choices"][0]["message"]["content"]

            # 写进 session，给 itinerary 用
            session['result_text'] = result_text

            return render_template("result.html", user=user, result=result_text)

        except requests.exceptions.ReadTimeout:
            logging.warning("DeepSeek 响应超时")
            return render_template("result.html",
                           user=user,
                           result="AI 推荐生成超时，请稍后再试。"), 503
        except requests.exceptions.RequestException as e:
            return f"Request error: {str(e)}", 500

    
    @app.route("/limitations/<int:user_id>", methods=["GET", "POST"])
    @login_required
    def limitations(user_id):
        user = User.query.get_or_404(user_id)
        if request.method == "POST":
            # 把所有多选字段转成 JSON 字符串
            lim = Limitation(
                user_id=user_id,
                duration=request.form.get("duration"),
                pace=request.form.get("pace"),
                budget=request.form.get("budget"),
            )
            db.session.add(lim)
            db.session.commit()
            return redirect(url_for("itinerary", user_id=user_id))
        return render_template("limitations.html", user=user)


    @app.route("/itinerary/<int:user_id>")
    def itinerary(user_id):
        user = User.query.get_or_404(user_id)

        # 1. 读取梦想偏好
        pref = Preference.query.filter_by(user_id=user_id).order_by(Preference.id.desc()).first()
        # 2. 读取限制
        lim = Limitation.query.filter_by(user_id=user_id).order_by(Limitation.id.desc()).first()
        
        if not pref or not lim:
            flash("缺少偏好或限制数据，请重新填写")
            return redirect(url_for('preferences', user_id=user_id))

        result_text = session.get('result_text', '')

        # 3. 构造 prompt
        user_language = user.language or session.get('language', 'en')
        prompt_language = "中文" if user_language == 'zh' else "English"

        prompt = f"""
        You are a senior Chinese travel advisor and itinerary planner. 
        Now, strickly find the desitination in **{result_text}**, and design a feasible itinerary for it.
        considering the user’s travel duration, pace, and budget.
        Please respond in output format based on {prompt_language} and ensure that all outputted text is in {prompt_language},
        and make sure do not show the words in parentheses of output format..

        === USER PROFILE ===
        Name: {user.name}
        Gender: {user.gender}
        Nationality: {user.nationality}
        Language: {user.language}
        Age: {user.age}
        Profession: {user.profession}

        === TRAVEL PREFERENCES ===
        {pref.payload}

        === REAL-LIFE LIMITATIONS ===
        Duration: {lim.duration}
        Pace: {lim.pace}
        Budget: {lim.budget}

        if {prompt_language} == "English", output format is:
            Ideal Destination (≤10 chars):
            Best Season (≤10 chars):
            Reason for Recommendation (≤200 chars, highlight match with user’s personality and preferences):
            Must-visit Recommendations:
            · Attraction (≤20 chars):
            · Experience (≤20 chars):
            · Food (≤20 chars):
            Detailed Itinerary:
                · Day 1 (Overview, ≤15 chars):
                · Recommended Attraction (≤20 chars, with feature description):
                · Recommended Experience (≤20 chars):
                · Recommended Food (≤10 chars):
                · Recommended Accommodation (≤10 chars):
                
                · Day 2 (Overview, ≤15 chars):
                · Recommended Attraction (≤20 chars, with feature description):
                · Recommended Experience (≤20 chars):
                · Recommended Food (≤10 chars):
                · Recommended Accommodation (≤10 chars):
                ……
                · Day n (Overview, ≤15 chars):
                · Recommended Attraction (≤20 chars, with feature description):
                · Recommended Experience (≤20 chars):
                · ecommended Food (≤10 chars):
                · Recommended Accommodation (≤10 chars):
            Possible Challenges & Suggestions (≤25 chars):

        if {prompt_language} == "中文", output format is:
            梦想地点 (≤10 字):
            最佳季节 (≤10 字):
            推荐理由 (≤200 字, 突出用户个性与偏好):
            必去推荐s:
            · 景点 (≤20 字):
            · 体验 (≤20 字):
            · 美食 (≤20 字):
            详细行程:
                · 第1天 (概述, ≤15 字):
                · 推荐景点 (≤20 字, 特点介绍):
                · 推荐体验 (≤20 字):
                · 推荐美食 (≤10 字):
                · 推荐住宿 (≤10 字):
                
                · 第2天 (概述, ≤15 字):
                · 推荐景点 (≤20 字, 特点介绍):
                · 推荐体验 (≤20 字):
                · 推荐美食 (≤10 字):
                · 推荐住宿 (≤10 字):
                ……
                · 第n天 (概述, ≤15 字):
                · 推荐景点 (≤20 字, 特点介绍):
                · 推荐体验 (≤20 字):
                · 推荐美食 (≤10 字):
                · 推荐住宿 (≤10 字):
            可能的挑战与建议 (≤25 字):
        """

        # 4. 调用 DeepSeek
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            return "API key missing", 500
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
        
        try:
            r = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
            if r.status_code != 200:
                return f"LLM error: {r.text}", 500
            content = r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Request error: {e}", 500
        except requests.exceptions.ReadTimeout:
            logging.warning("DeepSeek 响应超时")
            return render_template("result.html",
                           user=user,
                           result="AI 推荐生成超时，请稍后再试。"), 503

        # 5. 落库 & 渲染
        db.session.add(Itinerary(user_id=user_id, content=content))
        db.session.commit()
        return render_template("itinerary.html", user=user, content=content) 

    
    @app.route('/replay/<int:user_id>')
    def replay(user_id):
        """统一重玩入口：已登录直达 preferences，未登录先登录"""
        if session.get('uid'):                      # 已登录
            return redirect(url_for('preferences', user_id=user_id))
        # 未登录：记下想重玩，登录后再跳
        session['after_login'] = 'replay'
        session['replay_uid'] = user_id
        return redirect(url_for('login'))
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)