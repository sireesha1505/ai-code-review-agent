from pathlib import Path

from langchain_core.documents import Document


DOCUMENT_PATH = (
    Path(__file__).parent
    / "documents"
    / "coding_guidelines.md"
)


def load_local_guidelines():
    text = DOCUMENT_PATH.read_text(
        encoding="utf-8"
    )

    return [
        {
            "path": "coding_guidelines.md",
            "content": text
        }
    ]


def get_rag_documents(fetched_documents):

    valid_documents = [
        document
        for document in fetched_documents
        if document.get("content", "").strip()
    ]

    if valid_documents:
        return valid_documents

    return load_local_guidelines()


def split_documents(documents):
    langchain_documents = []

    for document in documents:

        content = document["content"]

        sections = content.split("\n## ")

        for index, section in enumerate(sections):

            if not section.strip():
                continue

            if index == 0:
                title = "Repository Overview"
                section_content = section.strip()
            else:
                lines = section.split("\n", 1)

                title = lines[0].strip()

                section_content = (
                    lines[1].strip()
                    if len(lines) > 1
                    else ""
                )

            enriched_content = (
                f"Section: {title}\n\n"
                f"{section_content}"
            )

            langchain_documents.append(
                Document(
                    page_content=enriched_content,
                    metadata={
                        "source": document["path"],
                        "section": title,
                    }
                )
            )

    return langchain_documents