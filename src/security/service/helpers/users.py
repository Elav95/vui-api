import re
import uuid
from fastapi import Depends, HTTPException, Request
from jose import jwt, JWTError
from requests import Session
from starlette import status
from security.service.helpers.dependencies import oauth2_scheme
from security.model.model import TokenData, UserOut, UserCreate
from core.config import ConfigHelper
from helpers.printer import PrintHelper

# from sqlalchemy import create_engine, Column, String, Boolean, DateTime as DateTimeA
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.sql import func
# from helpers.database import GUID
from typing import List, Optional
from security.service.helpers.dependencies import pwd_context
from core.context import current_user_var, called_endpoint_var, cp_user
from security.helpers.database import SessionLocal, get_db
from security.helpers.database import User

config_app = ConfigHelper()
print_ls = PrintHelper('[authentication.users]',
                       level=config_app.get_internal_log_level())

disable_password_rate = config_app.get_security_disable_pwd_rate()
secret_access_key = config_app.get_security_access_token_key()
algorithm = config_app.get_security_algorithm()


# path_db = config_app.get_path_db()
#
# # SQLite database initialization
# DATABASE_URL = f"sqlite:///./{path_db}/data.db"
# print_ls.info(f"Users database {DATABASE_URL}")
#
# Base = declarative_base()
#
#
# class User(Base):
#     __tablename__ = 'users'
#     id = Column(GUID(), primary_key=True, default=uuid.uuid4)
#     username = Column(String, unique=True)
#     full_name = Column(String)
#     password = Column(String)
#     is_admin = Column(Boolean, default=False)
#     is_default = Column(Boolean, default=False)
#     is_disabled = Column(Boolean, default=False)
#     time_created = Column(DateTimeA(timezone=True), server_default=func.now())
#     time_updated = Column(DateTimeA(timezone=True), onupdate=func.now())
#
#     def toJSON(self):
#         return {'username': self.username,
#                 'is_admin': self.is_admin,
#                 'is_default': self.is_default,
#                 'is_disabled': self.is_disabled
#                 }
#
#
# engine = create_engine(
#     DATABASE_URL,
#     connect_args={'check_same_thread': False}
# )
#
# Base.metadata.create_all(bind=engine)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#
#
# # User CRUD operations
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def rate_password_strength(password):
    if disable_password_rate:
        return 'NoCheck'
    else:
        # Define a dictionary of regex patterns and their corresponding complexity scores
        complexity_patterns = {
            r".{8,}": 1,  # Minimum length of 8 characters
            r"(?=.*\d)": 1,  # At least one digit
            r"(?=.*[a-z])": 1,  # At least one lowercase letter
            r"(?=.*[A-Z])": 1,  # At least one uppercase letter
            r"(?=.*[!@#$%^&*()\-_=+{};:,<.>])": 1  # At least one special character
        }

        complexity_score = 0

        # Check each complexity pattern against the password
        for pattern, score in complexity_patterns.items():
            if re.search(pattern, password):
                complexity_score += score

        # Rate the password based on the complexity score
        if complexity_score <= 1:
            return 'Weak'
        elif complexity_score <= 3:
            return 'Medium'
        else:
            return 'Strong'


def control_data(user_id: uuid.UUID = None,
                 username: str = '',
                 password: str = '',
                 db: SessionLocal = None):
    # password rate
    if rate_password_strength(password) == 'Weak':
        raise HTTPException(status_code=403, detail='The password is weak')
    if len(username) > 0:
        if user_id is not None:
            # unique username
            user = db.query(User).filter(User.username == username).first()
        else:
            user = db.query(User).filter(User.id != user_id, User.username == username).first()

        if user:
            raise HTTPException(status_code=403, detail='The username is not unique')

    if user_id is not None:
        hashed_password = hash_password(password)
        # print(f"user_id={user_id}-pwd={password}-hash={hashed_password}")
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            res = verify_password(plain_password=password,
                                  hashed_password=user.password)
            if res:
                raise HTTPException(status_code=403, detail={
                    'error': {'title': 'Forbidden', 'description': 'The old password is equal to the new password'}})
        else:
            raise HTTPException(status_code=403, detail='The user is deleted')
    return True


def create_user(user: UserCreate, db: SessionLocal) -> UserOut:
    if control_data(user_id=None,
                    username=user.username,
                    password=user.password,
                    db=db):
        hashed_password = hash_password(user.password)
        db_user = User(username=user.username,
                       full_name=user.full_name,
                       password=hashed_password,
                       is_admin=user.is_admin)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user


def get_user(user_id: uuid.UUID, db: SessionLocal) -> Optional[UserOut]:
    user = db.query(User).filter(User.id == user_id, User.is_disabled == False).first()  # Filters out disabled users
    if user:
        return user
    return None


# def get_user_by_name(username: str, db: SessionLocal = Depends(get_db)) -> Optional[UserOut]:
def get_user_by_name(username: str, db: SessionLocal) -> Optional[User]:
    return db.query(User).filter(User.username == username, User.is_disabled == False).first()


def get_all_users(db: SessionLocal) -> List[UserOut]:
    return db.query(User).all()


def delete_user(user_id: uuid.UUID, db: SessionLocal):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        if db_user.is_default:
            raise HTTPException(status_code=403, detail='Cannot delete the default user')
        db.delete(db_user)
        db.commit()
        return {"message": 'User deleted successfully'}
    else:
        raise HTTPException(status_code=404, detail='User not found')


def create_default_user(db: SessionLocal):
    print("INFO:     create_default_user.check")
    default_username = config_app.get_default_admin_username()
    default_user = db.query(User).filter(User.username == default_username).first()
    if default_user is None:
        print("INFO:     create_default_user.forced")
        default_password = config_app.get_default_admin_password()
        hashed_default_password = hash_password(default_password)
        new_default_user = User(username=default_username,
                                full_name='administrator',
                                password=hashed_default_password,
                                is_default=True,
                                is_admin=True,
                                is_disabled=False)
        db.add(new_default_user)
        db.commit()


def disable_user(user_id: uuid.UUID, db: SessionLocal):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        if db_user.is_default:
            raise HTTPException(status_code=403, detail='Cannot disable the default user')
        db_user.is_disabled = True
        db.commit()
        return {'message': 'User disabled successfully'}
    else:
        raise HTTPException(status_code=404, detail='User not found')


def update_user(user_id: uuid.UUID, full_name: str, password: str, db: SessionLocal):
    if control_data(user_id=user_id,
                    username='',
                    password=password,
                    db=db):
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            if len(full_name) > 0:
                db_user.full_name = full_name
            db_user.password = hash_password(password)

            db.commit()
            return {'messages': [{'title': 'Update Password', 'description': 'User updates successfully!'}]}
        else:
            raise HTTPException(status_code=404, detail='User not found')


def authenticate_user(db, username: str, password: str):
    user = get_user_by_name(username, db)
    if not user:
        print_ls.info(f"Login denied for :{username}")
        return False
    res = verify_password(plain_password=password,
                          hashed_password=user.password)
    if not res:
        print_ls.info(f"Access failed for :{username}")
        return False
    print_ls.info(f"Login in :{username}")
    return user


# LS 2024.03.18 moved in tokens.py script
# def create_access_token(data: dict, expires_delta: timedelta | None = None):
#     to_encode = data.copy()
#     if expires_delta:
#         expire = datetime.utcnow() + expires_delta
#     else:
#         expire = datetime.utcnow() + timedelta(minutes=2)
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, secret_access_key, algorithm=algorithm)
#
#     return encoded_jwt
#

async def get_current_user(request: Request, token: str = Depends(oauth2_scheme),
                           db: Session = Depends(get_db)) -> UserOut:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = jwt.decode(token, secret_access_key, algorithms=[algorithm])
        username: str = payload.get('sub')
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    # for nats user
    if payload.get('is_nats'):
        user = User()
        user.username = "nats"
        user.is_nats = True
        user.cp_mapping_user = request.headers.get('cp_user')
        return user

    user = get_user_by_name(db=db,
                            username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(request: Request, current_user: User = Depends(get_current_user)):
    if current_user.is_disabled:
        raise HTTPException(status_code=400, detail='Inactive user')
    cu = current_user_var.set(current_user)
    if current_user.is_nats:
        cp_user.set(request.headers.get('cp_user'))
    # return current_user
    try:
        yield current_user
    finally:
        if called_endpoint_var.get() != '/api/v1/stats/in-progress':
            print_ls.debug(
                f"Reset context current user {str(current_user_var.get().username)} endpoint: {called_endpoint_var.get()}")
        current_user_var.reset(cu)


async def get_current_user_token(token: str = Depends(oauth2_scheme)) -> UserOut:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = jwt.decode(token, secret_access_key, algorithms=[algorithm])
        username: str = payload.get('sub')
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = get_user_by_name(db=SessionLocal(),
                            username=token_data.username)
    if user is None:
        raise credentials_exception
    return user
