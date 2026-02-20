from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime, date, timedelta
import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.config['SECRET_KEY'] = 'biotone-secret-key-2026'
import os
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///biotone.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
MAIL_EMAIL = os.environ.get('MAIL_EMAIL')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
analyzer = SentimentIntensityAnalyzer()

# ─── MODELS ───────────────────────────────────────────────
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    entries = db.relationship('MoodEntry', backref='user', lazy=True)

class MoodEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(50))
    date_only = db.Column(db.String(20))
    text = db.Column(db.Text)
    mood = db.Column(db.String(100))
    level = db.Column(db.String(50))
    note = db.Column(db.Text)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ─── HELPERS ──────────────────────────────────────────────
def get_streak(entries):
    if not entries:
        return 0
    streak = 0
    expected = date.today()
    seen = []
    for e in entries:
        d = e.date_only
        if d and d not in seen:
            seen.append(d)
    for d_str in seen:
        d = date.fromisoformat(d_str)
        if d == expected:
            streak += 1
            expected = date.fromordinal(expected.toordinal() - 1)
        elif d < expected:
            break
    return streak

def check_crisis(entries):
    if len(entries) < 3:
        return False
    return all(e.level == 'High Stress' for e in entries[:3])

def send_otp_email(to_email, otp):
    msg = MIMEMultipart()
    msg['From'] = MAIL_EMAIL
    msg['To'] = to_email
    msg['Subject'] = 'Bio-Tone — Your OTP Code'

    body = f"""
    Hi there,

    Your Bio-Tone OTP code is:

    {otp}

    This code expires in 10 minutes.
    If you didn't request this, ignore this email.

    — Bio-Tone Team
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(MAIL_EMAIL, MAIL_PASSWORD)
        server.sendmail(MAIL_EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def generate_otp():
    return str(random.randint(100000, 999999))

def get_insight(compound, text):
    words = text.lower().split()
    length = len(words)
    is_heavy = length > 20 or compound < -0.5

    if any(w in words for w in ['breakup','broke','heartbreak','relationship','ex','memories']):
        return ("Heartbreak is one of the most physically painful emotions humans experience — it's not weakness, it's biology. What you're feeling is grief, and grief needs time. Let yourself feel it without judging it. Talk to someone you trust.") if is_heavy else "Heartbreak takes time. Be patient with yourself — healing isn't linear."
    elif any(w in words for w in ['tired','exhausted','drained','sleep','energy']):
        return ("Deep exhaustion isn't just physical — it's emotional too. Step away from screens, drink water, and rest. Don't push through — rest IS productive.") if is_heavy else "Your body might be asking for rest. Even 20 minutes of stillness can reset a lot."
    elif any(w in words for w in ['alone','lonely','nobody','no one','isolated']):
        return ("Loneliness can feel permanent, but it rarely is. Try sending one message to someone — connection starts small. You reaching out shows you still want to be seen.") if is_heavy else "Feeling alone is heavy. One small connection — even a text — can shift things."
    elif any(w in words for w in ['anxious','worried','nervous','scared','fear','panic']):
        return ("Name 5 things you can see, 4 you can touch, 3 you can hear. This pulls your nervous system back to the present. Then ask: what is the ONE thing I can control right now?") if is_heavy else "Anxiety lives in the future. Try bringing yourself back to this exact moment."
    elif any(w in words for w in ['unmotivated','motivation','lazy','stuck','pointless','purpose']):
        return ("Losing motivation is often a signal you've been pushing too hard. Start with the smallest possible action. Motivation follows action — not the other way around.") if is_heavy else "Motivation follows action, not the other way. Start with something tiny today."
    elif any(w in words for w in ['angry','frustrated','annoyed','mad','rage','furious']):
        return ("Strong anger usually has something underneath it — hurt or feeling unheard. Try physical release: a fast walk, pushups, or scream into a pillow. Then the situation will look clearer.") if is_heavy else "Anger often has hurt underneath it. Give yourself space before responding."
    elif any(w in words for w in ['happy','good','great','excited','grateful','amazing']):
        return ("You're in a good place right now — take a moment to actually notice it. What made today different? Write it down — it's useful to remember what good feels like.") if is_heavy else "This energy is worth protecting. Notice what contributed to this feeling today."
    elif compound <= -0.5:
        return ("You're carrying something heavy. Please don't go through this alone — talk to someone you trust, or reach out to iCall at 9152987821. Just saying 'I'm not okay' is enough to start.")
    elif compound <= -0.05:
        return "It's okay to not be okay. You showed up today and that matters more than you think."
    else:
        return "Neutral days are valid too. Sometimes steady is exactly what we need."

def get_image(compound, text):
    words = text.lower().split()
    if any(w in words for w in ['breakup','broke','heartbreak','relationship','ex','memories','miss']):
        return 'images/heartbreak.jpg'
    elif any(w in words for w in ['give up','giving up','hopeless','pointless','worthless','quit']):
        return 'images/courage.jpg'
    elif any(w in words for w in ['anxious','worried','nervous','scared','fear','panic']):
        return 'images/calm.jpg'
    elif any(w in words for w in ['tired','exhausted','drained','sleep','energy']):
        return 'images/rest.jpg'
    elif any(w in words for w in ['alone','lonely','nobody','no one','isolated']):
        return 'images/together.jpg'
    elif any(w in words for w in ['angry','frustrated','annoyed','mad','rage']):
        return 'images/peace.jpg'
    elif any(w in words for w in ['unmotivated','stuck','lazy','motivation','purpose']):
        return 'images/rise.jpg'
    elif compound >= 0.05:
        return 'images/joy.jpg'
    else:
        return 'images/calm.jpg'

def get_videos(compound, text):
    words = text.lower().split()
    if any(w in words for w in ['breakup','broke','heartbreak','relationship','ex','memories','miss']):
        return [
            {'title': 'How to Heal a Broken Heart', 'channel': 'Jay Shetty', 'url': 'https://www.youtube.com/watch?v=ZSNxXCMJFpA'},
            {'title': 'Letting Go — Sadhguru', 'channel': 'Sadhguru', 'url': 'https://www.youtube.com/watch?v=PFlNXGdj59I'},
            {'title': 'You Will Be Okay', 'channel': 'Calm', 'url': 'https://www.youtube.com/watch?v=RqPeLKMSQrE'},
        ]
    elif any(w in words for w in ['unmotivated','motivation','lazy','stuck','pointless','purpose']):
        return [
            {'title': 'When You Feel Like Giving Up', 'channel': 'Motiversity', 'url': 'https://www.youtube.com/watch?v=mgmVOuLgFB0'},
            {'title': 'Start With Why — Simon Sinek', 'channel': 'TED', 'url': 'https://www.youtube.com/watch?v=u4ZoJKF_VuA'},
            {'title': 'The Power of Discipline', 'channel': 'David Goggins', 'url': 'https://www.youtube.com/watch?v=D1oNF7RxdcY'},
        ]
    elif any(w in words for w in ['anxious','worried','nervous','scared','fear','panic','stress']):
        return [
            {'title': 'How to Stop Anxiety', 'channel': 'Headspace', 'url': 'https://www.youtube.com/watch?v=O-6f5wQXSu8'},
            {'title': '5 Minute Meditation for Anxiety', 'channel': 'Goodful', 'url': 'https://www.youtube.com/watch?v=inpok4MKVLM'},
            {'title': 'Anxiety Is Not Your Enemy', 'channel': 'Sadhguru', 'url': 'https://www.youtube.com/watch?v=IBFCnHBBlxQ'},
        ]
    elif any(w in words for w in ['tired','exhausted','drained','sleep','energy']):
        return [
            {'title': 'Sleep Meditation — Deep Rest', 'channel': 'Jason Stephenson', 'url': 'https://www.youtube.com/watch?v=1vx8iUvfyCY'},
            {'title': 'Why You Are Always Tired', 'channel': 'Kurzgesagt', 'url': 'https://www.youtube.com/watch?v=js7V5MDRPEM'},
            {'title': 'Restore Your Energy', 'channel': 'Sadhguru', 'url': 'https://www.youtube.com/watch?v=9xDNHZFWyog'},
        ]
    elif any(w in words for w in ['alone','lonely','nobody','no one','isolated']):
        return [
            {'title': 'You Are Not Alone', 'channel': 'Jay Shetty', 'url': 'https://www.youtube.com/watch?v=n3Xv_g3g-mA'},
            {'title': 'How to Deal With Loneliness', 'channel': 'Psych2Go', 'url': 'https://www.youtube.com/watch?v=bGOmcoSgDgE'},
            {'title': 'Finding Peace Within Yourself', 'channel': 'Sadhguru', 'url': 'https://www.youtube.com/watch?v=3rTs_GBUZ8M'},
        ]
    elif any(w in words for w in ['angry','frustrated','annoyed','mad','rage','furious']):
        return [
            {'title': 'How to Control Anger', 'channel': 'Sadhguru', 'url': 'https://www.youtube.com/watch?v=_278Y7sPFuk'},
            {'title': 'Anger Management Techniques', 'channel': 'Psych2Go', 'url': 'https://www.youtube.com/watch?v=BsVq5R_F6RA'},
            {'title': 'Box Breathing to Calm Down Fast', 'channel': 'Mark Divine', 'url': 'https://www.youtube.com/watch?v=tEmt1Znux58'},
        ]
    elif compound >= 0.05:
        return [
            {'title': 'Morning Motivation to Start Strong', 'channel': 'Motiversity', 'url': 'https://www.youtube.com/watch?v=ZXsQAXx_ao0'},
            {'title': 'Gratitude Meditation — 10 Minutes', 'channel': 'Goodful', 'url': 'https://www.youtube.com/watch?v=u3VvyFuqiwM'},
            {'title': 'Stay Consistent — Keep Going', 'channel': 'Tom Bilyeu', 'url': 'https://www.youtube.com/watch?v=_ZFEDOWGXAs'},
        ]
    else:
        return [
            {'title': 'Daily Mindfulness Practice', 'channel': 'Headspace', 'url': 'https://www.youtube.com/watch?v=ZToicYcHIOU'},
            {'title': 'Journaling for Mental Clarity', 'channel': 'Better Ideas', 'url': 'https://www.youtube.com/watch?v=dArgOrm98Bk'},
            {'title': "Simple Habits for a Better Day", 'channel': "Matt D'Avella", 'url': 'https://www.youtube.com/watch?v=9gDMFcMC2ig'},
        ]

# ─── ROUTES ───────────────────────────────────────────────
@app.route('/')
@login_required
def home():
    entries = MoodEntry.query.filter_by(user_id=current_user.id).order_by(MoodEntry.id.desc()).all()
    streak = get_streak(entries)
    return render_template('index.html', streak=streak)

@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    user_text = request.form['user_text'].strip()
    journal_note = request.form.get('journal_note', '').strip()
    score = analyzer.polarity_scores(user_text)
    compound = score['compound']
    words = user_text.lower().split()

    if compound >= 0.05:
        mood = "You seem positive and calm 😊"
        level = "Low Stress"
        if any(w in words for w in ['excited','amazing','fantastic','love']):
            header = "You're feeling really good today 🌟"
        elif any(w in words for w in ['grateful','thankful','blessed']):
            header = "You're in a grateful headspace today 🙏"
        else:
            header = "You seem calm and positive today 😊"
    elif compound <= -0.05:
        mood = "You seem stressed or low 😟"
        level = "High Stress"
        if any(w in words for w in ['breakup','broke','heartbreak','relationship']):
            header = "You're going through heartbreak right now 💔"
        elif any(w in words for w in ['alone','lonely','nobody','no one']):
            header = "You're feeling isolated and alone right now"
        elif any(w in words for w in ['tired','exhausted','drained']):
            header = "You're running on empty right now 😔"
        elif any(w in words for w in ['anxious','worried','nervous','scared']):
            header = "You're feeling anxious and overwhelmed right now"
        elif any(w in words for w in ['angry','frustrated','mad','furious']):
            header = "You're feeling frustrated and angry right now"
        elif any(w in words for w in ['unmotivated','stuck','pointless']):
            header = "You're feeling stuck and unmotivated right now"
        else:
            header = "You felt stressed or overwhelmed today 😟"
    else:
        mood = "You seem neutral today 😐"
        level = "Moderate"
        header = "You're feeling steady today 😐"

    insight = get_insight(compound, user_text)
    image = get_image(compound, user_text)
    videos = get_videos(compound, user_text)

    entry = MoodEntry(
        user_id=current_user.id,
        date=datetime.now().strftime('%d %b %Y, %I:%M %p'),
        date_only=str(date.today()),
        text=user_text,
        mood=mood,
        level=level,
        note=journal_note
    )
    db.session.add(entry)
    db.session.commit()

    entries = MoodEntry.query.filter_by(user_id=current_user.id).order_by(MoodEntry.id.desc()).all()
    crisis = check_crisis(entries)

    return render_template('result.html',
                           mood=mood, level=level, text=user_text,
                           header=header, insight=insight, note=journal_note,
                           crisis=crisis, image=image, videos=videos)

@app.route('/history')
@login_required
def history():
    entries = MoodEntry.query.filter_by(user_id=current_user.id).order_by(MoodEntry.id.desc()).all()
    dates, scores = [], []
    for entry in list(reversed(entries))[-10:]:
        dates.append(entry.date.split(',')[1].strip() if entry.date and ',' in entry.date else entry.date)
        if entry.level == 'High Stress':
            scores.append(2)
        elif entry.level == 'Moderate':
            scores.append(1)
        else:
            scores.append(0)
    return render_template('history.html', entries=entries, dates=dates, scores=scores)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Try logging in.')
            return redirect(url_for('register'))
        new_user = User(username=email, email=email, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Wrong username or password.')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip()
        user = User.query.filter_by(email=email).first()
        if user:
            otp = generate_otp()
            user.otp = otp
            user.otp_expiry = datetime.now() + timedelta(minutes=10)
            db.session.commit()
            success = send_otp_email(email, otp)
            if success:
                flash('OTP sent to your email. Check your inbox.')
                return redirect(url_for('verify_otp', email=email))
            else:
                flash('Failed to send email. Try again.')
        else:
            flash('No account found with that email.')
    return render_template('forgot_password.html')

@app.route('/verify-otp/<email>', methods=['GET', 'POST'])
def verify_otp(email):
    if request.method == 'POST':
        entered_otp = request.form['otp'].strip()
        user = User.query.filter_by(email=email).first()
        if user and user.otp == entered_otp and user.otp_expiry > datetime.now():
            user.otp = None
            user.otp_expiry = None
            db.session.commit()
            return redirect(url_for('reset_password', email=email))
        else:
            flash('Invalid or expired OTP. Try again.')
    return render_template('verify_otp.html', email=email)

@app.route('/reset-password/<email>', methods=['GET', 'POST'])
def reset_password(email):
    if request.method == 'POST':
        new_password = request.form['password'].strip()
        user = User.query.filter_by(email=email).first()
        if user:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            flash('Password reset successful. Please login.')
            return redirect(url_for('login'))
    return render_template('reset_password.html', email=email)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
# ```

# Save with **Ctrl + S**.

# ---

## Then Push to GitHub
# ```
# git add .
# git commit -m "Fix port binding for Render"
# git push