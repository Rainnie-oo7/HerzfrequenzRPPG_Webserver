import io
import matplotlib
matplotlib.use('Agg')  # Verhindert GUI-Fehler in Webserver-Kontext
import matplotlib.pyplot as plt
import numpy as np
import threading
import time
from flask import Flask, render_template, request, redirect, url_for, flash, Response, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import cv2

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todos.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
latest_frame = None
cap = cv2.VideoCapture('static/vid3ich.mp4')


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

####


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user is None:
            user = User(username=username, password=password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Username already exists', 'danger')
    return render_template('register.html')

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()

    return redirect(url_for('login'))


@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        description = request.form['description']
        new_todo = Todo(description=description, user_id=current_user.id)
        db.session.add(new_todo)
        db.session.commit()
        return redirect(url_for('index'))
    todos = Todo.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', todos=todos)

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/add', methods=['POST'])
@login_required
def add_todo():
    description = request.form['description']
    new_todo = Todo(description=description, user_id=current_user.id)
    db.session.add(new_todo)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/update/<int:id>', methods=['POST'])
@login_required
def update_todo(id):
    todo = Todo.query.get_or_404(id)
    todo.description = request.form['description']
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_todo(id):
    todo = Todo.query.get_or_404(id)
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/privacy', methods=['GET', 'POST'])
def privacy():
    if request.method == 'POST':
        if 'accept' in request.form:
            return redirect(url_for('index'))
        else:
            error_html = '<p style="color: red;">Du musst die Datenschutzerklärung akzeptieren, um fortzufahren.</p>'
            return render_template('privacy.html', error_message=error_html)
    return render_template('privacy.html', error_message='')


# Verhindert das Zurückgehen, Damit wird jedes HTML-Ergebnis so gesendet, dass der Browser es nicht cachen darf
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/static_image')
@login_required
def static_image():
    # Beispiel: Bild laden (oder generiere eins mit OpenCV)
    img = cv2.imread('static/Einkaufskorb.png')  # → stelle sicher, dass es existiert
    # img = cv2.putText(img, 'Hallo', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    _, buffer = cv2.imencode('.png', img)
    io_buf = io.BytesIO(buffer.tobytes())

    return send_file(io_buf, mimetype='image/jpeg')

def capture_loop():
    global latest_frame
    while True:
        success, frame = cap.read()
        if not success:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        latest_frame = frame.copy()
        time.sleep(1 / 30)  # ca. 30 FPS

@app.route('/video_stream')
@login_required
def video_stream():
    def stream():
        global latest_frame
        while True:
            if latest_frame is None:
                continue
            _, buffer = cv2.imencode('.jpg', latest_frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(1 / 30)

    return Response(stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/histogram_stream')
@login_required
def histogram_stream():
    global latest_frame
    if latest_frame is None:
        return "No frame", 503

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.set_xlim(0, 256)
    ax.set_ylim(0, 10000)  # Beispielwert anpassen

    for i, color in enumerate(('b', 'g', 'r')):
        hist = cv2.calcHist([latest_frame], [i], None, [256], [0, 256])
        ax.plot(hist, color=color)

    ax.set_title("Live RGB-Histogramm")
    ax.set_xlabel("Helligkeit")
    ax.set_ylabel("Häufigkeit")
    fig.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)

    return send_file(buf, mimetype='image/png')


if __name__ == "__main__":
    threading.Thread(target=capture_loop, daemon=True).start()

    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0')
