"""
Services for text chunking and embedding operations.
"""
import hashlib
import json
import logging
from typing import List, Dict, Any, Tuple
from django.db import transaction
from django.conf import settings

# Optional imports for ML dependencies
try:
    from sentence_transformers import SentenceTransformer
    from transformers import AutoTokenizer
    ML_DEPENDENCIES_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    AutoTokenizer = None
    ML_DEPENDENCIES_AVAILABLE = False

from .models import LegalUnit, Chunk, ChunkEmbedding, IngestLog, InstrumentExpression
from .enums import IngestStatus

logger = logging.getLogger(__name__)


class TextChunkingService:
    """Service for chunking legal unit text into overlapping segments."""
    
    def __init__(self):
        # Initialize tokenizer for token counting
        if not ML_DEPENDENCIES_AVAILABLE:
            raise ImportError("ML dependencies not available. Please install: pip install sentence-transformers transformers torch")
        self.tokenizer = AutoTokenizer.from_pretrained('distilbert-base-multilingual-cased')
        
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using the tokenizer."""
        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        return len(tokens)
    
    def chunk_text(self, text: str, max_tokens: int = 900, min_tokens: int = 700, overlap: int = 100) -> List[Tuple[str, int]]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Input text to chunk
            max_tokens: Maximum tokens per chunk
            min_tokens: Minimum tokens per chunk
            overlap: Number of tokens to overlap between chunks
            
        Returns:
            List of (chunk_text, overlap_with_previous) tuples
        """
        total_tokens = self.count_tokens(text)
        
        # If text is short enough, return as single chunk
        if total_tokens <= max_tokens:
            return [(text, 0)]
        
        chunks = []
        words = text.split()
        current_chunk_words = []
        current_tokens = 0
        
        i = 0
        while i < len(words):
            word = words[i]
            word_tokens = self.count_tokens(word)
            
            # If adding this word exceeds max_tokens, finalize current chunk
            if current_tokens + word_tokens > max_tokens and current_chunk_words:
                chunk_text = ' '.join(current_chunk_words)
                overlap_tokens = 0
                
                # Calculate overlap for next chunk
                if chunks:  # Not the first chunk
                    overlap_words = current_chunk_words[-overlap:] if len(current_chunk_words) > overlap else current_chunk_words
                    overlap_tokens = self.count_tokens(' '.join(overlap_words))
                
                chunks.append((chunk_text, overlap_tokens if len(chunks) > 0 else 0))
                
                # Start next chunk with overlap
                if len(current_chunk_words) > overlap:
                    current_chunk_words = current_chunk_words[-overlap:]
                    current_tokens = self.count_tokens(' '.join(current_chunk_words))
                else:
                    current_chunk_words = []
                    current_tokens = 0
            else:
                current_chunk_words.append(word)
                current_tokens += word_tokens
                i += 1
        
        # Add final chunk if there are remaining words
        if current_chunk_words:
            chunk_text = ' '.join(current_chunk_words)
            overlap_tokens = 0
            if chunks:  # Calculate overlap for final chunk
                overlap_words = current_chunk_words[:overlap] if len(current_chunk_words) > overlap else current_chunk_words
                overlap_tokens = self.count_tokens(' '.join(overlap_words))
            chunks.append((chunk_text, overlap_tokens if len(chunks) > 0 else 0))
        
        return chunks
    
    def create_citation_payload(self, unit: LegalUnit) -> Dict[str, Any]:
        """Create citation payload JSON for a legal unit."""
        return {
            'unit_type': unit.get_unit_type_display(),
            'num_label': unit.number or unit.label,
            'eli_fragment': unit.eli_fragment or '',
            'xml_id': unit.xml_id or ''
        }
    
    def generate_hash(self, text: str) -> str:
        """Generate SHA-256 hash for chunk text."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()


class EmbeddingService:
    """Service for generating embeddings using sentence transformers."""
    
    def __init__(self):
        self.model_name = 'distiluse-base-multilingual-cased-v2'
        self.model = None
    
    def _load_model(self):
        """Lazy load the embedding model."""
        if not ML_DEPENDENCIES_AVAILABLE:
            raise ImportError("ML dependencies not available. Please install: pip install sentence-transformers transformers torch")
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        self._load_model()
        embedding = self.model.encode(text)
        return embedding.tolist()


class ChunkProcessingService:
    """Main service for processing legal units into chunks and embeddings."""
    
    def __init__(self):
        self.chunking_service = TextChunkingService()
        self.embedding_service = EmbeddingService()
    
    @transaction.atomic
    def process_expression(self, expression: InstrumentExpression) -> Dict[str, Any]:
        """
        Process all legal units in an expression to create chunks and embeddings.
        
        Args:
            expression: InstrumentExpression to process
            
        Returns:
            Dictionary with processing results
        """
        # Create ingest log entry
        log_entry = IngestLog.objects.create(
            operation_type='chunk_processing',
            source_system='chunking_service',
            status=IngestStatus.PROCESSING,
            metadata={'expression_id': str(expression.id)}
        )
        
        try:
            results = {
                'chunks_created': 0,
                'embeddings_created': 0,
                'units_processed': 0,
                'errors': []
            }
            
            # Get all legal units for this expression
            legal_units = LegalUnit.objects.filter(expr=expression).order_by('tree_id', 'lft')
            
            for unit in legal_units:
                try:
                    unit_result = self.process_legal_unit(unit)
                    results['chunks_created'] += unit_result['chunks_created']
                    results['embeddings_created'] += unit_result['embeddings_created']
                    results['units_processed'] += 1
                except Exception as e:
                    error_msg = f"Error processing unit {unit.id}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            # Update log entry
            log_entry.status = IngestStatus.COMPLETED if not results['errors'] else IngestStatus.FAILED
            log_entry.metadata.update(results)
            log_entry.save()
            
            return results
            
        except Exception as e:
            log_entry.status = IngestStatus.FAILED
            log_entry.metadata['error'] = str(e)
            log_entry.save()
            raise
    
    def process_legal_unit(self, unit: LegalUnit) -> Dict[str, Any]:
        """
        Process a single legal unit to create chunks and embeddings.
        
        Args:
            unit: LegalUnit to process
            
        Returns:
            Dictionary with processing results for this unit
        """
        results = {'chunks_created': 0, 'embeddings_created': 0}
        
        # Skip if unit has no content
        if not unit.content or not unit.content.strip():
            return results
        
        # Check token count
        token_count = self.chunking_service.count_tokens(unit.content)
        
        if token_count <= 900:
            # Create single chunk
            chunk_data = [(unit.content, 0)]
        else:
            # Split into multiple chunks
            chunk_data = self.chunking_service.chunk_text(unit.content)
        
        # Create chunks and embeddings
        for chunk_text, overlap_prev in chunk_data:
            chunk_hash = self.chunking_service.generate_hash(chunk_text)
            
            # Check if chunk already exists (avoid duplicates)
            existing_chunk = Chunk.objects.filter(
                expr=unit.expr,
                hash=chunk_hash
            ).first()
            
            if existing_chunk:
                continue  # Skip duplicate
            
            # Create chunk
            chunk = Chunk.objects.create(
                expr=unit.expr,
                unit=unit,
                chunk_text=chunk_text,
                token_count=self.chunking_service.count_tokens(chunk_text),
                overlap_prev=overlap_prev,
                citation_payload_json=self.chunking_service.create_citation_payload(unit),
                hash=chunk_hash
            )
            results['chunks_created'] += 1
            
            # Generate and save embedding
            try:
                embedding_vector = self.embedding_service.generate_embedding(chunk_text)
                
                ChunkEmbedding.objects.create(
                    chunk=chunk,
                    embedding=embedding_vector,
                    model=self.embedding_service.model_name
                )
                results['embeddings_created'] += 1
                
            except Exception as e:
                logger.error(f"Failed to create embedding for chunk {chunk.id}: {str(e)}")
        
        return results


# Service instances
chunk_processing_service = ChunkProcessingService()
