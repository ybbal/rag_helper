import logging
import os
import pathlib

SRC_PATH = pathlib.Path(__file__).resolve().parent.parent
PROJECT_PATH = SRC_PATH.parent
DATA_PATH = PROJECT_PATH / "data"
INSTRUCTIONS_PATH = DATA_PATH / "instr"
TMP_STORAGE_PATH = DATA_PATH / "tmp"
USER_TMP_STORAGE_PATH = TMP_STORAGE_PATH / "user_img_storage"

logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s',
    level=logging.WARN,
    force=True,
    handlers=[
        logging.FileHandler(str(PROJECT_PATH / os.getenv("LOG_PATH")), encoding="UTF-8"),
        logging.StreamHandler()
    ]
)