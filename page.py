from langchain_community.document_loaders import WebBaseLoader

url = "https://www.apple.com/in-edu/shop/buy-mac"

data = WebBaseLoader(url)

docs = data.load()

print(docs[0].page_content)
