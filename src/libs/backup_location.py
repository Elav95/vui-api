import json
import os

from fastapi.responses import JSONResponse

from libs.process import *

from helpers.commons import *
from helpers.handle_exceptions import *


class BackupLocation:

    @handle_exceptions_async_method
    async def get(self, json_response=True):
        output = await run_process_check_output(['velero', 'backup-location', 'get', '-o', 'json',
                                                 '-n', os.getenv('K8S_VELERO_NAMESPACE', 'velero')])
        if 'error' in output:
            return output

        backup_location = json.loads(output['data'])

        if backup_location['kind'].lower() == 'backupstoragelocation':
            backup_location = {'items': [backup_location]}

        add_id_to_list(backup_location['items'])

        res = {'data': {'payload': backup_location}}
        if json_response:
            return JSONResponse(content=res, status_code=201, headers={'X-Custom-Header': 'header-value'})
        else:
            return backup_location
