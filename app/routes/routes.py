from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import firebase_admin
from firebase_admin import auth as fb_auth, credentials
from app.database.db import db, cursor
from app.ai.inference import predict

main = Blueprint('main', __name__)

UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ── SPLASH ────────────────────────────────────────────────────────────────────
@main.route('/')
def splash():
    return render_template('splash.html')


# ── LOGIN ─────────────────────────────────────────────────────────────────────
@main.route('/login')
def login():
    return render_template('login.html')


# ── REGISTER ──────────────────────────────────────────────────────────────────
@main.route('/register')
def register():
    return render_template('register.html')


# ── SAVE USER ─────────────────────────────────────────────────────────────────
@main.route('/save_user', methods=['POST'])
def save_user():
    fullname = request.form['fullname']
    age      = request.form['age']
    username = request.form['username']
    password = request.form['password']
    hashed_password = generate_password_hash(password)
    sql = "INSERT INTO users (fullname, age, email, password) VALUES (%s,%s,%s,%s)"
    try:
        cursor.execute(sql, (fullname, age, username, hashed_password))
        db.commit()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return redirect(url_for('main.register'))
    return redirect(url_for('main.login'))


# ── VALIDATE LOGIN ────────────────────────────────────────────────────────────
@main.route('/validate_login', methods=['POST'])
def validate_login():
    username = request.form['username']
    password = request.form['password']
    cursor.execute("SELECT * FROM users WHERE email=%s", (username,))
    user = cursor.fetchone()
    if user and check_password_hash(user[4], password):
        session['user']    = user[1]
        session['user_id'] = user[0]
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))


# ── GOOGLE LOGIN (GET — redirige desde Firebase JS) ───────────────────────────
@main.route('/google_login')
def google_login_redirect():
    email = request.args.get('email')
    name  = request.args.get('name')
    if not email:
        return redirect(url_for('main.login'))
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    if not user:
        cursor.execute(
            "INSERT INTO users (fullname, age, email, password) VALUES (%s,%s,%s,%s)",
            (name, 0, email, "google_account")
        )
        db.commit()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
    session['user']    = name
    session['user_id'] = user[0]
    return redirect(url_for('main.dashboard'))


# ── GOOGLE LOGIN (POST — verifica token Firebase Admin) ───────────────────────
@main.route('/google_login_token', methods=['POST'])
def google_login_token():
    data = request.get_json()
    if not data or 'idToken' not in data:
        return jsonify({"ok": False, "error": "Sin token"}), 400
    try:
        decoded = fb_auth.verify_id_token(data['idToken'], clock_skew_seconds=60)
        uid     = decoded['uid']
        email   = decoded.get('email', '')
        name    = decoded.get('name', '')

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        if not user:
            cursor.execute(
                "INSERT INTO users (fullname, age, email, password) VALUES (%s,%s,%s,%s)",
                (name, 0, email, "google_account")
            )
            db.commit()
            cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cursor.fetchone()

        session['user']    = name
        session['user_id'] = user[0]
        return jsonify({"ok": True, "redirect": "/dashboard"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 401


# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@main.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('main.login'))
    return render_template('index.html', username=session['user'])


# ── ANALIZAR RETINA ───────────────────────────────────────────────────────────
@main.route('/analizar', methods=['POST'])
def analizar():
    if 'user' not in session:
        return redirect(url_for('main.login'))
    if 'image' not in request.files:
        return redirect(url_for('main.dashboard'))
    image = request.files['image']
    if image.filename == '' or not allowed_file(image.filename):
        return redirect(url_for('main.dashboard'))
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filename = secure_filename(image.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    image.save(filepath)
    result = predict(filepath)
    user_id = session.get('user_id')
    if user_id:
        try:
            cursor.execute(
                "INSERT INTO scan_history (user_id, image_filename, prediction, confidence, severity) VALUES (%s,%s,%s,%s,%s)",
                (user_id, filename, result['prediction'], result['confidence'], result['severity'])
            )
            db.commit()
        except Exception as e:
            print(f"[DB] Historial no guardado: {e}")
    return render_template('result.html', result=result, image_filename=filename, username=session['user'])


# ── HISTORIAL ─────────────────────────────────────────────────────────────────
@main.route('/historial')
@main.route('/historial')
def historial():
    if 'user' not in session:
        return redirect(url_for('main.login'))

    user_id = session.get('user_id')
    scans = []
    stats = {"total": 0, "promedio": 0, "max_severidad": "none"}

    if user_id:
        try:
            cursor.execute(
                "SELECT * FROM scan_history WHERE user_id=%s ORDER BY scanned_at DESC LIMIT 20",
                (user_id,)
            )
            scans = cursor.fetchall()

            if scans:
                total      = len(scans)
                confianzas = [float(s[4]) for s in scans]
                promedio   = round(sum(confianzas) / total, 1)

                orden = ["none", "mild", "moderate", "severe", "proliferative"]
                severidades = [s[5] for s in scans if s[5] in orden]
                max_sev = max(severidades, key=lambda x: orden.index(x)) if severidades else "none"

                stats = {"total": total, "promedio": promedio, "max_severidad": max_sev}

        except Exception as e:
            print(f"[DB] {e}")

    return render_template('historial.html', scans=scans, username=session['user'], stats=stats)


# ── LOGOUT ────────────────────────────────────────────────────────────────────
@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))