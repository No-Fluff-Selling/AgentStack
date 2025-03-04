from setuptools import setup, find_packages

setup(
    name="b2b_researcher",
    version="0.1.0",
    packages=find_packages(include=['b2b_researcher', 'b2b_researcher.*']),
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "pydantic>=2.4.2",
        "aiohttp>=3.9.0",
        "python-dotenv>=1.0.0",
        "langgraph>=0.2.69",
        "langchain>=0.1.0",
        "langchain-openai>=0.0.2",
        "langchain-community>=0.0.10",
        "faiss-cpu>=1.7.4",
        "typing-extensions>=4.8.0",
        "python-dateutil>=2.8.2",
        "requests>=2.31.0",
        "websockets>=12.0",
        "beautifulsoup4>=4.12.0",
    ],
    python_requires=">=3.11",
)
