from app.main import app


def main() -> None:
    print("Backend app is available via the 'app' object.")


if __name__ == "__main__":
    # Run with uvicorn for convenience when invoking this file directly
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
