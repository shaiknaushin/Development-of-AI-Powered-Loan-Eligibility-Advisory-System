from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session
from app import models, schemas, auth, crud, ocr, statement_parser
from app.database import get_session
from app.websockets import manager
from ml import model as ml_model
import shutil
import json
from typing import List

router = APIRouter()

@router.post("/applications", response_model=schemas.CreditApplicationRead)
def create_application_with_statement(
    db: Session = Depends(get_session),
    current_user: models.User = Depends(auth.get_current_user),
    app_data: str = Form(...),
    bank_statement: UploadFile = File(...)
):
    """
    Creates an application from chatbot data AND a bank statement, then runs an
    immediate, intelligent preliminary prediction.
    """
    try:
        application_in = schemas.CreditApplicationCreate.model_validate(json.loads(app_data))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid application data format.")

    application = crud.create_application(db, application_in, owner_id=current_user.id)
    
    statement_path = f"uploads/app_{application.id}_user_{current_user.id}_statement.pdf"
    with open(statement_path, "wb") as buffer:
        shutil.copyfileobj(bank_statement.file, buffer)
    
    statement_metrics = statement_parser.analyze_bank_statement(statement_path)
    crud.update_application_with_statement_data(db, application.id, statement_path, statement_metrics)
    
    app_with_data = crud.get_application(db, application.id)
    decision, _, _ = ml_model.predict_creditworthiness(app_with_data)
    updated_app = crud.update_preliminary_decision(db, application.id, decision)

    return updated_app

@router.post("/applications/{app_id}/documents")
async def upload_and_verify_documents(
    app_id: int,
    aadhaar_file: UploadFile = File(...),
    salary_slip_file: UploadFile = File(...),
    db: Session = Depends(get_session),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Handles document uploads, OCR, verification, and re-prediction in a single, synchronous,
    and robust transaction. This replaces the old background task system.
    """
    app = crud.get_application(db, app_id)
    if not app or app.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Application not found")

    # 1. Save files to the server
    aadhaar_path = f"uploads/app_{app.id}_user_{current_user.id}_aadhaar.jpg"
    salary_slip_path = f"uploads/app_{app.id}_user_{current_user.id}_salary.pdf"
    try:
        with open(aadhaar_path, "wb") as buffer: shutil.copyfileobj(aadhaar_file.file, buffer)
        with open(salary_slip_path, "wb") as buffer: shutil.copyfileobj(salary_slip_file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save files: {e}")

    # 2. Run OCR on the saved documents
    aadhaar_text = ocr.extract_text_from_image(aadhaar_path)
    salary_text = ocr.extract_text_from_image(salary_slip_path)
    aadhaar_data = ocr.parse_aadhaar_document(aadhaar_text)
    financial_data = ocr.parse_financial_document(salary_text)

    # 3. Verify details by comparing user input with OCR data
    name_match = crud.is_name_match(app.full_name, aadhaar_data.get("name"))
    income_match = False
    if financial_data.get("salary"):
        declared_income = app.monthly_income
        ocr_income = financial_data["salary"]
        if declared_income > 0 and abs(declared_income - ocr_income) / declared_income <= 0.20:
            income_match = True

    # 4. Run the second, more accurate prediction using OCR data
    decision, score, _ = ml_model.predict_creditworthiness(app, use_ocr_data=True, ocr_data=financial_data)
    
    # 5. Update the database with all new information
    crud.update_verified_decision(db, app_id, decision, score, name_match, income_match)
    crud.update_application_docs_and_status(db, app_id, aadhaar_path, salary_slip_path)
    
    # 6. Notify admin that the application is ready for their final decision
    await manager.broadcast(f"Documents for application #{app.id} have been verified and are ready for admin approval.")
    
    return {"message": "Documents uploaded and verified successfully."}

@router.get("/applications/me", response_model=List[schemas.CreditApplicationRead])
def get_my_applications(
    db: Session = Depends(get_session),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Fetches all applications for the currently logged-in user."""
    return crud.get_user_applications(db, user_id=current_user.id)

