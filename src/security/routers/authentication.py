from typing import Annotated
from fastapi import APIRouter
from fastapi.security import OAuth2PasswordRequestForm

from security.controllers.authentication import Authentication
from security.model.model import Token, TokenRefresh
from security.service.helpers.rate_limiter import LimiterRequests, RateLimiter
from security.service.helpers.users import *

from utils.commons import route_description
from helpers.printer import PrintHelper

from core.config import ConfigHelper
from utils.handle_exceptions import handle_exceptions_async_method

config = ConfigHelper()
router = APIRouter()

auth = Authentication()

print_ls = PrintHelper('[authentication.routers]',
                       level=config_app.get_internal_log_level())

tag_name = 'Security'
endpoint_limiter = LimiterRequests(printer=print_ls,
                                   tags=tag_name,
                                   default_key='L1')

limiter = endpoint_limiter.get_limiter_cust('token')
route = '/token'


@router.post(path=route,
             tags=[tag_name],
             summary='Release a new token',
             description=route_description(tag=tag_name,
                                           route=route,
                                           limiter_calls=limiter.max_request,
                                           limiter_seconds=limiter.seconds),
             dependencies=[Depends(RateLimiter(interval_seconds=limiter.seconds,
                                               max_requests=limiter.max_request))],
             response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db: Session = Depends(get_db)):
    return await auth.login(form_data.username, form_data.password, db)


limiter_tr = endpoint_limiter.get_limiter_cust('token_refresh')
route = '/token-refresh'


@router.post(path=route,
             tags=[tag_name],
             summary='Refresh the access token',
             description=route_description(tag=tag_name,
                                           route=route,
                                           limiter_calls=limiter_tr.max_request,
                                           limiter_seconds=limiter_tr.seconds),
             dependencies=[Depends(RateLimiter(interval_seconds=limiter_tr.seconds,
                                               max_requests=limiter_tr.max_request))],
             response_model=TokenRefresh)
async def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    return await auth.refresh_login(refresh_token, db)
