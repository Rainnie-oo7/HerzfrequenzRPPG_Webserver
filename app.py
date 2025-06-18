from flask import Flask, render_template, request, redirect, url_for, flash, Response
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
camera = cv2.VideoCapture(0)  # Index 0 für Standardkamera
###Funzt nicht mit Smartphone. Am PC habe ich keine Kamera
#muss es mit vid1.mp4 ausprobieren
def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # JPEG-Encoding
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            # Multipart response
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_plot')
@login_required
def video_plot():
    return render_template('video_plot.html')

@app.route('/video_feed')
@login_required
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

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



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0')
