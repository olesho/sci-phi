from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain_community.cache import SQLiteCache
from langchain.globals import set_llm_cache
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
import langchain
from dotenv import load_dotenv
import os
import getpass

question_list = [
    "What is the problem solved by this paper?",
    "What is the main contribution of this paper?",
    "What is the main idea of this paper?",
    "What is the main result of this paper?",
    "What is the main conclusion of this paper?",
    "What is the main future work of this paper?",
    "What is the main limitation of this paper?",
    "What is the main advantage of this paper?",
    "What is the main disadvantage of this paper?",
    "What is the main application of this paper?",
]

# Load environment variables from .env file
load_dotenv()

# if "GROQ_API_KEY" not in os.environ:
#     os.environ["GROQ_API_KEY"] = getpass.getpass("Enter your Groq API key: ")

# Initialize the cache with SQLite
set_llm_cache(SQLiteCache(database_path=".langchain.db"))

prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert in scientific paper analysis. "
            "You are given a specific question regarding a provided scientific paper. "
            "You need to answer the question based on the provided paper. Please provide a concise answer."
        ),
        # Please see the how-to about improving performance with
        # reference examples.
        # MessagesPlaceholder('examples'),
        ("human", "Paper: {text} \nQuestion: {question}"),
    ]
)

def clean_think_tags(output: str) -> str:
    import re
    return re.sub(r"<think>.*?</think>", "", output, flags=re.DOTALL)


def question_paper(text: str, question: str, model: str = "qwen3:14b") -> str:
    # llm = ChatOllama(model="llama3-chatqa:8b", temperature=0.0)
    llm = ChatOllama(model=model, temperature=0.0)
    # llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0)  # Uncomment to use Groq
    # llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    prompt = prompt_template.invoke({"text": text, "question": question})
    results = llm.invoke(prompt)
    # print(clean_think_tags(results.content))
    return clean_think_tags(results.content)
    

if __name__ == "__main__":
    question_paper("fastapi_app/llm/paper.txt", "What is the main contribution of this paper?")