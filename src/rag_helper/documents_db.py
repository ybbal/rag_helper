import pathlib
import re
from logging import getLogger

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders.directory import DirectoryLoader
from langchain_community.vectorstores.faiss import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

from rag_helper import DATA_PATH, EXTRACTED_IMAGES_PATH
from rag_helper.docx_loader import DocxByHeadingLoader

_logger = getLogger(__name__)
# _logger.setLevel(INFO)

_DOC_PATH = str(DATA_PATH / "rag_data")
_MAX_CHUNK_SIZE = 1400
_CHUNK_OVERLAP = 70
_TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=_MAX_CHUNK_SIZE,
    chunk_overlap=_CHUNK_OVERLAP,
    separators=["\n\n\n", "\n\n", "\n"],
    keep_separator=False, is_separator_regex=False
)


def _get_docs(doc_path: str) -> list[Document]:
    loaders: list[DirectoryLoader] = [
        DirectoryLoader(doc_path, glob="**/[!.~]*.doc*", loader_cls=DocxByHeadingLoader,
                        loader_kwargs={'images_output_dir': EXTRACTED_IMAGES_PATH}),
        # DirectoryLoader(doc_path, glob="**/*.txt", loader_cls=TextLoader,
        #                 loader_kwargs={'autodetect_encoding': True}),
        # DirectoryLoader(doc_path, glob="**/*.json", loader_cls=TextLoader,
        #                 loader_kwargs={'autodetect_encoding': False}),
        # DirectoryLoader(doc_path, glob="**/*.pdf", loader_cls=PyPDFLoader,
        #                 loader_kwargs={'extract_images': False}),
        # DirectoryLoader(doc_path, glob="**/*.html", loader_cls=BSHTMLLoader,
        #                 loader_kwargs={'bs_kwargs': {"features": "html.parser"}}),
    ]

    documents: list[Document] = []
    for loader in loaders:
        docs = loader.load()
        # print(*docs, sep="\n\n")
        docs = [doc.model_copy(update={"page_content": _trim_document_content(doc.page_content)}) for doc in docs]
        # print(*docs, sep="\n\n")
        docs = _TEXT_SPLITTER.split_documents(docs)
        docs = [
            doc.model_copy(update={"page_content": _update_chunk_content_by_file_name(doc.page_content, doc.metadata)})
            for doc in docs
        ]
        documents += docs

    # print(*documents, sep="\n\n")
    return documents


def _trim_document_content(content: str):
    res = re.sub(r"\n{1,2}", "\n", content)
    res = re.sub(r"\n{3,}", "\n\n", res)
    res = re.sub(r"(\n+\t+){2,}", "\n\n\n", res)
    res = re.sub(r"\t+", " ", res)
    return res


def _update_chunk_content_by_file_name(content: str, metadata: dict):
    res = re.sub(r"\n{2,}", "\n", content)
    file_name = metadata["source"]
    return pathlib.Path(file_name).stem + "\n" + res


def load_vector_store(embeddings: Embeddings) -> VectorStore:
    _logger.info("Загрузка документов из %s", _DOC_PATH)
    documents = _get_docs(_DOC_PATH)
    _logger.info("Получили документов: %s", len(documents))
    db = FAISS.from_documents(
        documents,
        embeddings,
    )
    return db
