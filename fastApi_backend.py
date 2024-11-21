from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import openai
from dotenv import load_dotenv
import os
import logging
import redis

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI app
app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with specific origins if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
cache = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

# Constants
INDEX_FILE = "data/arbor_faiss.index"
METADATA_FILE = "data/arbor_metadata.json"

# Load FAISS index and metadata
try:
    index = faiss.read_index(INDEX_FILE)
    with open(METADATA_FILE, "r") as f:
        metadata = json.load(f)
except Exception as e:
    logger.error(f"Error loading FAISS index or metadata: {e}")
    metadata = []
    index = None

# Load embedding model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


def improve_query(query: str) -> str:
    """
    Use GPT-3.5/4 to improve the user's query by adding context or clarification.
    """
    try:
        prompt = (
            f"Improve the following query by adding context, clarification, or relevant details based on the document "
            f"which contains construction equipment information (section can be product_catalog, technical_details, "
            f"price_history, and material alternatives, etc.) to make it more precise for RAG Application:\n\n"
            f"Original Query: {query}\n\n"
            f"Improved Query:"
        )
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that improves user queries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.3
        )
        improved_query = response['choices'][0]['message']['content'].strip()
        logger.info(f"Improved Query: {improved_query}")
        return query
    except Exception as e:
        logger.error(f"Error improving query: {e}")
        return query  # Fallback to original query if improvement fails


def get_top_k_documents(query: str, k: int):
    """
    Get the top K documents from FAISS index based on the query.
    """
    try:
        query_embedding = embedding_model.encode(query).reshape(1, -1).astype('float32')
        distances, indices = index.search(query_embedding, k)
        top_documents = [metadata[idx] for idx in indices[0] if 0 <= idx < len(metadata)]
        return top_documents
    except Exception as e:
        logger.error(f"Error during FAISS search: {e}")
        return []


def extract_response_components(query: str, documents: list):
    """
    Use GPT-3.5-turbo to extract structured response components from the documents.
    """
    necc_docs = "\n\n".join([json.dumps(doc) for doc in documents])
    prompt = (
        f"You are a helpful assistant for answering structured queries. Always respond with pure JSON only, without any additional formatting such as Markdown or enclosing your output in backticks.\n\n"
        f"If the {query} wants an alternative or other options for something, then make sure to look at material_alternatives section.\n\n"
        f"Given the following query and context, provide a structured response with these components:\n\n"
        f"Query: {query}\n\n"
        f"Context:\n{necc_docs}\n\n"
        f"Please provide:\n"
        f"1. Brief context summary (~6 words without using the word 'context')\n"
        f"2. List of relevant product IDs mentioned in the Context which you think are relevant to the query\n"
        f"3. List of relevant document IDs in the Context, ensuring no overlap with product IDs\n"
        f"4. 4 key points as bullet points\n"
        f"5. A concise answer to the {query} based on the information in the above points. Make sure it is plain text and not json or any other format.\n"
        f"Format the response as JSON with keys: context, relevant_products, relevant_documents, key_points, answer."
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for Arbor Home, developed by Arbor Home. Be professional in the way you answer and do not entertain any questions which are not in the context"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        choices = response.get("choices", [])
        if not choices or "message" not in choices[0] or "content" not in choices[0]["message"]:
            logger.error(f"Unexpected OpenAI response structure: {response}")
            return {
                "context": "Error generating response: Unexpected OpenAI response structure.",
                "relevant_products": [],
                "relevant_documents": [],
                "key_points": [],
                "answer": "Error"
            }
        answer = choices[0]["message"]["content"].strip()
        return json.loads(answer)
    except Exception as e:
        logger.error(f"Error generating GPT-3.5-turbo response: {e}")
        return {
            "context": f"Error generating response: {str(e)}",
            "relevant_products": [],
            "relevant_documents": [],
            "key_points": [],
            "answer": "Error"
        }


@app.post("/process_query")
async def process_query(request: Request):
    """
    API endpoint to process query from the frontend.
    """
    try:
        data = await request.json()
        query = data.get("query", "").strip()
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        # Check if the response is already cached
        cached_response = cache.get(query)
        if cached_response:
            logger.info(f"Cache hit for query: {query}")
            return JSONResponse(content=json.loads(cached_response))

        improved_query = improve_query(query)
        top_documents = get_top_k_documents(improved_query, k=6)
        if not top_documents:
            raise HTTPException(status_code=404, detail="No relevant documents found")

        response = extract_response_components(query, top_documents)
        cache.set(query, json.dumps(response), ex=3600)
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
