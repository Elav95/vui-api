from fastapi import APIRouter, Depends

from helpers.handle_exceptions import *
from helpers.printer_helper import PrintHelper
from libs.backup import Backup
from fastapi import Request
from libs.security.rate_limiter import RateLimiter, LimiterRequests

router = APIRouter()

backup = Backup()
print_ls = PrintHelper('routes.backup_location_v1')

endpoint_limiter = LimiterRequests(debug=False,
                                   printer=print_ls,
                                   tags='Backup',
                                   default_key='L1')
limiter = endpoint_limiter.get_limiter_cust('backup_get')

tag_name = "Backup"

@router.get('/backup/get',
            tags=[tag_name],
            summary='Get backups list',
            description=f"Rate limiter key: {tag_name}:backup_get",
            dependencies=[Depends(RateLimiter(interval_seconds=limiter.seconds,
                                              max_requests=limiter.max_request))])
@handle_exceptions_async_method
async def backup_get(schedule_name=None, only_last_for_schedule='', in_progress=False):
    return await backup.get(schedule_name=schedule_name,
                            only_last_for_schedule=only_last_for_schedule.lower() == 'true',
                            in_progress=in_progress)


limiter_logs = endpoint_limiter.get_limiter_cust('backup_logs')


@router.get('/backup/logs',
            tags=[tag_name],
            summary='Get backups logs',
            description=f"Rate limiter key: {tag_name}:backup_logs",
            dependencies=[Depends(RateLimiter(interval_seconds=limiter_logs.seconds,
                                              max_requests=limiter_logs.max_request))])
@handle_exceptions_async_method
async def backup_logs(resource_name=None):
    return await backup.logs(resource_name)


limiter_des = endpoint_limiter.get_limiter_cust('backup_describe')


@router.get('/backup/describe',
            tags=[tag_name],
            summary='Get backups detail',
            description=f"Rate limiter key: {tag_name}:backup_describe",
            dependencies=[Depends(RateLimiter(interval_seconds=limiter_des.seconds,
                                              max_requests=limiter_des.max_request))])
@handle_exceptions_async_method
async def backup_describe(resource_name=None):
    return await backup.describe(resource_name)


limiter_del = endpoint_limiter.get_limiter_cust('backup_delete')


@router.get('/backup/delete',
            tags=[tag_name],
            summary='Delete a backup',
            description=f"Rate limiter key: {tag_name}:backup_delete",
            dependencies=[Depends(RateLimiter(interval_seconds=limiter_del.seconds,
                                              max_requests=limiter_del.max_request))])
@handle_exceptions_async_method
async def backup_delete(resource_name=None):
    return await backup.delete(resource_name)


limiter_setting = endpoint_limiter.get_limiter_cust('backup_create_settings')


@router.get('/backup/create/settings',
            tags=[tag_name],
            summary='Create a setting for a backup',
            description=f"Rate limiter key: {tag_name}:backup_create_settings",
            dependencies=[Depends(RateLimiter(interval_seconds=limiter_setting.seconds,
                                              max_requests=limiter_setting.max_request))])
@handle_exceptions_async_method
async def get_settings_create():
    return await backup.get_settings_create()


limiter_create = endpoint_limiter.get_limiter_cust('backup_create')


@router.post('/backup/create',
             tags=[tag_name],
             summary='Create a backup',
             description=f"Rate limiter key: {tag_name}:backup_create",
             dependencies=[Depends(RateLimiter(interval_seconds=limiter_create.seconds,
                                               max_requests=limiter_create.max_request))])
@handle_exceptions_async_method
async def create(info: Request):
    req_info = await info.json()
    return await backup.create(req_info)


limiter_create_from_schedule = endpoint_limiter.get_limiter_cust('backup_crete_from_schedule')


@router.post('/backup/create-from-schedule',
             tags=[tag_name],
             summary='Create a backup from a schedule',
             description=f"Rate limiter key: {tag_name}:backup_create_from_schedule",
             dependencies=[Depends(RateLimiter(interval_seconds=limiter_create_from_schedule.seconds,
                                               max_requests=limiter_create_from_schedule.max_request))])
@handle_exceptions_async_method
async def create_from_schedule(info: Request):
    req_info = await info.json()
    return await backup.create_from_schedule(req_info)


limiter_expiration = endpoint_limiter.get_limiter_cust('backup_get_expiration')


@router.get('/backup/get-expiration',
            tags=['Backup'],
            summary='Get expiration time for a specific backup',
            description=f"Rate limiter key: {tag_name}:backup_get_expiration",
            dependencies=[Depends(RateLimiter(interval_seconds=limiter_expiration.seconds,
                                              max_requests=limiter_expiration.max_request))])
@handle_exceptions_async_method
async def get_expiration(backup_name=None):
    return await backup.get_expiration(backup_name)


limiter_update_expiration = endpoint_limiter.get_limiter_cust('backup_update_expiration')


@router.get('/backup/update-expiration',
            tags=['Backup'],
            summary='Update expiration date for a backup',
            description=f"Rate limiter key: {tag_name}:backup_update_expiration",
            dependencies=[Depends(RateLimiter(interval_seconds=limiter_update_expiration.seconds,
                                              max_requests=limiter_update_expiration.max_request))])
@handle_exceptions_async_method
async def update_expiration(backup_name=None, expiration=None):
    return await backup.update_expiration(backup_name, expiration)


limiter_storage_classes = endpoint_limiter.get_limiter_cust('backup_get_storage_classes')


@router.get('/backup/get-storage-classes',
            tags=['Backup'],
            summary='Get backup storage classes',
            description=f"Rate limiter key: {tag_name}:backup_get_storage_classes",
            dependencies=[Depends(RateLimiter(interval_seconds=limiter_storage_classes.seconds,
                                              max_requests=limiter_storage_classes.max_request))])
@handle_exceptions_async_method
async def get_backup_storage_classes(backup_name=None):
    return await backup.get_backup_storage_classes(backup_name)
