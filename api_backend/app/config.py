from dotenv import load_dotenv
import os
load_dotenv()

DATABASE_URL    = os.getenv("DATABASE_URL")
JWT_SECRET      = os.getenv("JWT_SECRET")
JWT_ALGORITHM   = os.getenv("JWT_ALGORITHM")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 60))