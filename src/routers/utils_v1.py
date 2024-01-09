from fastapi import APIRouter, Depends
from helpers.handle_exceptions import *
from helpers.printer_helper import PrintHelper
from libs.k8s_v1 import K8sV1
from libs.security.rate_limiter import RateLimiter, LimiterRequests
from libs.utils_v1 import UtilsV1
from datetime import datetime

router = APIRouter()
rate_limiter = RateLimiter()

utils = UtilsV1()
k8s = K8sV1()

print_ls = PrintHelper('routes.utils_v1')

endpoint_limiter = LimiterRequests(debug=False,
                                   printer=print_ls,
                                   tags="Statistics",
                                   default_key='L1')
limiter = endpoint_limiter.get_limiter_cust("utilis_stats")


@router.get('/utils/stats',
            tags=["Statistics"],
            summary="Get backups repository",
            dependencies=[Depends(RateLimiter(interval_seconds=limiter.seconds,
                                              max_requests=limiter.max_request))])
@handle_exceptions_async_method
async def stats():
    return await utils.stats()


limiter_v = endpoint_limiter.get_limiter_cust("utilis_version")


@router.get('/utils/version',
            tags=["Statistics"],
            summary="Get velero client version",
            dependencies=[Depends(RateLimiter(interval_seconds=limiter_v.seconds,
                                              max_requests=limiter_v.max_request))])
@handle_exceptions_async_method
async def version():
    return await utils.version()


limiter_inprog = endpoint_limiter.get_limiter_cust("utilis_in_progress")


@router.get('/utils/in-progress',
            tags=["Statistics"],
            summary="Get operations in progress",
            dependencies=[Depends(RateLimiter(interval_seconds=limiter_inprog.seconds,
                                              max_requests=limiter_inprog.max_request))])
@handle_exceptions_async_method
async def in_progress():
    return await utils.in_progress()


endpoint_limiter_st = LimiterRequests(debug=False,
                                      printer=print_ls,
                                      tags="Status",
                                      default_key='L1')
limiter_status = endpoint_limiter.get_limiter_cust("utilis_status")


@router.get('/utils/health',
            tags=["Status"],
            summary="UTC time",
            dependencies=[Depends(RateLimiter(interval_seconds=limiter_status.seconds,
                                              max_requests=limiter_status.max_request))])
@handle_exceptions_async_method
async def health():
    return {'timestamp': datetime.utcnow()}


@router.get('/utils/health_k8s',
            tags=["Status"],
            summary="Get K8s connection an api status",
            dependencies=[Depends(RateLimiter(interval_seconds=limiter_status.seconds,
                                              max_requests=limiter_status.max_request))])
@handle_exceptions_async_method
async def k8s_nodes_status():
    return await k8s.get_k8s_online()
