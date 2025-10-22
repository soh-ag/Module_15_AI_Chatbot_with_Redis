from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import logging
import time
from typing import Dict, Any

from .cache import cache
from .ai_engine import ai_engine
from .config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="AI Chatbot with Redis Caching",
    description="Scalable AI chatbot with Redis caching for improved performance",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="User query")

class ChatResponse(BaseModel):
    query: str
    response: str
    cached: bool
    response_time: float
    timestamp: float

class HealthResponse(BaseModel):
    status: str
    redis_connected: bool
    timestamp: float

# Utility functions
def generate_cache_key(query: str) -> str:
    """Generate a consistent cache key for the query"""
    return f"chat:{query.lower().strip()}"

# Routes
@app.get("/")
async def root():
    return {"message": "AI Chatbot API with Redis Caching"}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        redis_connected=cache.health_check(),
        timestamp=time.time()
    )

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint that uses Redis caching to store and retrieve responses
    """
    start_time = time.time()
    
    try:
        query = request.query.strip()
        if not query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query cannot be empty"
            )

        cache_key = generate_cache_key(query)
        
        # Check cache first
        cached_response = cache.get(cache_key)
        
        if cached_response:
            # Cache hit
            response_time = time.time() - start_time
            logger.info(f"🚀 Cache hit - Response time: {response_time:.3f}s")
            
            return ChatResponse(
                query=query,
                response=cached_response,
                cached=True,
                response_time=response_time,
                timestamp=time.time()
            )
        
        # Cache miss - Generate AI response
        logger.info(f"🔍 Cache miss, generating AI response for: {query}")
        ai_response = ai_engine.get_response(query)
        
        # Store in cache
        cache.set(cache_key, ai_response)
        
        response_time = time.time() - start_time
        logger.info(f"⚡ AI generated - Response time: {response_time:.3f}s")
        
        return ChatResponse(
            query=query,
            response=ai_response,
            cached=False,
            response_time=response_time,
            timestamp=time.time()
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.delete("/cache/{query}")
async def delete_cache(query: str):
    """Delete specific query from cache"""
    cache_key = generate_cache_key(query)
    if cache.delete(cache_key):
        return {"message": f"Cache deleted for query: {query}"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found in cache"
        )

@app.delete("/cache")
async def clear_cache():
    """Clear all cache (use with caution in production)"""
    # Note: In production, you might want to add authentication/authorization
    if cache.redis_client:
        cache.redis_client.flushdb()
        return {"message": "Cache cleared successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Redis not available"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )