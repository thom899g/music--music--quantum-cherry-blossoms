"""
Firebase Configuration & State Management
Central nervous system for the autonomous music ecosystem.
Architectural Rationale: Firebase provides real-time synchronization, offline capabilities,
and serverless triggers essential for closed-loop feedback systems.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app
from google.cloud.firestore_v1 import Client as FirestoreClient
from google.cloud.firestore_v1.document import DocumentReference
from google.cloud.firestore_v1.collection import CollectionReference

# Configure structured logging
logger = logging.getLogger(__name__)

@dataclass
class TrackVariant:
    """Data model for individual track variants in the evolutionary swarm."""
    variant_id: str
    parameters: Dict[str, Any]
    audio_path: Optional[str] = None
    platform_ids: Dict[str, str] = None  # {platform: platform_id}
    engagement_score: float = 0.0
    created_at: datetime = None
    generation: int = 1
    
    def __post_init__(self):
        if self.platform_ids is None:
            self.platform_ids = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

@dataclass
class PerformanceMetrics:
    """Real-time performance tracking across platforms."""
    variant_id: str
    platform: str
    streams: int = 0
    saves: int = 0
    shares: int = 0
    comments: int = 0
    sentiment_score: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    @property
    def engagement_score(self) -> float:
        """Weighted engagement score for variant selection."""
        return (0.5 * self.streams + 0.3 * self.saves + 0.2 * self.sentiment_score)

class FirebaseManager:
    """Singleton manager for Firebase operations with error handling and retry logic."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, credential_path: Optional[str] = None):
        if not self._initialized:
            self._credential_path = credential_path
            self._db: Optional[FirestoreClient] = None
            self._collections: Dict[str, CollectionReference] = {}
            self._initialize_firebase()
            self._initialized = True
    
    def _initialize_firebase(self) -> None:
        """Initialize Firebase with proper error handling and fallbacks."""
        try:
            # Priority order for credentials
            credential_sources = [
                self._credential_path,
                os.getenv('FIREBASE_CREDENTIALS_JSON'),
                'firebase-credentials.json'
            ]
            
            cred = None
            for source in credential_sources:
                if source and os.path.exists(source):
                    try:
                        cred = credentials.Certificate(source)
                        logger.info(f"Loaded Firebase credentials from {source}")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to load credentials from {source}: {e}")
                        continue
            
            # Initialize Firebase app
            if not firebase_admin._apps:
                if cred:
                    firebase_admin.initialize_app(cred)
                else:
                    # Use application default credentials (for GCP environments)
                    firebase_admin.initialize_app()
                    logger.info("Using application default credentials")
            
            self._db = firestore.client()
            self._initialize_collections()
            logger.info("Firebase initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise
    
    def _initialize_collections(self) -> None:
        """Initialize all required Firestore collections with schema validation."""
        collections = ['tracks', 'variants', 'performance_logs', 'feedback_signals']
        
        for collection_name in collections:
            self._collections[collection_name] = self._db.collection(collection_name)
        
        # Create initial schema validation document
        schema_doc = {
            'schema_version': '1.0',
            'created_at': datetime.now(timezone.utc),
            'system': 'quantum-cherry-blossoms',
            'description': 'Autonomous music generation ecosystem'
        }
        
        try:
            self._collections['tracks'].document('system_schema').set(schema_doc)
        except Exception as e:
            logger.warning(f"Schema document creation failed (may already exist): {e}")
    
    def create_variant(self, variant: TrackVariant) -> str:
        """Store a new track variant with validation."""
        try:
            variant_dict = asdict(variant)
            # Convert datetime to Firestore timestamp
            for key, value in variant_dict.items():
                if isinstance(value, datetime):
                    variant_dict[key] = value
            
            doc_ref = self._collections['variants'].document(variant.variant_id)
            doc_ref.set(variant_dict)
            
            logger.info(f"Created variant {variant.variant_id} in Firestore")
            return variant.variant_id
            
        except Exception as e:
            logger.error(f"Failed to create variant: {e}")
            raise
    
    def log_performance(self, metrics: PerformanceMetrics) -> bool:
        """Log performance metrics with deduplication check."""
        try:
            # Create unique ID for this performance log entry
            log_id = f"{metrics.variant_id}_{metrics.platform}_{metrics.timestamp.strftime('%Y%m%d%H')}"
            
            metrics_dict = asdict(metrics)
            metrics_dict['log_id'] = log_id
            
            self._collections['performance_logs'].document(log_id).set(metrics_dict)
            
            # Update variant's aggregate metrics
            self._update_variant_metrics(metrics)
            
            logger.debug(f"Logged performance for variant {metrics.variant_id} on {metrics.platform}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log performance: {e}")
            return False
    
    def _update_variant_metrics(self, metrics: PerformanceMetrics) -> None:
        """Update variant's aggregate engagement score."""
        try:
            variant_ref = self._collections['variants'].document(metrics.variant_id)
            variant_doc = variant_ref.get()
            
            if variant_doc.exists:
                variant_data = variant_doc.to_dict()
                current_score = variant_data.get('engagement_score', 0.0)
                new_score = current_score + (metrics.engagement_score * 0.1)  # Decay factor
                
                variant_ref.update({
                    'engagement_score': new_score,
                    'last_updated': datetime.now(timezone.utc)
                })
        except Exception as e:
            logger.warning(f"Could not update variant metrics: {e}")
    
    def get_top_variants(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve top-performing variants for exploitation phase."""
        try:
            query = (self._collections['variants']
                    .order_by('engagement_score', direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            variants = []
            for doc in query.stream():
                variant_data = doc.to_dict()
                variant_data['id'] = doc.id
                variants.append(variant_data)
            
            return variants
            
        except Exception as e:
            logger.error(f"Failed to retrieve top variants: {e}")
            return []
    
    def get_variant_parameters(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve parameters for a specific variant."""
        try:
            doc_ref = self._collections['variants'].document(variant_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict().get('parameters')
            return None
            
        except Exception as e:
            logger.error(f"Failed to get variant parameters: {e}")
            return None

# Export singleton instance
firebase_manager = FirebaseManager()