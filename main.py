from dotenv import load_dotenv
from web.app import run_app

if __name__ == "__main__":
    load_dotenv("web.env")
    run_app()
