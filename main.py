import os
import streamlit as st
from langchain_couchbase import CouchbaseVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import tempfile
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

@st.cache_resource(show_spinner="Connecting to Couchbase")
def connect_to_couchbase(connection_string, db_username, db_password):
    """Connect to couchbase"""
    from couchbase.cluster import Cluster
    from couchbase.auth import PasswordAuthenticator
    from couchbase.options import ClusterOptions
    from datetime import timedelta

    auth = PasswordAuthenticator(db_username, db_password)
    options = ClusterOptions(auth)
    connect_string = connection_string
    cluster = Cluster(connect_string, options)

    cluster.wait_until_ready(timedelta(seconds=5))

    return cluster

@st.cache_resource(show_spinner="Connecting to Vector Store")
def get_vector_store(
    _cluster,
    db_bucket,
    db_scope,
    db_collection,
    _embedding,
    index_name,
):
    """Return the Couchbase vector store"""
    vector_store = CouchbaseVectorStore(
        cluster=_cluster,
        bucket_name=db_bucket,
        scope_name=db_scope,
        collection_name=db_collection,
        embedding=_embedding,
        index_name=index_name,
    )
    return vector_store

def check_environment_variable(variable_name):
    """Check if environment variable is set"""
    if variable_name not in os.environ:
        st.error(
            f"{variable_name} environment variable is not set. Please add it to the secrets.toml file"
        )
        st.stop()

def save_to_vector_store(uploaded_file, vector_store):
    """Chunk the PDF & store it in Couchbase Vector Store"""
    if uploaded_file is not None:
        temp_dir = tempfile.TemporaryDirectory()
        temp_file_path = os.path.join(temp_dir.name, uploaded_file.name)

        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getvalue())
            loader = PyPDFLoader(temp_file_path)
            docs = loader.load()

        vector_store.add_documents(docs)
        st.info(f"PDF loaded into vector store in {len(docs)} documents")

if __name__ == "__main__":

    st.set_page_config(
        page_title="Chat with any PDF uploaded using Couchbase, Langchain & Gemini Pro",
        layout="centered",
        initial_sidebar_state="auto",
        menu_items=None,
    )

    DB_CONN_STR = os.getenv("DB_CONN_STR")
    DB_USERNAME = os.getenv("DB_USERNAME")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_BUCKET = os.getenv("DB_BUCKET")
    DB_SCOPE = os.getenv("DB_SCOPE")
    DB_COLLECTION = os.getenv("DB_COLLECTION")
    INDEX_NAME = os.getenv("INDEX_NAME")

    check_environment_variable("GOOGLE_API_KEY")
    check_environment_variable("DB_CONN_STR")
    check_environment_variable("DB_USERNAME")
    check_environment_variable("DB_PASSWORD")
    check_environment_variable("DB_BUCKET")
    check_environment_variable("DB_SCOPE")
    check_environment_variable("DB_COLLECTION")
    check_environment_variable("INDEX_NAME")

    embedding = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
    )

    cluster = connect_to_couchbase(DB_CONN_STR, DB_USERNAME, DB_PASSWORD)

    vector_store = get_vector_store(
        cluster,
        DB_BUCKET,
        DB_SCOPE,
        DB_COLLECTION,
        embedding,
        INDEX_NAME,
    )

    with st.sidebar:
        st.header("Upload your PDF")
        with st.form("upload pdf"):
            uploaded_file = st.file_uploader(
                "Choose a PDF.",
                help="The document will be deleted after one hour of inactivity (TTL).",
                type="pdf",
            )
            submitted = st.form_submit_button("Upload")
            if submitted:
                save_to_vector_store(uploaded_file, vector_store)

        st.subheader("Workflow of this app")
        st.markdown(
            """
            For each question, you will get two answers: 
            * one using RAG 
            * one using pure LLM
            """
        )

        st.markdown(
            "For RAG, I have used [Langchain](https://langchain.com/), [Couchbase Vector Search](https://couchbase.com/) & [Gemini](https://gemini.google.com/). This app fetch parts of the PDF relevant to the question using Vector search & add it as the context to the LLM. The LLM is instructed to answer based on the context from the Vector Store."
        )

    retriever = vector_store.as_retriever()

    template = """If you are not able to answer based on the context provided, respond with a generic answer. Answer the question using the context below:
    {context}

    Question: {question}"""

    prompt = ChatPromptTemplate.from_template(template)

    llm = GoogleGenerativeAI(
        temperature=0.3,
        model="models/gemini-1.5-pro",
    )

    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    template_without_rag = """Answer the question.

    Question: {question}"""

    prompt_without_rag = ChatPromptTemplate.from_template(template_without_rag)

    llm_without_rag = GoogleGenerativeAI(
        temperature=0,
        model="models/gemini-1.5-pro",
    )

    chain_without_rag = (
        {"question": RunnablePassthrough()}
        | prompt_without_rag
        | llm_without_rag
        | StrOutputParser()
    )

    st.title("Privacera Assignment")
    st.markdown(
        "First generated answer is using *RAG* while second generated answer is purely by *LLM (Gemini)*"
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": "Hi, I'm a chatbot who can chat with the PDF. How can I help you?"
            }
        )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if question := st.chat_input("Ask a question based on the PDF"):
        st.chat_message("user").markdown(question)
        st.session_state.messages.append(
            {"role": "user", "content": question}
        )

        with st.chat_message("assistant"):
            message_placeholder = st.empty()

        rag_response = ""
        for chunk in chain.stream(question):
            rag_response += chunk
            message_placeholder.markdown(rag_response + "▌")

        message_placeholder.markdown(rag_response)
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": rag_response
            }
        )

        with st.chat_message("ai"):
            message_placeholder_pure_llm = st.empty()
        pure_llm_response = ""

        for chunk in chain_without_rag.stream(question):
            pure_llm_response += chunk
            message_placeholder_pure_llm.markdown(pure_llm_response + "▌")

        message_placeholder_pure_llm.markdown(pure_llm_response)
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": pure_llm_response
            }
        )
