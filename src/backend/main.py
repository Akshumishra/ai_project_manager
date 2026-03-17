import logging
import uvicorn

def configure_logging():
    """Set up structured console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def main():
    configure_logging()

    # Import and forward to your FastAPI workspace app
    print("\nStarting API server on 127.0.0.1:8000")
    print("Documentation: http://127.0.0.1:8000/docs\n")

    # Use string-based reload bind addressing so reload watches your workspace recursively!
    uvicorn.run(
        "src.backend.meeting_bot.api.app:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True
    )

if __name__ == "__main__":
    main()
