from fastapi import FastAPI

app = FastAPI(
    title="Search-Grounded AI Agent Drift Gate",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}
