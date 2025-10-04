import logging
import pathlib

from langchain.globals import set_verbose

VERBOSE: bool = False

set_verbose(VERBOSE)
logging.basicConfig()
if VERBOSE:
    logging.getLogger("langchain.retrievers.multi_query").setLevel(logging.INFO)
    logging.getLogger("langchain_community.chat_models.gigachat").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.INFO)


SRC_PATH = pathlib.Path(__file__).resolve().parent.parent
PROJECT_PATH = SRC_PATH.parent
DATA_PATH = PROJECT_PATH / "data"
