from flask import Flask, render_template, request
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import json
import os
from datetime import datetime, date

app = Flask(__name__)
analyzer = SentimentIntensityAnalyzer()

HISTORY_FILE = 'mood_history.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_entry(text, mood, level, note):
    history = load_history()
    entry = {
        'date': datetime.now().strftime('%d %b %Y, %I:%M %p'),
        'date_only': str(date.today()),
        'text': text,
        'mood': mood,
        'level': level,
        'note': note
    }
    history.insert(0, entry)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def check_crisis(history):
    if len(history) < 3:
        return False
    last_three = history[:3]
    return all(entry['level'] == 'High Stress' for entry in last_three)

def get_streak(history):
    if not history:
        return 0

    streak = 0
    today = date.today()
    expected = today

    seen_dates = []
    for entry in history:
        d = entry.get('date_only')
        if d and d not in seen_dates:
            seen_dates.append(d)

    for d_str in seen_dates:
        d = date.fromisoformat(d_str)
        if d == expected:
            streak += 1
            expected = date.fromordinal(expected.toordinal() - 1)
        elif d < expected:
            break

    return streak

def get_insight(compound, text):
    words = text.lower().split()
    length = len(words)
    is_heavy = length > 20 or compound < -0.5

    if any(w in words for w in ['breakup', 'broke', 'heartbreak', 'relationship', 'ex', 'memories']):
        if is_heavy:
            return ("Heartbreak is one of the most physically painful emotions humans experience — "
                    "it's not weakness, it's biology. What you're feeling is grief, and grief needs time, "
                    "not solutions. For now: let yourself feel it without judging it. Avoid replaying conversations. "
                    "Try to eat something, drink water, and sleep — your nervous system needs basic fuel to heal. "
                    "Talk to someone you trust, even just to say 'I'm not okay right now.'")
        else:
            return "Heartbreak takes time. Be patient with yourself — healing isn't linear."

    elif any(w in words for w in ['tired', 'exhausted', 'drained', 'sleep', 'energy']):
        if is_heavy:
            return ("Deep exhaustion isn't just physical — it's often emotional too. "
                    "Your mind and body are telling you they've been running on empty for too long. "
                    "Try to: step away from screens for 30 minutes, drink a glass of water right now, "
                    "and if possible lie down even without sleeping. Don't push through — rest IS productive.")
        else:
            return "Your body might be asking for rest. Even 20 minutes of stillness can reset a lot."

    elif any(w in words for w in ['alone', 'lonely', 'nobody', 'no one', 'isolated']):
        if is_heavy:
            return ("Loneliness can feel permanent, but it rarely is. Right now your brain is "
                    "telling you a story that nobody cares — that story isn't always accurate. "
                    "Try sending one message to someone, anyone — not to explain everything, "
                    "just to say hi. Connection starts small. You reaching out here shows you "
                    "still want to be seen, and that matters.")
        else:
            return "Feeling alone is heavy. One small connection — even a text — can shift things."

    elif any(w in words for w in ['anxious', 'worried', 'nervous', 'scared', 'fear', 'panic']):
        if is_heavy:
            return ("Anxiety is your brain trying to protect you by imagining every bad outcome. "
                    "It's exhausting. Right now try this: name 5 things you can see, 4 you can touch, "
                    "3 you can hear. This pulls your nervous system back to the present. "
                    "Then ask yourself — what is the ONE thing I can control in this moment? "
                    "Start there. Everything else can wait.")
        else:
            return "Anxiety lives in the future. Try bringing yourself back to this exact moment."

    elif any(w in words for w in ['unmotivated', 'motivation', 'lazy', 'stuck', 'pointless', 'purpose']):
        if is_heavy:
            return ("Losing motivation isn't a character flaw — it's often a signal that something "
                    "needs to change or that you've been pushing too hard for too long. "
                    "Start with the smallest possible action: make your bed, drink water, go outside "
                    "for 10 minutes. Motivation follows action — not the other way around. "
                    "You don't need to feel ready. Just start tiny.")
        else:
            return "Motivation follows action, not the other way. Start with something tiny today."

    elif any(w in words for w in ['angry', 'frustrated', 'annoyed', 'mad', 'rage', 'furious']):
        if is_heavy:
            return ("Strong anger usually has something underneath it — hurt, betrayal, or feeling "
                    "unheard. Before reacting, try to name what's beneath the anger. "
                    "Physical release helps: go for a fast walk, do 20 pushups, or even scream into "
                    "a pillow. Once your body calms down, the situation usually looks clearer.")
        else:
            return "Anger often has hurt underneath it. Give yourself space before responding to anything."

    elif any(w in words for w in ['happy', 'good', 'great', 'excited', 'grateful', 'amazing']):
        if is_heavy:
            return ("You're clearly in a good place right now — and you deserve to feel this fully. "
                    "Take a moment to actually notice it instead of rushing past it. "
                    "What made today different? Write it down if you can — "
                    "it's useful to remember what good feels like when harder days come.")
        else:
            return "This energy is worth protecting. Notice what contributed to this feeling today."

    elif compound <= -0.5:
        return ("You're carrying something heavy right now. That takes real strength even when it "
                "doesn't feel like it. Please don't go through this alone — talk to someone you trust, "
                "or reach out to iCall at 9152987821. You don't have to have the words figured out. "
                "Just saying 'I'm not doing well' is enough to start.")

    elif compound <= -0.05:
        return "It's okay to not be okay. You showed up today and that matters more than you think."

    else:
        return "Neutral days are valid too. Sometimes steady is exactly what we need."


def get_image(compound, text):
    words = text.lower().split()

    if any(w in words for w in ['breakup', 'broke', 'heartbreak', 'relationship', 'ex', 'memories', 'miss']):
        return 'images/heartbreak.jpg'
    elif any(w in words for w in ['give up', 'giving up', 'hopeless', 'pointless', 'worthless', 'quit']):
        return 'images/courage.jpg'
    elif any(w in words for w in ['anxious', 'worried', 'nervous', 'scared', 'fear', 'panic']):
        return 'images/calm.jpg'
    elif any(w in words for w in ['tired', 'exhausted', 'drained', 'sleep', 'energy']):
        return 'images/rest.jpg'
    elif any(w in words for w in ['alone', 'lonely', 'nobody', 'no one', 'isolated']):
        return 'images/together.jpg'
    elif any(w in words for w in ['angry', 'frustrated', 'annoyed', 'mad', 'rage']):
        return 'images/peace.jpg'
    elif any(w in words for w in ['unmotivated', 'stuck', 'lazy', 'motivation', 'purpose']):
        return 'images/rise.jpg'
    elif compound >= 0.05:
        return 'images/joy.jpg'
    else:
        return 'images/calm.jpg'
    
def get_videos(compound, text):
    words = text.lower().split()

    if any(w in words for w in ['breakup', 'broke', 'heartbreak', 'relationship', 'ex', 'memories', 'miss']):
        return [
            {'title': 'How to Heal a Broken Heart', 'channel': 'Jay Shetty', 'url': 'https://www.youtube.com/watch?v=ZSNxXCMJFpA'},
            {'title': 'Letting Go — Sadhguru', 'channel': 'Sadhguru', 'url': 'https://www.youtube.com/watch?v=PFlNXGdj59I'},
            {'title': 'You Will Be Okay — Gentle Reminder', 'channel': 'Calm', 'url': 'https://www.youtube.com/watch?v=RqPeLKMSQrE'},
        ]
    elif any(w in words for w in ['unmotivated', 'motivation', 'lazy', 'stuck', 'pointless', 'purpose', 'give up', 'giving up']):
        return [
            {'title': 'When You Feel Like Giving Up', 'channel': 'Motiversity', 'url': 'https://www.youtube.com/watch?v=mgmVOuLgFB0'},
            {'title': 'Start With Why — Simon Sinek', 'channel': 'TED', 'url': 'https://www.youtube.com/watch?v=u4ZoJKF_VuA'},
            {'title': 'The Power of Discipline', 'channel': 'David Goggins', 'url': 'https://www.youtube.com/watch?v=D1oNF7RxdcY'},
        ]
    elif any(w in words for w in ['anxious', 'worried', 'nervous', 'scared', 'fear', 'panic', 'stress']):
        return [
            {'title': 'How to Stop Anxiety — Guided', 'channel': 'Headspace', 'url': 'https://www.youtube.com/watch?v=O-6f5wQXSu8'},
            {'title': '5 Minute Meditation for Anxiety', 'channel': 'Goodful', 'url': 'https://www.youtube.com/watch?v=inpok4MKVLM'},
            {'title': 'Anxiety Is Not Your Enemy', 'channel': 'Sadhguru', 'url': 'https://www.youtube.com/watch?v=IBFCnHBBlxQ'},
        ]
    elif any(w in words for w in ['tired', 'exhausted', 'drained', 'sleep', 'energy']):
        return [
            {'title': 'Sleep Meditation — Deep Rest', 'channel': 'Jason Stephenson', 'url': 'https://www.youtube.com/watch?v=1vx8iUvfyCY'},
            {'title': 'Why You Are Always Tired', 'channel': 'Kurzgesagt', 'url': 'https://www.youtube.com/watch?v=js7V5MDRPEM'},
            {'title': 'Restore Your Energy — Sadhguru', 'channel': 'Sadhguru', 'url': 'https://www.youtube.com/watch?v=9xDNHZFWyog'},
        ]
    elif any(w in words for w in ['alone', 'lonely', 'nobody', 'no one', 'isolated']):
        return [
            {'title': 'You Are Not Alone', 'channel': 'Jay Shetty', 'url': 'https://www.youtube.com/watch?v=n3Xv_g3g-mA'},
            {'title': 'How to Deal With Loneliness', 'channel': 'Psych2Go', 'url': 'https://www.youtube.com/watch?v=bGOmcoSgDgE'},
            {'title': 'Finding Peace Within Yourself', 'channel': 'Sadhguru', 'url': 'https://www.youtube.com/watch?v=3rTs_GBUZ8M'},
        ]
    elif any(w in words for w in ['angry', 'frustrated', 'annoyed', 'mad', 'rage', 'furious']):
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
            {'title': 'Simple Habits for a Better Day', 'channel': 'Matt D\'Avella', 'url': 'https://www.youtube.com/watch?v=9gDMFcMC2ig'},
        ]    
@app.route('/')
def home():
    history = load_history()
    streak = get_streak(history)
    return render_template('index.html', streak=streak)


@app.route('/analyze', methods=['POST'])
def analyze():
    user_text = request.form['user_text']
    journal_note = request.form.get('journal_note', '').strip()
    score = analyzer.polarity_scores(user_text)
    compound = score['compound']
    words = user_text.lower().split()

    if compound >= 0.05:
        mood = "You seem positive and calm 😊"
        level = "Low Stress"
        if any(w in words for w in ['excited', 'amazing', 'fantastic', 'love']):
            header = "You're feeling really good today 🌟"
        elif any(w in words for w in ['grateful', 'thankful', 'blessed']):
            header = "You're in a grateful headspace today 🙏"
        else:
            header = "You seem calm and positive today 😊"

    elif compound <= -0.05:
        mood = "You seem stressed or low 😟"
        level = "High Stress"
        if any(w in words for w in ['breakup', 'broke', 'heartbreak', 'relationship']):
            header = "You're going through heartbreak right now 💔"
        elif any(w in words for w in ['alone', 'lonely', 'nobody', 'no one']):
            header = "You're feeling isolated and alone right now"
        elif any(w in words for w in ['tired', 'exhausted', 'drained']):
            header = "You're running on empty right now 😔"
        elif any(w in words for w in ['anxious', 'worried', 'nervous', 'scared']):
            header = "You're feeling anxious and overwhelmed right now"
        elif any(w in words for w in ['angry', 'frustrated', 'mad', 'furious']):
            header = "You're feeling frustrated and angry right now"
        elif any(w in words for w in ['unmotivated', 'stuck', 'pointless']):
            header = "You're feeling stuck and unmotivated right now"
        else:
            header = "You felt stressed or overwhelmed today 😟"

    else:
        mood = "You seem neutral today 😐"
        level = "Moderate"
        if any(w in words for w in ['okay', 'fine', 'alright', 'managing']):
            header = "You're getting through the day — that's enough"
        else:
            header = "You're feeling steady today 😐"

    insight = get_insight(compound, user_text)
    image = get_image(compound, user_text)
    videos = get_videos(compound, user_text)
    save_entry(user_text, mood, level, journal_note)
    history = load_history()
    crisis = check_crisis(history)

    return render_template('result.html',
                           mood=mood,
                           level=level,
                           text=user_text,
                           header=header,
                           insight=insight,
                           note=journal_note,
                           crisis=crisis,
                           image=image,
                           videos=videos)


@app.route('/history')
def history():
    entries = load_history()

    dates = []
    scores = []
    for entry in reversed(entries[-10:]):
        dates.append(entry['date'].split(',')[1].strip())
        if entry['level'] == 'High Stress':
            scores.append(2)
        elif entry['level'] == 'Moderate':
            scores.append(1)
        else:
            scores.append(0)

    return render_template('history.html',
                           entries=entries,
                           dates=dates,
                           scores=scores)


if __name__ == '__main__':
    app.run(debug=True)