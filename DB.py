from langchain_community.vectorstores import Chroma
from langchain_mistralai import MistralAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

from langchain_core.documents import Document

docs = [
    Document(
        page_content="This is a sample comment.",
        metadata={"source": "AI_book"}
    ),
    Document(
        page_content="Artificial Intelligence is transforming modern software systems.",
        metadata={"source": "DataScience_book"}
    ),
    Document(
        page_content="Machine learning models help automate repetitive tasks.",
        metadata={"source": "DL_book"}
    )
]
embedding_model = MistralAIEmbeddings()

vector_store = Chroma.from_documents(
    documents=docs,
    embedding=embedding_model,
    collection_name="sample_collection",
    persist_directory="chroms-db"
)

result = vector_store.similarity_search("what is AI?", k=2)

for r in result:
    print(r.page_content)
    print(r.metadata)

retriver = vector_store.as_retriever()

docs = retriver.invoke("Explain Machine learning?")

for d in docs:
    print(d.page_content)
