from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from database import engine, SessionLocal
from datetime import date as Date
import models
from models import Transaction as TransactionModel
from typing import Annotated, Optional, List
from router import auth
from router.auth import get_current_user

app = FastAPI(title="Expense Tracker API")

models.Base.metadata.create_all(bind=engine)
app.include_router(auth.router)

# pydentic schemas
class TransactionCreate(BaseModel):
    title: str = Field(max_length=100)
    amount: float
    type: str
    category: str
    date: Date

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in ["income", "expense"]:
            raise ValueError("Type must be 'income' or 'expense'")
        return v


class TransactionResponse(BaseModel):
    id: int
    title: str
    amount: float
    type: str
    category: str
    date: Date

    class Config:
        from_attributes = True


class TransactionUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    type: Optional[str] = None
    category: Optional[str] = None
    date: Optional[Date] = None
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v
    
    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in ["income", "expense"]:
            raise ValueError("Type must be 'income' or 'expense'")
        return v


# dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


#transaction create
@app.post("/transactions", response_model=TransactionResponse)
def create_transaction(db: db_dependency, user: user_dependency, transaction: TransactionCreate):

    new_transaction = TransactionModel(
        title=transaction.title,
        amount=transaction.amount,
        type=transaction.type,
        category=transaction.category,
        date=transaction.date,
        owner_id=user.get("id")
    )

    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    return new_transaction



# filter transactions
@app.get("/transactions/filter", response_model=List[TransactionResponse])
def filter_transactions(
    db: db_dependency,
    user: user_dependency,
    type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    minimum_amount: Optional[float] = Query(None),
    maximum_amount: Optional[float] = Query(None)
):

    query = db.query(TransactionModel).filter(
        TransactionModel.owner_id == user.get("id")
    )

    if type:
        query = query.filter(TransactionModel.type == type)

    if category:
        query = query.filter(TransactionModel.category == category)

    if minimum_amount:
        query = query.filter(TransactionModel.amount >= minimum_amount)

    if maximum_amount:
        query = query.filter(TransactionModel.amount <= maximum_amount)

    return query.all()



# view transaction by id
@app.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: int, db: db_dependency, user: user_dependency):

    transaction = db.query(TransactionModel).filter(
        TransactionModel.id == transaction_id,
        TransactionModel.owner_id == user.get("id")
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction

# view all transactions
@app.get("/transactions", response_model=List[TransactionResponse])
def get_transactions(db: db_dependency, user: user_dependency):

    return db.query(TransactionModel).filter(
        TransactionModel.owner_id == user.get("id")
    ).all()

# edit transactions
@app.put("/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(transaction_id: int, db: db_dependency, user: user_dependency, update_data: TransactionUpdate):

    transaction = db.query(TransactionModel).filter(
        TransactionModel.id == transaction_id,
        TransactionModel.owner_id == user.get("id")
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    update_dict = update_data.model_dump(exclude_unset=True)

    for key, value in update_dict.items():
        setattr(transaction, key, value)

    db.commit()
    db.refresh(transaction)

    return transaction


# delete transaction
@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, db: db_dependency, user: user_dependency):

    transaction = db.query(TransactionModel).filter(
        TransactionModel.id == transaction_id,
        TransactionModel.owner_id == user.get("id")
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.commit()

    return {"message": "Transaction deleted successfully"}

