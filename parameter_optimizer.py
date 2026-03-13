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