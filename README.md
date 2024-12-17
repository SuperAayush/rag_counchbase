## RAG Demo using Couchbase, Streamlit, Langchain, and Gemini Pro

This demo application allows you to converse with your personalized PDF documents by leveraging Couchbase's vector search features to enhance the outcomes from Gemini Pro in a Retrieval-Augmented-Generation (RAG) setup.

### How does it work?

Upload your personalized PDF files and pose inquiries directly via the chat interface.

For every question posed, two types of responses will be provided:

- one derived through RAG 
- one from the standalone LLM - Gemini Pro.

In the RAG process, we utilize Langchain, Couchbase Vector Search, and Gemini Pro to extract segments of the PDF pertinent to your question through Vector search. These segments are then integrated as context for the LLM, which is designed to generate answers using the information from the Vector Store.

### How to Run

- #### Install dependencies

  `pip install -r requirements.txt`

- #### Set the environment secrets

  Set the below in secrets.toml file unser .streamlit folder

  ```
    DB_CONN_STR = "connection_string"
    DB_USERNAME = "username"
    DB_PASSWORD = "password"
    DB_BUCKET = "bucket_name"
    DB_SCOPE = "bucket_scope"
    DB_COLLECTION = "bucket_collection"
    INDEX_NAME = "index_name"
    LOGIN_PASSWORD = "new_password_for_login"
    GOOGLE_API_KEY = "API_Key"
  ```

### With Counchbase

- #### Create the Search Index on Full Text Service

  We need to create the Search Index on the Full Text Service in Couchbase. You can follow the below tutorial to add searchindex.json file in counchbase cluster.
 
  - [Couchbase Capella](https://docs.couchbase.com/cloud/search/import-search-index.html)

  #### Index Definition

  In this instance, we are setting up the `pdf_search` index on the documents located in the docs collection, which is part of the shared scope of the `pdf-docs` bucket. The index configuration specifies the embeddings vector field with 768 dimensions and associates the text field with it. Additionally, all fields contained within metadata are dynamically mapped and indexed to handle different document formats. The chosen method for measuring similarity is the `dot_product`.

- #### Run the application

  `streamlit run main.py`

### Without Councbase

The application without couchbase will only generate one response and with not have vector embedding from couchbase. You can run it using the below commands

Step 1: 
    `pip install -r requirements.txt`

Step 2: 
  `streamlit run main.py`

Step 3: 
Upload a PDF file and ask question related to the PDF