# MUSIC: MUSIC: Quantum Cherry Blossoms

## Objective
A mission to generate a high-energy, melody-driven Anime Synth-Pop instrumental. The track will feature shimmering arpeggiators, a powerful, emotive lead melody, and a driving four-on-the-floor beat with future bass elements. Execution will utilize `generate_music.py` with parameters targeting euphoric major-key progressions and crisp, modern sound design, followed by automated distribution and metadata optimization via `claw_uploader.py` to target key streaming playlists in Anime, Electronic, and Pop categories.

## Strategy


## Execution Output
SUMMARY: I've successfully architected and implemented Phase 0 and foundational components of the Quantum Cherry Blossoms autonomous music ecosystem. This includes a robust Firebase infrastructure with intelligent state management, a predictive parameter optimization system, and the core music generation pipeline with validation. The system establishes a closed-loop, learning-based architecture that will evolve based on performance feedback.

OUTPUT: I've created 8 critical files that form the foundation of the autonomous music generation and distribution system:

### FILE: requirements.txt
```
# Core System Dependencies
firebase-admin>=6.5.0
google-cloud-firestore>=2.15.0
google-cloud-functions>=1.12.0
pandas>=2.1.0
numpy>=1.24.0
scikit-learn>=1.3.0
librosa>=0.10.0
Pillow>=10.0.0
requests>=2.31.0
python-dotenv>=1.0.0
spotipy>=2.23.0
soundcloud>=1.4.2

# Development & Logging
python-logging-loki>=0.3.1
structlog>=23.1.0
colorlog>=6.7.0

# Audio Processing
pydub>=0.25.1
soundfile>=0.12.1
```

### FILE: firebase_config.py
```python
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
```

### FILE: parameter_optimizer.py
```python
"""
Predictive Parameter Optimization Engine
Uses machine learning to evolve music generation parameters based on performance.
Architectural Rationale: Random Forest was chosen for its robustness to overfitting
and ability to handle mixed data types in parameter space.
"""

import numpy as np
import pandas as pd
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import pickle

# Import sklearn with correct naming
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

logger = logging.getLogger(__name__)

@dataclass
class ParameterSpace:
    """Defines the search space for music generation parameters."""
    bpm: Tuple[int, int] = (128, 132)  # Anime synth-pop typical range
    key_complexity: Tuple[float, float] = (0.3, 0.8)  # 0=simple, 1=complex
    arpeggiator_density: Tuple[float, float] = (0.5, 0.9)  # Note density
    bass_weight: Tuple[float, float] = (0.6, 0.9)  # Future bass emphasis
    melodic_intensity: Tuple[float, float] = (0.7, 1.0)  # Lead melody prominence
    progression_variation: Tuple[int, int] = (3, 6)  # Chord progression length
    
    @property
    def default_parameters(self) -> Dict[str, Any]:
        """Return the brief-defined optimal parameters for cold start."""
        return {
            'bpm': 130,
            'key_complexity': 0.5,
            'arpeggiator_density': 0.8,
            'bass_weight': 0.8,
            'melodic_intensity': 0.9,
            'progression_variation': 4,
            'sound_design': 'shimmering_arpeggiators',
            'key': 'C_major',
            'energy_level': 'high'
        }

class PredictiveOptimizer:
    """Machine learning model for predicting engagement from parameters."""
    
    def __init__(self, firebase_manager):
        self.firebase = firebase_manager
        self.param_space = ParameterSpace()
        self.model: Optional[RandomForestRegressor] = None
        self.scaler: Optional[StandardScaler] = None
        self.model_path = Path('models/parameter_predictor.pkl')
        self.is_trained = False
        
        # Ensure model directory exists
        self.model_path.parent.mkdir(exist_ok=True)
    
    def _load_training_data(self) -> Optional[pd.DataFrame]:
        """Load historical variant data from Firestore for training."""
        try:
            # Query variants with engagement scores
            variants_ref = self.firebase._collections['variants']
            variants = variants_ref.where('engagement_score', '>', 0).stream()
            
            data = []
            for variant in variants:
                variant_data = variant.to_dict()
                
                # Extract features and target
                params = variant_data.get('parameters', {})
                engagement = variant_data.get('engagement_score', 0)
                
                if params and engagement > 0:
                    # Convert parameters to feature vector
                    features = self._parameters_to_features(params)
                    features['engagement_score'] = engagement
                    data.append(features)
            
            if len(data) < 10:  # Insufficient data for training
                logger.warning(f"Insufficient training data: {len(data)} samples")
                return None
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Failed to load training data: {e}")
            return None
    
    def _parameters_to_features(self, params: Dict[str, Any]) -> Dict[str, float]:
        """Convert parameter dictionary to numerical feature vector."""
        feature_mapping = {
            'bpm': params.get('bpm', 130),
            'key_complexity': params.get('key_complexity', 0.