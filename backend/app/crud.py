from sqlmodel import Session, select
from typing import List
from . import models, schemas, auth

def get_user_by_email(db: Session, email: str) -> models.User | None:
    """Fetches a single user from the database by their email address."""
    statement = select(models.User).where(models.User.email == email)
    return db.execute(statement).scalar_one_or_none()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Creates a new user in the database with a hashed password."""
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_application(db: Session, application: schemas.CreditApplicationCreate, owner_id: int) -> models.CreditApplication:
    """Creates a new credit application in the database."""
    db_application = models.CreditApplication.model_validate(application, update={"owner_id": owner_id})
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application

def get_application(db: Session, app_id: int) -> models.CreditApplication | None:
    """Fetches a single application by its ID."""
    return db.get(models.CreditApplication, app_id)

def update_application_with_statement_data(db: Session, app_id: int, statement_path: str, metrics: dict):
    """Saves the bank statement path and all analyzed financial metrics to the database."""
    app = get_application(db, app_id)
    if app:
        app.bank_statement_path = statement_path
        app.average_balance = metrics.get("average_balance")
        app.estimated_salary = metrics.get("estimated_salary")
        app.bounced_checks_count = metrics.get("bounced_checks_count")
        app.missed_recent_emis = metrics.get("missed_recent_emis")
        db.add(app)
        db.commit()
        db.refresh(app)
    return app

def update_preliminary_decision(db: Session, app_id: int, decision: str):
    """Updates an application with the initial AI prediction."""
    app = db.get(models.CreditApplication, app_id)
    if app:
        app.preliminary_decision = decision
        db.add(app)
        db.commit()
        db.refresh(app)
    return app

def update_verified_decision(db: Session, app_id: int, decision: str, score: float, name_match: bool, income_match: bool):
    """Updates the application with the OCR-verified prediction."""
    app = db.get(models.CreditApplication, app_id)
    if app:
        app.verified_decision = decision
        app.verified_score = score
        app.ocr_name_match = name_match
        app.ocr_income_match = income_match
        db.add(app)
        db.commit()
        db.refresh(app)
    return app
    
def update_application_docs_and_status(db: Session, app_id: int, aadhaar_path: str, salary_slip_path: str):
    """Updates an application with document paths and sets status to pending_approval."""
    app = get_application(db, app_id)
    if app:
        app.aadhaar_path = aadhaar_path
        app.salary_slip_path = salary_slip_path
        app.status = "pending_approval"
        db.add(app)
        db.commit()
        db.refresh(app)
    return app

def update_final_decision(db: Session, app_id: int, decision: str, score: float, reasons: str) -> models.CreditApplication | None:
    """Updates the application with the final, admin-approved decision."""
    app = get_application(db, app_id)
    if app:
        app.final_decision = decision
        app.final_score = score
        app.decision_reasons = reasons
        app.status = decision.lower()
        db.add(app)
        db.commit()
        db.refresh(app)
    return app

def get_user_applications(db: Session, user_id: int) -> List[models.CreditApplication]:
    """Fetches all applications belonging to a specific user."""
    statement = select(models.CreditApplication).where(models.CreditApplication.owner_id == user_id)
    return db.execute(statement).scalars().all()

def get_all_applications(db: Session) -> List[models.CreditApplication]:
    """Fetches all applications from all users (for admin)."""
    statement = select(models.CreditApplication)
    return db.execute(statement).scalars().all()

def is_name_match(entered_name: str, extracted_name: str | None, threshold: float = 0.8) -> bool:
    """
    This is the new function that was missing.
    It performs an intelligent 'fuzzy match' between two names.
    """
    if not extracted_name or not entered_name:
        return False
    
    entered_words = set(entered_name.lower().split())
    extracted_words = set(extracted_name.lower().split())
    
    common_words = entered_words.intersection(extracted_words)
    
    if not entered_words:
        return False
        
    match_ratio = len(common_words) / len(entered_words)
    
    return match_ratio >= threshold

