from fastapi import FastAPI

app = FastAPI(title="Octizen")

@app.get("/")
def root():
    return {
        "name": "Octizen",
        "version": "0.1.0",
        "status": "Running"
    }
