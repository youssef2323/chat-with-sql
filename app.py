import streamlit as st
from pathlib import Path
from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine
import sqlite3
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="LangChain: Chat with SQL DB", page_icon="🦜")
st.title("🦜 LangChain: Chat with SQL DB")

LOCALDB = "USE_LOCALDB"
MYSQL = "USE_MYSQL"

radio_opt = ["Use SQLLite 3 Database-Student", "Connect to your MySQL Database"]

selected_opt = st.sidebar.radio(
    label="Choose the DB which you want to chat", options=radio_opt
)

if radio_opt.index(selected_opt) == 1:
    db_uri = MYSQL
    mysql_host = st.sidebar.text_input("Provide MySQL Host")
    mysql_user = st.sidebar.text_input("MySQL User")
    mysql_password = st.sidebar.text_input("MySQL Password", type="password")
    mysql_db = st.sidebar.text_input("MySQL Database")
    api_key = st.sidebar.text_input(label="Provide Your Groq API Key", type="password")
    if api_key:
        os.environ["GROQ_API_KEY"] = api_key
        st.sidebar.success("API Key Provided Successfully")
    else:
        st.sidebar.error("Please Provide API Key")
else:
    db_uri = LOCALDB
    api_key = st.sidebar.text_input(label="Provide Your Groq API Key", type="password")
    if api_key:
        os.environ["GROQ_API_KEY"] = api_key
        st.sidebar.success("API Key Provided Successfully")
    else:
        st.sidebar.error("Please Provide API Key")
if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
    st.session_state["messages"] = [
        {"role": "assistant", "content": "How can I help you?"}
    ]


groq_key = os.getenv("GROQ_API_KEY", "").strip()
if not groq_key or not groq_key.startswith("gsk_"):
    st.error(
        "Missing or invalid GROQ_API_KEY. Paste a valid Groq key (starts with 'gsk_') in the sidebar or set the env var."
    )
    st.stop()


## LLM model
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, streaming=True)


@st.cache_resource(ttl="2h")
def configure_db(db_uri, **kwargs):
    if db_uri == LOCALDB:
        dbfilepath = (Path(__file__).resolve().parent / "student.db").absolute()
        print(dbfilepath)
        creator = lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro", uri=True)
        return SQLDatabase(create_engine("sqlite:///", creator=creator))
    elif db_uri == MYSQL:
        mysql_user = kwargs.get("mysql_user")
        mysql_password = kwargs.get("mysql_password")
        mysql_db = kwargs.get("mysql_db")
        if not (mysql_user and mysql_password and mysql_db):
            st.error("Please provide all MySQL credentials")
            st.stop()
        return SQLDatabase(
            create_engine(
                f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@localhost/{mysql_db}"
            )
        )


if db_uri == MYSQL:
    db = configure_db(
        db_uri, mysql_user=mysql_user, mysql_password=mysql_password, mysql_db=mysql_db
    )
else:
    db = configure_db(db_uri)

## toolkit
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
## agent
agent = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
)


user_query = st.chat_input(placeholder="Ask anything from the database")
if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        streamlit_callback = StreamlitCallbackHandler(st.container())
        response = agent.run(user_query, callbacks=[streamlit_callback])
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.write(response)
