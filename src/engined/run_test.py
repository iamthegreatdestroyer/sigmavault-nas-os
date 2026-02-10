import traceback

import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

if __name__ == "__main__":
    try:
        print("Starting server...")
        uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")
    except Exception as e:
        print(f"Exception: {e}")
        traceback.print_exc()
