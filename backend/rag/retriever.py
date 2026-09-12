from functools import lru_cache

from common.logger import logger
from rag.vector_store import create_vector_store


@lru_cache(maxsize=1)
def get_retriever():

    vector_store = create_vector_store()

    return vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "score_threshold": 0.35,
            "k": 3
        }
    )

if __name__ == "__main__":
    retriever = get_retriever()

    results = retriever.invoke(
        "How should database access be handled in FastAPI?"
    )

    for i, document in enumerate(results):
        logger.info("--- RESULT %s ---", i)
        logger.info(document.page_content)