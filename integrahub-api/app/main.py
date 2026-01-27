from fastapi import FastAPI

app = FastAPI(title="IntegraHub API")

@app.get("/health")
def health():
    return {"status": "ok"}
