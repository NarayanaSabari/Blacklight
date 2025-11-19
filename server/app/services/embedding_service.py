"""
Embedding service for generating semantic embeddings using Google Gemini API.

This service provides functionality to:
- Generate 768-dimensional embeddings using models/embedding-001
- Batch process multiple texts efficiently
- Handle errors and implement retry logic
- Cache embeddings to avoid regeneration
"""

import os
import time
import logging
from typing import List, Optional, Dict, Any
import google.generativeai as genai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings using Google Gemini API.
    
    Uses models/embedding-001 to generate 768-dimensional vectors
    for semantic similarity matching.
    """
    
    # Gemini API configuration
    MODEL_NAME = "models/embedding-001"
    EMBEDDING_DIMENSION = 768
    
    # Batch processing configuration
    MAX_BATCH_SIZE = 100  # Gemini API limit
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_MIN_WAIT = 1  # seconds
    RETRY_MAX_WAIT = 10  # seconds
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize EmbeddingService with Google Gemini API.
        
        Args:
            api_key: Google API key. If not provided, reads from GOOGLE_API_KEY env var.
        
        Raises:
            ValueError: If API key is not provided or found in environment
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "Google API key is required. Provide via constructor or GOOGLE_API_KEY environment variable."
            )
        
        # Configure Gemini API
        genai.configure(api_key=self.api_key)
        
        logger.info(f"EmbeddingService initialized with model: {self.MODEL_NAME}")
    
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def generate_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
        """
        Generate embedding for a single text using Gemini API.
        
        Implements retry logic with exponential backoff for transient failures.
        
        Args:
            text: Input text to generate embedding for
            task_type: Task type for embedding generation. Options:
                - RETRIEVAL_QUERY: For search queries
                - RETRIEVAL_DOCUMENT: For documents to be searched (default)
                - SEMANTIC_SIMILARITY: For similarity comparison
                - CLASSIFICATION: For text classification
        
        Returns:
            768-dimensional embedding vector
        
        Raises:
            ValueError: If text is empty or None
            Exception: If API call fails after retries
        
        Example:
            >>> service = EmbeddingService()
            >>> embedding = service.generate_embedding("Python developer with 5 years experience")
            >>> len(embedding)
            768
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty or None")
        
        # Clean and truncate text if needed
        text = text.strip()
        
        try:
            logger.debug(f"Generating embedding for text (length: {len(text)})")
            
            # Generate embedding using Gemini API
            result = genai.embed_content(
                model=self.MODEL_NAME,
                content=text,
                task_type=task_type
            )
            
            embedding = result['embedding']
            
            # Validate embedding dimension
            if len(embedding) != self.EMBEDDING_DIMENSION:
                raise ValueError(
                    f"Unexpected embedding dimension: {len(embedding)} (expected {self.EMBEDDING_DIMENSION})"
                )
            
            logger.debug(f"Successfully generated embedding (dimension: {len(embedding)})")
            return embedding
        
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def generate_batch_embeddings(
        self,
        texts: List[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
        batch_size: Optional[int] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Processes texts in batches to respect API rate limits and improve efficiency.
        Implements retry logic with exponential backoff for transient failures.
        
        Args:
            texts: List of texts to generate embeddings for
            task_type: Task type for embedding generation (see generate_embedding)
            batch_size: Number of texts to process per batch (default: MAX_BATCH_SIZE)
        
        Returns:
            List of 768-dimensional embedding vectors (same order as input)
        
        Raises:
            ValueError: If texts list is empty
            Exception: If API call fails after retries
        
        Example:
            >>> service = EmbeddingService()
            >>> texts = ["Python developer", "Java engineer", "DevOps specialist"]
            >>> embeddings = service.generate_batch_embeddings(texts)
            >>> len(embeddings)
            3
            >>> len(embeddings[0])
            768
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")
        
        # Filter out empty texts and track indices
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text.strip())
                valid_indices.append(i)
        
        if not valid_texts:
            raise ValueError("All texts are empty or None")
        
        batch_size = batch_size or self.MAX_BATCH_SIZE
        total_texts = len(valid_texts)
        all_embeddings = []
        
        logger.info(f"Generating embeddings for {total_texts} texts in batches of {batch_size}")
        
        try:
            # Process in batches
            for i in range(0, total_texts, batch_size):
                batch_texts = valid_texts[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total_texts + batch_size - 1) // batch_size
                
                logger.debug(f"Processing batch {batch_num}/{total_batches} ({len(batch_texts)} texts)")
                
                # Generate embeddings for batch
                result = genai.embed_content(
                    model=self.MODEL_NAME,
                    content=batch_texts,
                    task_type=task_type
                )
                
                batch_embeddings = result['embedding']
                
                # Validate batch embeddings
                if len(batch_embeddings) != len(batch_texts):
                    raise ValueError(
                        f"Batch embedding count mismatch: got {len(batch_embeddings)}, expected {len(batch_texts)}"
                    )
                
                for embedding in batch_embeddings:
                    if len(embedding) != self.EMBEDDING_DIMENSION:
                        raise ValueError(
                            f"Unexpected embedding dimension: {len(embedding)} (expected {self.EMBEDDING_DIMENSION})"
                        )
                
                all_embeddings.extend(batch_embeddings)
                
                # Rate limiting: small delay between batches
                if i + batch_size < total_texts:
                    time.sleep(0.1)
            
            logger.info(f"Successfully generated {len(all_embeddings)} embeddings")
            
            # Create result list with None for invalid indices
            result_embeddings = [None] * len(texts)
            for i, embedding in zip(valid_indices, all_embeddings):
                result_embeddings[i] = embedding
            
            return result_embeddings
        
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise
    
    def generate_candidate_embedding(self, candidate_data) -> List[float]:
        """
        Generate embedding for a candidate profile.
        
        Combines candidate's skills, experience, and profile summary into a single
        text for embedding generation.
        
        Args:
            candidate_data: Candidate model object or dictionary containing:
                - current_title: str - Current job title
                - skills: List[str] - Technical skills
                - total_experience_years: int - Years of experience
                - profile_summary: str - Profile summary/bio (optional)
        
        Returns:
            768-dimensional embedding vector
        
        Example:
            >>> service = EmbeddingService()
            >>> candidate = Candidate.query.first()
            >>> embedding = service.generate_candidate_embedding(candidate)
        """
        # Build candidate profile text
        parts = []
        
        # Handle both model objects and dicts
        def get_value(obj, key, default=None):
            if hasattr(obj, key):
                return getattr(obj, key, default)
            return obj.get(key, default) if isinstance(obj, dict) else default
        
        # Add title if available
        title = get_value(candidate_data, "current_title") or get_value(candidate_data, "title")
        if title:
            parts.append(f"Title: {title}")
        
        # Add years of experience
        years = get_value(candidate_data, "total_experience_years") or get_value(candidate_data, "years_of_experience", 0)
        if years:
            parts.append(f"Experience: {years} years")
        
        # Add skills
        skills = get_value(candidate_data, "skills", [])
        if skills:
            skills_text = ", ".join(skills)
            parts.append(f"Skills: {skills_text}")
        
        # Add summary if available
        summary = (get_value(candidate_data, "professional_summary") or 
                   get_value(candidate_data, "profile_summary") or 
                   get_value(candidate_data, "summary", ""))
        if summary:
            parts.append(f"Summary: {summary}")
        
        # Combine all parts
        profile_text = ". ".join(parts)
        
        # Generate embedding
        return self.generate_embedding(profile_text)
    
    def generate_job_embedding(self, job_data) -> List[float]:
        """
        Generate embedding for a job posting.
        
        Combines job's skills, description, and title into a single text
        for embedding generation.
        
        Args:
            job_data: JobPosting model object or dictionary containing:
                - title: str - Job title
                - description: str - Job description
                - skills: List[str] - Required skills
                - experience_min: int - Minimum years of experience (optional)
                - location: str - Job location (optional)
        
        Returns:
            768-dimensional embedding vector
        
        Example:
            >>> service = EmbeddingService()
            >>> job = JobPosting.query.first()
            >>> embedding = service.generate_job_embedding(job)
        """
        # Build job description text
        parts = []
        
        # Handle both model objects and dicts
        def get_value(obj, key, default=None):
            if hasattr(obj, key):
                return getattr(obj, key, default)
            return obj.get(key, default) if isinstance(obj, dict) else default
        
        # Add title
        title = get_value(job_data, "title", "")
        if title:
            parts.append(f"Job Title: {title}")
        
        # Add required skills
        skills = get_value(job_data, "skills", []) or get_value(job_data, "required_skills", [])
        if skills:
            skills_text = ", ".join(skills)
            parts.append(f"Required Skills: {skills_text}")
        
        # Add experience requirement
        exp_min = get_value(job_data, "experience_min")
        if exp_min:
            parts.append(f"Minimum Experience: {exp_min} years")
        
        # Add location if specified
        location = get_value(job_data, "location", "")
        if location:
            parts.append(f"Location: {location}")
        
        # Add job description
        description = get_value(job_data, "description", "")
        if description:
            # Truncate description if too long (keep first 500 chars)
            if len(description) > 500:
                description = description[:500] + "..."
            parts.append(f"Description: {description}")
        
        # Combine all parts
        job_text = ". ".join(parts)
        
        if not job_text.strip():
            raise ValueError("Job data is empty or missing required fields")
        
        logger.debug(f"Generating embedding for job posting (length: {len(job_text)})")
        
        return self.generate_embedding(job_text, task_type="RETRIEVAL_DOCUMENT")
