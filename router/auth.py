from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone
from typing import Annotated, Optional
from database import SessionLocal
from models import Users
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError

router = APIRouter(prefix="/auth", tags=["Authentication"])

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
OAuth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/login")

SECRET_KEY = 'your-secret-key'
ALGORITHM = 'HS256'


#schemas
class CreateUsers(BaseModel):
    email: EmailStr
    username: str
    firstname: str
    lastname: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr

    class Config:
        from_attributes = True


class UpdateUser(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None


class UpdatePassword(BaseModel):
    current_password: str
    new_password: str



#authentucation
def authenticate_user(username: str, password: str, db: Session):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        return False

    if not bcrypt_context.verify(password, user.hashed_password):
        return False

    return user


def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: Annotated[str, Depends(OAuth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_id: int = payload.get('id')

        if username is None or user_id is None:
            raise HTTPException(status_code=401, detail='User not found')

        return {'username': username, 'id': user_id}

    except JWTError:
        raise HTTPException(status_code=401, detail='Invalid token')


# dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

#user register
@router.post('/register', response_model=UserResponse)
def register_user(db: db_dependency, new_user: CreateUsers):

    existing_user = db.query(Users).filter(Users.username == new_user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail='User already exists')

    user_model = Users(
        email=new_user.email,
        username=new_user.username,
        firstname=new_user.firstname,
        lastname=new_user.lastname,
        hashed_password=bcrypt_context.hash(new_user.password),
    )

    db.add(user_model)
    db.commit()
    db.refresh(user_model)

    return user_model


#user login
@router.post('/login')
def login_user(db: db_dependency, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):

    user = authenticate_user(form_data.username, form_data.password, db)

    if not user:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    token = create_access_token(user.username, user.id, timedelta(minutes=30))

    return {'access_token': token, 'token_type': 'bearer'}


# user update
@router.put('/edituser')
def update_user(user: user_dependency, db: db_dependency, update_user: UpdateUser):

    db_user = db.query(Users).filter(Users.id == user.get('id')).first()

    update_data = update_user.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()

    return {"message": "User updated successfully"}


# change password user
@router.put('/passwordchange')
def update_password(user: user_dependency, db: db_dependency, update_password: UpdatePassword):

    db_user = db.query(Users).filter(Users.id == user.get('id')).first()

    if not bcrypt_context.verify(update_password.current_password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail='Wrong Password')

    db_user.hashed_password = bcrypt_context.hash(update_password.new_password)

    db.commit()

    return {"message": "Password updated successfully"}