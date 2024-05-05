from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from helpers.connection_manager import WebSocket, manager

from core.config import ConfigHelper
from core.context import called_endpoint_var
from security.helpers.database import SessionLocal

from security.service.helpers.middleware import add_process_time_header
from security.service.helpers.users import create_default_user


from api.common.app_info import appInfo
from api.v1.api_v1 import v1

from app_data import __version__, __app_name__, __app_description__, __app_summary__

load_dotenv()
config = ConfigHelper()


# init logger engine
# print_helper = PrintHelper('[app]')

# docs redocs
# docs_url = '/docs'
# re_docs_url = '/redoc'
# enabled_docs = config.get_api_disable_documentation()
# if not enabled_docs:
#    docs_url = None
#    re_docs_url = None

#
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#
#     db = SessionLocal()
#     try:
#         print("Force creation default user")
#         # Create default db
#         create_default_user(db)
#         yield db
#
#     finally:
#         db.close()
#     yield


app = FastAPI(
    title=__app_name__,
    description=__app_description__,
    summary=__app_summary__,
    version=__version__,
    license_info={
        'name': 'Apache 2.0',
        'identifier': 'Apache-2.0',
    },
    # docs_url=docs_url,
    # redoc_url=re_docs_url,
    # lifespan=lifespan
)

origins = config.get_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=["X-Process-Time"]
)

app.middleware('http')(add_process_time_header)


@app.middleware("http")
async def set_called_endpoint(request: Request, call_next):
    # get the endpoint called by the request
    called_endpoint = request.url.path
    # set the endpoint called in the context variable
    ce = called_endpoint_var.set(called_endpoint)
    try:
        # call the next endpoint in the application
        return await call_next(request)
    finally:
        called_endpoint_var.reset(ce)


@app.get('/api')
async def online():
    return JSONResponse(content={'status': 'alive'}, status_code=200)


# @app.websocket("/ws",
#                dependencies=[Depends(get_current_active_user)])
# Can't use jwt in socket header request
@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # await manager.send_personal_message('Connection READY!', websocket=websocket)


app.mount("/api/v1", v1, "v1")
app.mount("/api/info", appInfo, "appInfo")
