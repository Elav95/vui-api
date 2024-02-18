from fastapi import APIRouter, Depends
from fastapi import Request

from helpers.commons import route_description
from helpers.handle_exceptions import *
from helpers.printer_helper import PrintHelper

from libs.restore import Restore
from libs.security.rate_limiter import RateLimiter, LimiterRequests

router = APIRouter()
restore = Restore()
print_ls = PrintHelper('[routes.restore]')


tag_name = 'Restore'
endpoint_limiter = LimiterRequests(debug=False,
                                   printer=print_ls,
                                   tags=tag_name,
                                   default_key='L1')


limiter = endpoint_limiter.get_limiter_cust("restore_get")
route = '/restore/get'


@router.get(path=route,
            tags=[tag_name],
            summary='Get backups repository',
            description=route_description(tag=tag_name,
                                          route=route,
                                          limiter_calls=limiter.max_request,
                                          limiter_seconds=limiter.seconds),
            dependencies=[Depends(RateLimiter(interval_seconds=limiter.seconds,
                                              max_requests=limiter.max_request))])
@handle_exceptions_async_method
async def restore_get(in_progress=''):
    return await restore.get(in_progress=in_progress.lower() == 'true')


limiter_logs = endpoint_limiter.get_limiter_cust('restore_logs')
route = '/restore/logs'


@router.get(path=route,
            tags=[tag_name],
            summary='Get logs for restore operation',
            description=route_description(tag=tag_name,
                                          route=route,
                                          limiter_calls=limiter_logs.max_request,
                                          limiter_seconds=limiter_logs.seconds),
            dependencies=[Depends(RateLimiter(interval_seconds=limiter_logs.seconds,
                                              max_requests=limiter_logs.max_request))])
@handle_exceptions_async_method
async def restore_logs(resource_name=None):
    return await restore.logs(resource_name)


limiter_des = endpoint_limiter.get_limiter_cust('restore_describe')
route = '/restore/describe'


@router.get(path=route,
            tags=[tag_name],
            summary='Get detail for restore operation',
            description=route_description(tag=tag_name,
                                          route=route,
                                          limiter_calls=limiter_des.max_request,
                                          limiter_seconds=limiter_des.seconds),
            dependencies=[Depends(RateLimiter(interval_seconds=limiter_des.seconds,
                                              max_requests=limiter_des.max_request))])
@handle_exceptions_async_method
async def restore_describe(resource_name=None):
    return await restore.describe(resource_name)


limiter_delete = endpoint_limiter.get_limiter_cust('restore_delete')
route = '/restore/delete'


@router.get(path=route,
            tags=[tag_name],
            summary='Delete restore operation',
            description=route_description(tag=tag_name,
                                          route=route,
                                          limiter_calls=limiter_delete.max_request,
                                          limiter_seconds=limiter_delete.seconds),
            dependencies=[Depends(RateLimiter(interval_seconds=limiter_delete.seconds,
                                              max_requests=limiter_delete.max_request))])
@handle_exceptions_async_method
async def restore_delete(resource_name=None):
    return await restore.delete(resource_name)


limiter_create = endpoint_limiter.get_limiter_cust('restore_create')
route = '/restore/create'


@router.post(path=route,
             tags=[tag_name],
             summary='Create a new restore',
             description=route_description(tag=tag_name,
                                           route=route,
                                           limiter_calls=limiter_create.max_request,
                                           limiter_seconds=limiter_create.seconds),
             dependencies=[Depends(RateLimiter(interval_seconds=limiter_create.seconds,
                                               max_requests=limiter_create.max_request))])
@handle_exceptions_async_method
async def restore_create(info: Request):
    req_info = await info.json()
    return await restore.create(req_info)
