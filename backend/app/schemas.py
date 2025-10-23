from pydantic import BaseModel, EmailStr
from typing import Optional, List

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int
    is_admin: bool
    class Config: from_attributes = True

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserRead

# --- Application Schemas ---
class CreditApplicationCreate(BaseModel):
    full_name: str
    gender: str
    married: str
    dependents: str
    education: str
    self_employed: str
    monthly_income: float
    coapplicant_income: float
    loan_amount: float
    loan_amount_term: int
    credit_history: int
    property_area: str

class CreditApplicationRead(BaseModel):
    id: int
    status: str
    final_decision: Optional[str] = None
    # This is the crucial fix: The preliminary decision is now included
    # in the data sent back to the customer after the first submission.
    preliminary_decision: Optional[str] = None
    class Config: from_attributes = True

class CreditApplicationReadWithOwner(BaseModel):
    id: int
    owner: UserRead
    status: str
    aadhaar_path: Optional[str] = None
    salary_slip_path: Optional[str] = None
    preliminary_decision: Optional[str] = None
    verified_decision: Optional[str] = None
    final_decision: Optional[str] = None
    ocr_name_match: Optional[bool] = None
    ocr_income_match: Optional[bool] = None
    class Config: from_attributes = True

# --- Prediction Schema ---
class PredictionResponse(BaseModel):
    message: str
    result: str
    score: float
    report_url: str

