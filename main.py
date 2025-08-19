from fastapi import FastAPI, Depends, HTTPException


app = FastAPI()


@app.get('/')
def hello_word():
    return {'Hello': 'World'}


