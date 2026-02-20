from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()
sentence = "I am feeling really overwhelmed and exhausted today"
score = analyzer.polarity_scores(sentence)
print(score)