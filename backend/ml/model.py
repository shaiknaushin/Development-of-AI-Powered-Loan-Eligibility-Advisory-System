import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import f1_score
import joblib
import os
import numpy as np
from sqlmodel import create_engine, Session, select
from app.models import CreditApplication

# --- CONFIGURATION ---
DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL)
MODEL_PATH = "models_trained/credit_model.joblib"

CATEGORICAL_FEATURES = ['gender', 'married', 'dependents', 'education', 'self_employed', 'property_area']
NUMERICAL_FEATURES = [
    'monthly_income', 'coapplicant_income', 'loan_amount', 'loan_amount_term', 
    'credit_history', 'average_balance', 'bounced_checks_count', 'missed_recent_emis'
]
ALL_FEATURES = CATEGORICAL_FEATURES + NUMERICAL_FEATURES

def train_and_save_model():
    

    # ... (training logic remains the same, as it's the prediction logic that needs the upgrade)
    print("--- Starting AI Model Training ---")
    
    try:
        print("[Step 1/5] Loading and preparing Kaggle dataset...")
        df_kaggle = pd.read_csv("ml/synthetic_data.csv")
        df_kaggle = df_kaggle.rename(columns={
            'Gender': 'gender', 'Married': 'married', 'Dependents': 'dependents',
            'Education': 'education', 'Self_Employed': 'self_employed',
            'ApplicantIncome': 'monthly_income', 'CoapplicantIncome': 'coapplicant_income',
            'LoanAmount': 'loan_amount', 'Loan_Amount_Term': 'loan_amount_term',
            'Credit_History': 'credit_history', 'Property_Area': 'property_area',
            'Loan_Status': 'approved'
        })
        df_kaggle['approved'] = df_kaggle['approved'].apply(lambda x: 1 if x == 'Y' else 0)
        
        df_kaggle['average_balance'] = 50000 
        df_kaggle['bounced_checks_count'] = 0
        df_kaggle['missed_recent_emis'] = False
        
        for col in ['gender', 'married', 'dependents', 'self_employed']:
            df_kaggle[col].fillna(df_kaggle[col].mode()[0], inplace=True)
        df_kaggle['credit_history'].fillna(1.0, inplace=True)
        df_kaggle['loan_amount_term'].fillna(df_kaggle['loan_amount_term'].mean(), inplace=True)
        df_kaggle.dropna(subset=['loan_amount', 'monthly_income'], inplace=True)
    except FileNotFoundError:
        print("[ERROR] Could not find 'ml/synthetic_data.csv'.")
        return

    print("[Step 2/5] Loading real application data from database...")
    with Session(engine) as session:
        apps = session.exec(select(CreditApplication).where(CreditApplication.status.in_(['approved', 'rejected']))).all()
        df_real = pd.DataFrame([app.model_dump() for app in apps])
        if not df_real.empty:
            df_real['approved'] = df_real['final_decision'].apply(lambda x: 1 if x == 'Approved' else 0)
    
    df = pd.concat([df_kaggle, df_real], ignore_index=True)
    if df.empty or len(df) < 5: return

    for col in ['average_balance', 'bounced_checks_count', 'missed_recent_emis']:
        df[col].fillna(0, inplace=True)
    df['missed_recent_emis'] = df['missed_recent_emis'].astype(int)

    X = df[ALL_FEATURES]
    y = df['approved']
    
    preprocessor = ColumnTransformer(transformers=[
        ('num', StandardScaler(), NUMERICAL_FEATURES),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), CATEGORICAL_FEATURES)
    ], remainder='passthrough')

    pipeline = Pipeline(steps=[('preprocessor', preprocessor),
                               ('classifier', RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced'))])

    print("[Step 3/5] Fitting the RandomForest model...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    pipeline.fit(X_train, y_train)
    
    print("[Step 4/5] Calibrating optimal decision threshold...")
    y_pred_proba = pipeline.predict_proba(X_test)[:, 1]
    thresholds = np.arange(0.3, 0.7, 0.01)
    f1_scores = [f1_score(y_test, y_pred_proba > t) for t in thresholds]
    best_threshold = thresholds[np.argmax(f1_scores)]

    print("[Step 5/5] Evaluating and saving model...")
    final_f1 = f1_score(y_test, y_pred_proba > best_threshold)
    joblib.dump({'model': pipeline, 'threshold': best_threshold}, MODEL_PATH)
    print(f"--- AI Model Training Complete! Final F1 Score: {final_f1:.3f} ---")


def predict_creditworthiness(app: CreditApplication, use_ocr_data: bool = False, ocr_data: dict = None):
    prediction_data = app.model_dump()
    if use_ocr_data and ocr_data and ocr_data.get("salary"):
        prediction_data['monthly_income'] = ocr_data["salary"]
        
    # --- NEW: BANK-GRADE HARD RULES ENGINE ---
    # These rules are checked BEFORE the AI model is even called.
    if prediction_data.get('credit_history') == 0:
        return "High Risk (Rejected)", 0.05, {"Reason": "Failed to meet previous credit guidelines."}
    if prediction_data.get('missed_recent_emis') is True:
        return "High Risk (Rejected)", 0.10, {"Reason": "Recent EMI payments were missed in the bank statement."}
    if prediction_data.get('bounced_checks_count', 0) > 1:
        return "High Risk (Rejected)", 0.15, {"Reason": "Multiple bounced checks found in the bank statement."}

    if not os.path.exists(MODEL_PATH):
        train_and_save_model()
    
    if not os.path.exists(MODEL_PATH):
         return "Error", 0.0, {"Reason": "Model could not be trained"}

    model_data = joblib.load(MODEL_PATH)
    model = model_data['model']
    threshold = model_data['threshold']
    
    if prediction_data.get('loan_amount') and prediction_data['loan_amount'] > 1000:
         prediction_data['loan_amount'] = prediction_data['loan_amount'] / 1000

    data = pd.DataFrame([prediction_data])
    for col in ALL_FEATURES:
        if col not in data.columns: data[col] = 0
    data['missed_recent_emis'] = data['missed_recent_emis'].astype(int)
    data = data[ALL_FEATURES]

    proba = model.predict_proba(data)[0]
    score = float(proba[1])
    
    if score > (threshold + 0.15):
        result = "Low Risk (Likely Approve)"
    elif score < (threshold - 0.15):
        result = "High Risk (Likely Reject)"
    else:
        result = "Medium Risk (Admin Review Required)"
    
    print(f"\n--- AI Prediction Log for App ID: {app.id} ---")
    print(f"Credit History: {data['credit_history'].iloc[0]}, Missed EMIs: {data['missed_recent_emis'].iloc[0]}")
    print(f"Model Confidence (Approve): {score:.2f} | Threshold: {threshold:.2f}")
    print(f"Final Prediction: {result}")
    print("--------------------------------------\n")
    
    return result, score, {"Prediction based on": "Overall application profile"}

