from fastapi import FastAPI
from routers import user, search


app = FastAPI()


app.include_router(search.router)