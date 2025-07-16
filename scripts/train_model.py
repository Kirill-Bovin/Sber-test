import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from joblib import dump

df = pd.read_csv('data/clean/clean_deposits.csv')
df['is_recommend'] = (df['rate'] >= df['rate'].quantile(0.9)).astype(int)

features = ['rate', 'term_months', 'min_amount', 'risk_level', 'goal_accumulation']
X = df[features]
y = df['is_recommend']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

pipe = Pipeline([
    ('clf', LogisticRegression(class_weight='balanced', max_iter=1000))
])

pipe.fit(X_train, y_train)

os.makedirs('models', exist_ok=True)

dump({'pipeline': pipe, 'threshold': 0.20}, 'models/logreg_rec.joblib')
print('Model saved to models/logreg_rec.joblib')