import os
from fastapi.responses import JSONResponse

from utils.handle_exceptions import handle_exceptions_controller
from core.config import ConfigHelper

from api.common.response_model.successful_request import SuccessfulRequest
from api.common.response_model.failed_request import FailedRequest

from service.watchdog_service import WatchdogService

watchdog = WatchdogService()
config_app = ConfigHelper()

class Watchdog:

    @handle_exceptions_controller
    async def version(self):
        payload = await watchdog.version()

        if not payload['success']:
            response = FailedRequest(**payload['error'])
            return JSONResponse(content=response.toJSON(), status_code=400)

        response = SuccessfulRequest(payload=payload['data'])
        return JSONResponse(content=response.toJSON(), status_code=200)

    @handle_exceptions_controller
    async def send_report(self):
        payload = await watchdog.send_report()

        if not payload['success']:
            response = FailedRequest(**payload['error'])
            return JSONResponse(content=response.toJSON(), status_code=400)

        response = SuccessfulRequest(payload=payload['data'])
        return JSONResponse(content=response.toJSON(), status_code=200)

    @handle_exceptions_controller
    async def get_env(self):

        payload = await watchdog.get_env_variables()

        response = SuccessfulRequest(payload=payload['data'])
        return JSONResponse(content=response.toJSON(), status_code=200)

    @handle_exceptions_controller
    async def get_cron(self):

        payload = await watchdog.get_cron(job_name=config_app.get_cronjob_name())

        if not payload['success']:
            response = FailedRequest(**payload['error'])
            return JSONResponse(content=response.toJSON(), status_code=400)

        response = SuccessfulRequest(payload=payload['data'])
        return JSONResponse(content=response.toJSON(), status_code=200)

    @handle_exceptions_controller
    async def send_test_notification(self,
                                     email: bool = True,
                                     telegram: bool = True,
                                     slack: bool = True):
        payload = await watchdog.send_test_notification(email, telegram, slack)

        if not payload['success']:
            response = FailedRequest(**payload['error'])
            return JSONResponse(content=response.toJSON(), status_code=400)

        response = SuccessfulRequest(payload=payload['data'])
        return JSONResponse(content=response.toJSON(), status_code=200)
