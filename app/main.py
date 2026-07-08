from fastapi import FastAPI
from app.routers import user, search
from app.core.lifespan import lifespan


app = FastAPI(lifespan=lifespan)

app.include_router(search.router)
app.include_router(user.router)
