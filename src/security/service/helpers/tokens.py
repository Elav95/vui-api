import uuid

from jose import jwt, JWTError
from starlette import status
from starlette.responses import Response
from typing import List, Optional
from core.config import ConfigHelper

from datetime import timedelta, datetime

from security.helpers.database import SessionLocal
from security.helpers.database import RefreshToken

from helpers.logger import ColoredLogger, LEVEL_MAPPING
import logging

config_app = ConfigHelper()
logger = ColoredLogger.get_logger(__name__, level=LEVEL_MAPPING.get(config_app.get_internal_log_level(), logging.INFO))

token_access_expire = config_app.get_security_token_expiration()
token_refresh_expires_days = config_app.get_security_token_refresh_expiration()

secret_access_key = config_app.get_security_access_token_key()
secret_refresh_key = config_app.get_security_refresh_token_key()

algorithm = config_app.get_security_algorithm()


def __get_refresh_token_by_user(token: str,
                                user_id: uuid.UUID,
                                db: SessionLocal) -> Optional[RefreshToken]:
    logger.debug(f"__get_refresh_token_by_user")
    data = db.query(RefreshToken).filter(RefreshToken.token == token,
                                         RefreshToken.user_id == user_id).first()
    if data:
        return data
    return None


def __delete_user_token(user_id: uuid.UUID,
                        db: SessionLocal):
    logger.debug(f"__delete_user_token")

    db_token = db.query(RefreshToken).filter(RefreshToken.user_id == user_id).first()
    if db_token:
        db.delete(db_token)
        db.commit()
        return True
    return False


def _add_user_token(token: str,
                    user_id: uuid.UUID,
                    db: SessionLocal):
    logger.debug(f"_add_user_token")
    new_token = RefreshToken(user_id=user_id,
                             token=token)
    db.add(new_token)
    db.commit()
    return True


def check_refresh_token_in_db(refresh_token: str,
                              user_id: uuid.UUID,
                              db: SessionLocal):
    logger.debug(f"check_refresh_token_in_db {user_id}")
    ret = False
    if refresh_token is not None:
        data = __get_refresh_token_by_user(token=refresh_token,
                                           user_id=user_id,
                                           db=db)
        if data is not None:
            ret = True
        else:
            logger.warning(f"check auth refresh token: "
                           f"user has another token in db {refresh_token[:4]}")

    if not ret:
        logger.warning(f"check auth refresh token: not in db")
        return Response("Could not validate refresh token",
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        headers={'WWW-Authenticate': 'Bearer'})

    logger.debug(f"check auth refresh token: accepted")
    return ret


def add_refresh_token(refresh_token: str,
                      user_id: uuid.UUID,
                      db: SessionLocal):
    logger.debug(f"add_refresh_token")
    res = __delete_user_token(user_id=user_id,
                              db=db)
    logger.debug(f"add_refresh_token.delete old token: {res}")

    _add_user_token(token=refresh_token,
                    user_id=user_id,
                    db=db)


def create_access_token(data: dict, expires_delta: timedelta = None):
    logger.debug(f"create_access_token")
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    # LS 2024.12.12 check token key
    # encoded_jwt = jwt.encode(to_encode, secret_access_key, algorithm=algorithm)
    access_key = config_app.get_security_access_token_key()
    encoded_jwt = jwt.encode(to_encode, access_key, algorithm=algorithm)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta = None):
    logger.debug(f"create_refresh_token")
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)

    to_encode.update({"exp": expire})
    # LS 2024.12.12 check refresh key token
    # encoded_jwt = jwt.encode(to_encode, secret_refresh_key, algorithm=algorithm)
    refresh_key = config_app.get_security_refresh_token_key()
    encoded_jwt = jwt.encode(to_encode, refresh_key, algorithm=algorithm)
    return encoded_jwt


def verify_refresh_token(token: str):
    logger.debug(f"verify_refresh_token")
    try:
        username = ''
        # LS 2024.12.12 check refresh token
        # payload = jwt.decode(token, secret_refresh_key, algorithms=[algorithm])
        refresh_key = config_app.get_security_refresh_token_key()
        payload = jwt.decode(token, refresh_key, algorithms=[algorithm])

        if payload is not None:
            logger.debug(f"verify_refresh_token: {payload}")
            username: str = payload.get("sub")
            if username is None:
                return Response("Could not validate request-user",
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                headers={'WWW-Authenticate': 'Bearer'})

        return username
    except JWTError as jwe:
        logger.warning(f"verify_refresh_token {jwe}")
        return Response("Could not validate request",
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        headers={'WWW-Authenticate': 'Bearer'})
