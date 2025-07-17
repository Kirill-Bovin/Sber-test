import os

import numpy as np
import pandas as pd
from joblib import dump
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split

# Загружаем подготовленные данные
df = pd.read_csv("data/clean/clean_deposits.csv")

# Создаём целевую переменную:
# Рекомендуем, если ставка в топ 10% или если цель накопления (goal_accumulation == 1)
rate_threshold = df["rate"].quantile(0.9)
df["is_recommend"] = (
    (df["rate"] >= rate_threshold) | (df["goal_accumulation"] == 1)
).astype(int)

# Фичи — все, кроме целевой и name
feature_cols = [c for c in df.columns if c not in ["name", "is_recommend"]]

X = df[feature_cols]
y = df["is_recommend"]

# Разбиваем на тренировочную и тестовую выборки с стратификацией
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Создаём и обучаем классификатор
clf = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")
clf.fit(X_train, y_train)

# Оценка на тесте
y_pred = clf.predict(X_test)
y_proba = clf.predict_proba(X_test)[:, 1]

print(classification_report(y_test, y_pred))
print(f"ROC AUC: {roc_auc_score(y_test, y_proba):.3f}")

# Сохраняем модель и порог (например 0.2)
os.makedirs("models", exist_ok=True)
dump({"pipeline": clf, "threshold": 0.2}, "models/deposit_recommender.joblib")
print("Модель сохранена: models/deposit_recommender.joblib")
