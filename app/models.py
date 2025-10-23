from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_admin: bool = Field(default=False)
    applications: list["CreditApplication"] = Relationship(back_populates="owner")

class CreditApplication(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Data from chatbot
    full_name: str
    gender: Optional[str] = None
    married: Optional[str] = None
    dependents: Optional[str] = None
    education: Optional[str] = None
    self_employed: Optional[str] = None
    monthly_income: float
    coapplicant_income: Optional[float] = 0.0
    loan_amount: float
    loan_amount_term: Optional[int] = None
    credit_history: Optional[int] = None
    property_area: Optional[str] = None
    
    # Fields for Bank Statement Analysis
    bank_statement_path: Optional[str] = None
    average_balance: Optional[float] = None
    estimated_salary: Optional[float] = None
    bounced_checks_count: Optional[int] = None
    missed_recent_emis: Optional[bool] = None
    
    # Workflow and Prediction fields
    status: str = Field(default="pending_documents")
    preliminary_decision: Optional[str] = None
    verified_decision: Optional[str] = None
    verified_score: Optional[float] = None
    
    final_decision: Optional[str] = None
    # This is the new field that was missing from the database model
    final_score: Optional[float] = None 
    decision_reasons: Optional[str] = None
    
    # Other document paths
    aadhaar_path: Optional[str] = None
    salary_slip_path: Optional[str] = None
    ocr_name_match: Optional[bool] = None
    ocr_income_match: Optional[bool] = None
    
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    owner_id: int = Field(foreign_key="user.id")
    owner: "User" = Relationship(back_populates="applications")

