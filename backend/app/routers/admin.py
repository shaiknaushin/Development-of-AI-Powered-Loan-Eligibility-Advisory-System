from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session
from typing import List
import os
import json
from app import models, schemas, auth, crud
from app.database import get_session
from app.websockets import manager
from ml import model as ml_model
from app.pdf_generator import create_report_pdf

router = APIRouter()

@router.get("/applications", response_model=List[schemas.CreditApplicationReadWithOwner])
def get_all_applications(
    db: Session = Depends(get_session),
    current_admin: models.User = Depends(auth.get_current_admin_user)
):
    """Fetches all applications for the admin dashboard."""
    return crud.get_all_applications(db)

@router.post("/applications/{app_id}/approve")
async def approve_application(
    app_id: int,
    db: Session = Depends(get_session),
    current_admin: models.User = Depends(auth.get_current_admin_user)
):
    """Handles the final approval of an application by an admin."""
    app = crud.get_application(db, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    decision, score, reasons = ml_model.predict_creditworthiness(app)
    reasons_str = json.dumps(reasons)
    
    crud.update_final_decision(db, app_id, "Approved", score, reasons_str)
    
    # This is the crucial fix: Re-fetch the application from the database
    # to ensure we have the absolute latest data before generating the PDF.
    app_for_pdf = crud.get_application(db, app_id)
    if not app_for_pdf:
        raise HTTPException(status_code=500, detail="Failed to retrieve application after update.")

    report_path = create_report_pdf(app_for_pdf)
    
    await manager.send_personal_message(
        f"Congratulations! Your application #{app_id} has been approved. You can now download your final report.",
        app.owner_id
    )
    return {"message": "Application approved and report generated."}


@router.post("/applications/{app_id}/reject")
async def reject_application(
    app_id: int,
    db: Session = Depends(get_session),
    current_admin: models.User = Depends(auth.get_current_admin_user)
):
    """Handles the rejection of an application by an admin."""
    app = crud.get_application(db, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    _, score, reasons = ml_model.predict_creditworthiness(app)
    reasons_str = json.dumps(reasons)

    crud.update_final_decision(db, app_id, "Rejected", score, reasons_str)
    
    # Apply the same fix here to ensure the rejection PDF is always correct.
    app_for_pdf = crud.get_application(db, app_id)
    if not app_for_pdf:
        raise HTTPException(status_code=500, detail="Failed to retrieve application after update.")
        
    report_path = create_report_pdf(app_for_pdf)

    await manager.send_personal_message(
        f"We're sorry, but your application #{app_id} has been rejected after a final review.",
        app.owner_id
    )
    return {"message": "Application rejected."}


@router.post("/train-model")
async def train_model_endpoint(
    background_tasks: BackgroundTasks,
    current_admin: models.User = Depends(auth.get_current_admin_user)
):
    """Triggers the AI model re-training process."""
    # This functionality is now handled on server startup, but we keep the endpoint.
    background_tasks.add_task(ml_model.train_and_save_model)
    await manager.broadcast("Admin has initiated a manual model re-training.")
    return {"message": "Model training has been started in the background."}
