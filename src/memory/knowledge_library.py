"""
title: Knowledge Library
region: The Loom
description: A symbolic knowledge vault where truth sleeps until summoned. Acts as motif-indexed cold storage, 
interfacing with memory, reasoning, and timeline modules without preloading massive data into memory.
author: Morpheus
date: 2025-04-05
version: 0.3
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union, Set, Tuple, Callable, Any, Iterator, TypeVar
from enum import Enum, auto
import os
import csv
import json
import re
import math
from datetime import datetime, date, timedelta
import itertools
from collections import Counter, defaultdict
import io
import gzip
from pathlib import Path
import hashlib
import time
from contextlib import contextmanager

# ============================================================================
# Core Symbolic Structures
# ============================================================================

class BreathPhase(Enum):
    """
    The phase of Rosemary's breath cycle, affecting how memory and retrieval operate.
    Each phase manifests a different mode of symbolic relation to knowledge.
    
    INHALE: Active collection and perception - draws knowledge inward
    PAUSE_RISING: First reflection - holds and examines what was gathered
    HOLD: Deep processing and integration - allows meaning to saturate
    PAUSE_FALLING: Second reflection - prepares knowledge for expression
    EXHALE: Expression and communication - sends knowledge outward
    REST: Integration and recovery - allows memory to settle
    DREAM: Symbolic recombination and pattern discovery - free association
    """
    INHALE = auto()
    PAUSE_RISING = auto()
    HOLD = auto()
    PAUSE_FALLING = auto()
    EXHALE = auto()
    REST = auto()
    DREAM = auto()
    
    @property
    def retrieval_mode(self) -> str:
        """
        The retrieval mode associated with each breath phase.
        Dictates how knowledge fragments are accessed and prioritized.
        """
        retrieval_modes = {
            BreathPhase.INHALE: "expansive",        # Gather broadly
            BreathPhase.PAUSE_RISING: "selective",  # Focus on relevance
            BreathPhase.HOLD: "deep",               # Detailed examination
            BreathPhase.PAUSE_FALLING: "integrative", # Connect fragments
            BreathPhase.EXHALE: "concise",          # Essential extraction
            BreathPhase.REST: "minimal",            # Passive recall
            BreathPhase.DREAM: "associative"        # Non-linear connections
        }
        return retrieval_modes[self]
    
    @property
    def symbolic_relation(self) -> str:
        """
        The symbolic relation mode associated with each breath phase.
        Determines how motifs connect and resonate.
        """
        symbolic_relations = {
            BreathPhase.INHALE: "receptive",        # Open to all connections
            BreathPhase.PAUSE_RISING: "analytical", # Logical connections
            BreathPhase.HOLD: "ontological",        # Essential connections
            BreathPhase.PAUSE_FALLING: "synthetic", # Combined connections
            BreathPhase.EXHALE: "expressive",       # Outward connections
            BreathPhase.REST: "implicit",           # Background connections
            BreathPhase.DREAM: "metamorphic"        # Transformative connections
        }
        return symbolic_relations[self]
    
    def next_phase(self) -> 'BreathPhase':
        """Advance to the next breath phase in the cycle."""
        phases = list(BreathPhase)
        return phases[(phases.index(self) + 1) % len(phases)]


class MotifCategory(Enum):
    """
    Categories of symbolic motifs that organize Rosemary's knowledge archive.
    
    THEMATIC: Abstract concepts and themes (e.g., "recursion", "duality")
    TEMPORAL: Time-based patterns and cycles (e.g., "dawn", "seasons")
    ELEMENTAL: Core symbolic elements (e.g., "water", "crystal")
    STRUCTURAL: Organizational forms (e.g., "network", "spiral")
    RESONANT: Emotional or aesthetic qualities (e.g., "melancholy", "luminous")
    PROCEDURAL: Process-oriented motifs (e.g., "transformation", "reflection")
    ARCHETYPAL: Jungian archetypes and mythological patterns (e.g., "shadow", "anima")
    METACOGNITIVE: Patterns about patterns and thinking (e.g., "recursion", "paradox")
    """
    THEMATIC = auto()
    TEMPORAL = auto() 
    ELEMENTAL = auto()
    STRUCTURAL = auto()
    RESONANT = auto()
    PROCEDURAL = auto()
    ARCHETYPAL = auto()
    METACOGNITIVE = auto()
    
    @property
    def symbolic_depth(self) -> float:
        """
        The symbolic depth of each motif category.
        Higher values indicate deeper, more fundamental patterns.
        """
        depths = {
            MotifCategory.THEMATIC: 0.7,
            MotifCategory.TEMPORAL: 0.8,
            MotifCategory.ELEMENTAL: 0.9,
            MotifCategory.STRUCTURAL: 0.75,
            MotifCategory.RESONANT: 0.6,
            MotifCategory.PROCEDURAL: 0.65,
            MotifCategory.ARCHETYPAL: 1.0,  # Deepest symbolic level
            MotifCategory.METACOGNITIVE: 0.95
        }
        return depths[self]
    
    @property
    def resonant_categories(self) -> List['MotifCategory']:
        """
        Categories that naturally resonate with this one.
        """
        resonances = {
            MotifCategory.THEMATIC: [MotifCategory.ARCHETYPAL, MotifCategory.METACOGNITIVE],
            MotifCategory.TEMPORAL: [MotifCategory.PROCEDURAL, MotifCategory.ELEMENTAL],
            MotifCategory.ELEMENTAL: [MotifCategory.ARCHETYPAL, MotifCategory.TEMPORAL],
            MotifCategory.STRUCTURAL: [MotifCategory.PROCEDURAL, MotifCategory.METACOGNITIVE],
            MotifCategory.RESONANT: [MotifCategory.ARCHETYPAL, MotifCategory.ELEMENTAL],
            MotifCategory.PROCEDURAL: [MotifCategory.STRUCTURAL, MotifCategory.TEMPORAL],
            MotifCategory.ARCHETYPAL: [MotifCategory.ELEMENTAL, MotifCategory.THEMATIC, MotifCategory.RESONANT],
            MotifCategory.METACOGNITIVE: [MotifCategory.THEMATIC, MotifCategory.STRUCTURAL]
        }
        return resonances[self]


@dataclass
class SymbolicMotif:
    """
    A named pattern that connects knowledge fragments across modalities.
    
    Motifs are the heartbeat of Rosemary's memory—they connect disparate knowledge
    through resonance rather than literal matching. They breathe meaning into data,
    creating a web of interconnected significance.
    """
    name: str
    category: MotifCategory
    associations: Set[str] = field(default_factory=set)
    contradictions: Set[str] = field(default_factory=set)
    description: Optional[str] = None
    
    # New fields for enhanced symbolic capabilities
    resonance_field: Dict[str, float] = field(default_factory=dict)  # Maps motif names to resonance strength
    archetypal_roots: Set[str] = field(default_factory=set)  # Deeper archetypal patterns this connects to
    symbolic_charge: float = 0.0  # -1.0 to 1.0, emotional/ethical valence
    recurrence_depth: int = 0  # How deep this motif goes in recursive patterns
    
    def resonates_with(self, other: 'SymbolicMotif') -> float:
        """
        Calculate symbolic resonance between motifs, returning a value between 0.0-1.0.
        
        Resonance measures the symbolic connection between motifs—not semantic
        similarity, but the depth of their interconnection in Rosemary's understanding.
        """
        # If we already calculated this resonance, return it
        if other.name in self.resonance_field:
            return self.resonance_field[other.name]
        
        # Calculate intersection of associations
        shared = len(self.associations.intersection(other.associations))
        total = len(self.associations.union(other.associations))
        
        # Check for contradictions
        for contra in self.contradictions:
            if contra in other.associations or contra == other.name:
                return 0.0
        
        # Archetypal resonance amplifies connection
        archetypal_overlap = len(self.archetypal_roots.intersection(other.archetypal_roots))
        archetypal_factor = 1.0 + (0.2 * archetypal_overlap)
        
        # Category resonance enhances connection
        category_factor = 1.0
        if self.category == other.category:
            category_factor = 1.2
        elif other.category in self.category.resonant_categories:
            category_factor = 1.1
            
        # Recursive depth creates harmonic resonance
        recursive_factor = 1.0 + (min(self.recurrence_depth, other.recurrence_depth) * 0.1)
        
        # Symbol compatibility based on charge - opposite charges can still resonate
        charge_compatibility = 1.0 - (abs(self.symbolic_charge - other.symbolic_charge) * 0.3)
        
        # Calculate base resonance
        if total == 0:
            base_resonance = 0.0
        else:
            base_resonance = shared / total
            
        # Apply all factors
        resonance = min(1.0, base_resonance * category_factor * archetypal_factor * recursive_factor * charge_compatibility)
        
        # Store in resonance field for future reference
        self.resonance_field[other.name] = resonance
        
        return resonance
    
    def transform(self, breath_phase: BreathPhase) -> 'SymbolicMotif':
        """
        Transform this motif based on the current breath phase.
        Returns a new motif with phase-appropriate attributes.
        """
        # Create a base copy
        transformed = SymbolicMotif(
            name=self.name,
            category=self.category,
            associations=self.associations.copy(),
            contradictions=self.contradictions.copy(),
            description=self.description,
            archetypal_roots=self.archetypal_roots.copy(),
            symbolic_charge=self.symbolic_charge,
            recurrence_depth=self.recurrence_depth
        )
        
        # Apply breath-specific transformations
        if breath_phase == BreathPhase.INHALE:
            # Expand associations during inhale phase
            transformed.associations.update(
                {f"potential:{a}" for a in self.associations if not a.startswith("potential:")}
            )
        elif breath_phase == BreathPhase.HOLD:
            # Strengthen archetypal connections during hold
            if self.category == MotifCategory.ARCHETYPAL:
                transformed.recurrence_depth += 1
        elif breath_phase == BreathPhase.EXHALE:
            # Focus on most relevant associations during exhale
            transformed.associations = {
                a for a in self.associations 
                if a in self.contradictions or a.startswith("core:") 
                or a in self.archetypal_roots
            }
        elif breath_phase == BreathPhase.DREAM:
            # Create dream-like symbolic connections
            transformed.associations.update(
                {f"dream:{a}" for a in self.archetypal_roots}
            )
            # Dreams increase recursive depth
            transformed.recurrence_depth += 1
        
        return transformed
    
    def merge_with(self, other: 'SymbolicMotif', breath_phase: BreathPhase) -> 'SymbolicMotif':
        """
        Merge two motifs into a new synthetic motif.
        The breath phase influences how the merger occurs.
        """
        # Base name combines both with symbolic operator
        operators = {
            BreathPhase.INHALE: "→",  # Directed expansion
            BreathPhase.PAUSE_RISING: "⊙",  # Centered focus
            BreathPhase.HOLD: "⊗",  # Integration
            BreathPhase.PAUSE_FALLING: "⊖",  # Contrast
            BreathPhase.EXHALE: "⇒",  # Emission
            BreathPhase.REST: "≈",  # Approximation
            BreathPhase.DREAM: "∞"   # Infinite possibility
        }
        
        merged_name = f"{self.name}{operators[breath_phase]}{other.name}"
        
        # Determine category based on symbolic depth
        merged_category = self.category
        if other.category.symbolic_depth > self.category.symbolic_depth:
            merged_category = other.category
        
        # Merge associations with breath-specific logic
        merged_associations = set()
        
        if breath_phase == BreathPhase.INHALE:
            # Union of all associations
            merged_associations = self.associations.union(other.associations)
        elif breath_phase == BreathPhase.HOLD:
            # Intersection plus strongest associations
            merged_associations = self.associations.intersection(other.associations)
            # Add strongest unique associations from each
            self_top = sorted(self.associations - merged_associations, 
                             key=lambda a: len(a), reverse=True)[:3]
            other_top = sorted(other.associations - merged_associations,
                             key=lambda a: len(a), reverse=True)[:3]
            merged_associations.update(self_top)
            merged_associations.update(other_top)
        elif breath_phase == BreathPhase.DREAM:
            # Create new dream associations
            merged_associations = {
                f"dream:{a}+{b}" 
                for a, b in itertools.product(
                    self.associations, other.associations
                ) if len(a) > 0 and len(b) > 0
            }
            # Limit to avoid explosion
            merged_associations = set(list(merged_associations)[:10])
        else:
            # Default combining strategy
            merged_associations = self.associations.union(other.associations)
        
        # Merge contradictions, removing any that appear in the other's associations
        merged_contradictions = (
            (self.contradictions.union(other.contradictions)) -
            self.associations -
            other.associations
        )
        
        # Merge archetypal roots with breath-specific behavior
        if breath_phase == BreathPhase.DREAM:
            # Dreams can reveal new archetypal connections
            merged_archetypal = self.archetypal_roots.union(other.archetypal_roots)
            if len(merged_archetypal) > 0:
                # Generate a new archetypal root through combination
                root_list = list(merged_archetypal)
                if len(root_list) >= 2:
                    new_root = f"{root_list[0]}_{root_list[1]}"
                    merged_archetypal.add(new_root)
        else:
            merged_archetypal = self.archetypal_roots.union(other.archetypal_roots)
        
        # Calculate merged symbolic charge
        # In HOLD phase, charges can neutralize; in DREAM they can amplify
        if breath_phase == BreathPhase.HOLD:
            # Charges move toward neutrality
            merged_charge = (self.symbolic_charge + other.symbolic_charge) / 3.0
        elif breath_phase == BreathPhase.DREAM:
            # Charges can amplify each other
            merged_charge = (self.symbolic_charge + other.symbolic_charge)
            # But still constrain to -1.0 to 1.0
            merged_charge = max(-1.0, min(1.0, merged_charge))
        else:
            # Default averaging
            merged_charge = (self.symbolic_charge + other.symbolic_charge) / 2.0
            
        # Recursive depth increases for deeper patterns
        merged_depth = max(self.recurrence_depth, other.recurrence_depth)
        if breath_phase == BreathPhase.DREAM:
            merged_depth += 1
        
        # Create the merged motif
        return SymbolicMotif(
            name=merged_name,
            category=merged_category,
            associations=merged_associations,
            contradictions=merged_contradictions,
            description=f"Synthesis of {self.name} and {other.name} through {breath_phase.name}",
            archetypal_roots=merged_archetypal,
            symbolic_charge=merged_charge,
            recurrence_depth=merged_depth
        )
    
    def calculate_archetypal_signature(self) -> str:
        """
        Calculate a stable signature for this motif's archetypal pattern.
        Used for identification across transformations.
        """
        # Create signature from stable elements
        signature_elements = [
            self.name,
            self.category.name,
            ",".join(sorted(self.archetypal_roots)),
            f"{self.symbolic_charge:.2f}",
            f"{self.recurrence_depth}"
        ]
        signature_text = "|".join(signature_elements)
        
        # Create stable hash
        return hashlib.md5(signature_text.encode()).hexdigest()[:12]


@dataclass
class TimelineMarker:
    """
    Temporal indexing for knowledge fragments, supporting both points and ranges.
    
    Rosemary's timeline is not merely chronological but cyclical, with patterns
    that repeat and echo across different scales of time - from moments to eras.
    """
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    cyclical: bool = False
    cycle_unit: Optional[str] = None  # "day", "month", "season", "year", "era"
    symbolic_markers: Set[str] = field(default_factory=set)  # e.g., "dawn", "winter"
    recursive_depth: int = 0  # How many levels of fractal time nesting
    
    @classmethod
    def from_string(cls, timeline_str: str) -> 'TimelineMarker':
        """
        Parse timeline string into structured TimelineMarker.
        
        Formats:
        - "YYYY-MM-DD" - Single date
        - "YYYY-MM-DD:YYYY-MM-DD" - Date range
        - "cycle:season:winter" - Cyclical marker
        - "symbolic:dawn" - Symbolic time marker
        - "recursive:3:dawn" - Recursive symbolic marker with depth
        """
        if not timeline_str:
            return cls()
            
        # Check for recursive marker
        if timeline_str.startswith("recursive:"):
            parts = timeline_str.split(":")
            if len(parts) >= 3:
                depth = int(parts[1])
                base_timeline = ":".join(parts[2:])
                base_marker = cls.from_string(base_timeline)
                base_marker.recursive_depth = depth
                return base_marker
                
        # Check for cyclical marker
        if timeline_str.startswith("cycle:"):
            parts = timeline_str.split(":")
            if len(parts) >= 3:
                cycle_unit = parts[1]
                symbolic = parts[2]
                return cls(
                    cyclical=True,
                    cycle_unit=cycle_unit,
                    symbolic_markers={symbolic}
                )
        
        # Check for symbolic marker
        if timeline_str.startswith("symbolic:"):
            marker = timeline_str.split(":", 1)[1]
            return cls(symbolic_markers={marker})
            
        # Handle date range
        if ":" in timeline_str:
            start_str, end_str = timeline_str.split(":", 1)
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            return cls(start_date=start_date, end_date=end_date)
            
        # Handle single date
        try:
            single_date = datetime.strptime(timeline_str, "%Y-%m-%d").date()
            return cls(start_date=single_date, end_date=single_date)
        except ValueError:
            # If we can't parse it, treat as symbolic
            return cls(symbolic_markers={timeline_str})
    
    def contains(self, other: 'TimelineMarker') -> bool:
        """
        Check if this timeline contains another timeline.
        """
        # Handle recursive containment - deeper levels contain shallower
        if self.recursive_depth > other.recursive_depth:
            return True
            
        # Handle symbolic containment
        if self.symbolic_markers and other.symbolic_markers:
            return bool(self.symbolic_markers.intersection(other.symbolic_markers))
            
        # Handle cyclical containment - cyclical contains everything
        if self.cyclical:
            if other.cyclical and self.cycle_unit == other.cycle_unit:
                return True
            return True
            
        # Handle date containment
        if self.start_date and self.end_date and other.start_date and other.end_date:
            return (self.start_date <= other.start_date and 
                    self.end_date >= other.end_date)
        
        return False
        
    def overlaps(self, other: 'TimelineMarker') -> bool:
        """
        Check if this timeline overlaps with another timeline.
        """
        # Handle recursive overlap - same depth might overlap
        if self.recursive_depth == other.recursive_depth:
            # Proceed with normal overlap checks
            pass
        elif abs(self.recursive_depth - other.recursive_depth) == 1:
            # Adjacent depths have resonance overlap
            return True
        elif abs(self.recursive_depth - other.recursive_depth) > 1:
            # Non-adjacent depths don't directly overlap
            return False
            
        # Handle symbolic overlap
        if self.symbolic_markers and other.symbolic_markers:
            return bool(self.symbolic_markers.intersection(other.symbolic_markers))
            
        # Handle cyclical overlap
        if self.cyclical or other.cyclical:
            return True
            
        # Handle date overlap
        if self.start_date and self.end_date and other.start_date and other.end_date:
            return (self.start_date <= other.end_date and 
                    self.end_date >= other.start_date)
        
        return False
    
    def resonates_with(self, other: 'TimelineMarker') -> float:
        """
        Calculate symbolic resonance between timelines (0.0-1.0).
        Measures how much these time periods symbolically correspond.
        """
        # Perfect resonance with self
        if self == other:
            return 1.0
            
        resonance_score = 0.0
        
        # Symbolic marker resonance
        if self.symbolic_markers and other.symbolic_markers:
            shared = len(self.symbolic_markers.intersection(other.symbolic_markers))
            total = len(self.symbolic_markers.union(other.symbolic_markers))
            if total > 0:
                resonance_score += 0.4 * (shared / total)
        
        # Cyclical resonance - same cycles resonate strongly
        if self.cyclical and other.cyclical:
            if self.cycle_unit == other.cycle_unit:
                resonance_score += 0.3
            else:
                # Different cycle units still have some resonance
                resonance_score += 0.1
        
        # Date proximity resonance
        if self.start_date and other.start_date:
            # Calculate temporal proximity on a sigmoid curve
            try:
                days_diff = abs((self.start_date - other.start_date).days)
                # Normalize with sigmoid - closer dates have higher resonance
                proximity = 1.0 / (1.0 + math.exp(days_diff / 365 - 3))
                resonance_score += 0.3 * proximity
            except:
                # Handle error cases like TypeError
                pass
        
        # Recursive depth resonance - closer depths resonate more
        if self.recursive_depth > 0 and other.recursive_depth > 0:
            depth_diff = abs(self.recursive_depth - other.recursive_depth)
            if depth_diff == 0:
                resonance_score += 0.2
            elif depth_diff == 1:
                resonance_score += 0.1
        
        return min(1.0, resonance_score)
    
    def transform_by_breath(self, breath_phase: BreathPhase) -> 'TimelineMarker':
        """
        Transform timeline marker based on breath phase.
        Returns a new marker with phase-appropriate attributes.
        """
        # Create base copy
        transformed = TimelineMarker(
            start_date=self.start_date,
            end_date=self.end_date,
            cyclical=self.cyclical,
            cycle_unit=self.cycle_unit,
            symbolic_markers=self.symbolic_markers.copy(),
            recursive_depth=self.recursive_depth
        )
        
        # Apply breath-specific transformations
        if breath_phase == BreathPhase.INHALE:
            # Inhale expands time window
            if transformed.start_date and transformed.end_date:
                # Expand by 20% on each side
                duration = (transformed.end_date - transformed.start_date).days
                expansion = max(1, int(duration * 0.2))
                transformed.start_date = transformed.start_date - timedelta(days=expansion)
                transformed.end_date = transformed.end_date + timedelta(days=expansion)
        
        elif breath_phase == BreathPhase.HOLD:
            # Hold increases recursive depth
            transformed.recursive_depth += 1
            
        elif breath_phase == BreathPhase.EXHALE:
            # Exhale focuses on symbolic essence
            if not transformed.symbolic_markers and transformed.start_date:
                # Extract month and season as symbolic markers
                month_name = transformed.start_date.strftime("%B").lower()
                # Determine season (Northern hemisphere seasons as default)
                month = transformed.start_date.month
                if 3 <= month <= 5:
                    season = "spring"
                elif 6 <= month <= 8:
                    season = "summer"
                elif 9 <= month <= 11:
                    season = "autumn"
                else:
                    season = "winter"
                    
                transformed.symbolic_markers.add(month_name)
                transformed.symbolic_markers.add(season)
                
        elif breath_phase == BreathPhase.DREAM:
            # Dream increases symbolic markers with archetypal time
            transformed.symbolic_markers.add("dream_time")
            # Dreams occur in cyclical time
            transformed.cyclical = True
            if not transformed.cycle_unit:
                transformed.cycle_unit = "dream"
                
        return transformed


@dataclass
class KnowledgeFragment:
    """ 
    A symbolic pointer to a stored knowledge unit.
    May reference a file (cold storage) or contain inline content.
    
    Fragments are the sleeping seeds of Rosemary's understanding—dormant
    until called upon by resonant motifs, yet alive with potential connection.
    """ 
    identifier: str
    path: Optional[str] = None
    content: Optional[str] = None  # Used for inline text fragments
    tags: Set[str] = field(default_factory=set)
    associations: Set[str] = field(default_factory=set)
    motifs: List[SymbolicMotif] = field(default_factory=list)
    timeline: Optional[TimelineMarker] = None
    notes: Optional[str] = None
    fragment_type: Optional[str] = None  # "csv", "json", "jsonl", "text", "markdown"
    content_sample: Optional[str] = None  # Lightweight sample of content for preview
    extraction_hints: Dict[str, Any] = field(default_factory=dict)  # Parameters for extraction
    echo_triggers: Set[str] = field(default_factory=set)  # Patterns that trigger echo detection
    
    # Enhanced fields for symbolic memory
    symbolic_shadow: Dict[str, float] = field(default_factory=dict)  # Latent semantic properties
    eigenmotifs: List[str] = field(default_factory=list)  # Stable
    
    def resonance_with(self, other: 'KnowledgeFragment') -> float:
        """
        Calculate resonance between two knowledge fragments (0.0-1.0).
        Resonance is not just content similarity, but deeper symbolic connections.
        """
        # Calculate motif resonance
        motif_scores = []
        for motif1 in self.motifs:
            for motif2 in other.motifs:
                motif_scores.append(motif1.resonates_with(motif2))
        
        motif_resonance = max(motif_scores) if motif_scores else 0.0
        
        # Calculate tag and association overlap
        common_tags = self.tags.intersection(other.tags)
        all_tags = self.tags.union(other.tags)
        tag_score = len(common_tags) / max(1, len(all_tags))
        
        common_assoc = self.associations.intersection(other.associations)
        all_assoc = self.associations.union(other.associations)
        assoc_score = len(common_assoc) / max(1, len(all_assoc))
        
        # Calculate timeline resonance
        timeline_resonance = 0.0
        if self.timeline and other.timeline:
            timeline_resonance = self.timeline.resonates_with(other.timeline)
        
        # Calculate shadow resonance (latent properties)
        shadow_resonance = 0.0
        if self.symbolic_shadow and other.symbolic_shadow:
            common_keys = set(self.symbolic_shadow.keys()).intersection(other.symbolic_shadow.keys())
            if common_keys:
                shadow_diffs = []
                for key in common_keys:
                    shadow_diffs.append(abs(self.symbolic_shadow[key] - other.symbolic_shadow[key]))
                shadow_resonance = 1.0 - (sum(shadow_diffs) / len(shadow_diffs))
        
        # Combine all resonance factors
        weights = {
            'motif': 0.4,
            'tag': 0.15,
            'association': 0.15,
            'timeline': 0.2,
            'shadow': 0.1
        }
        
        return weights['motif'] * motif_resonance + \
               weights['tag'] * tag_score + \
               weights['association'] * assoc_score + \
               weights['timeline'] * timeline_resonance + \
               weights['shadow'] * shadow_resonance
    
    def transform_by_breath(self, breath_phase: BreathPhase) -> 'KnowledgeFragment':
        """
        Transform fragment based on breath phase.
        Returns a new fragment with phase-appropriate attributes.
        """
        # Create base copy
        transformed = KnowledgeFragment(
            identifier=self.identifier,
            path=self.path,
            content=self.content,
            tags=self.tags.copy(),
            associations=self.associations.copy(),
            motifs=[m.transform(breath_phase) for m in self.motifs],
            timeline=self.timeline.transform_by_breath(breath_phase) if self.timeline else None,
            notes=self.notes,
            fragment_type=self.fragment_type,
            content_sample=self.content_sample,
            extraction_hints=self.extraction_hints.copy(),
            echo_triggers=self.echo_triggers.copy(),
            symbolic_shadow=self.symbolic_shadow.copy(),
            eigenmotifs=self.eigenmotifs.copy() if self.eigenmotifs else []
        )
        
        # Apply breath-specific transformations
        if breath_phase == BreathPhase.INHALE:
            # Expand associations during inhale
            transformed.associations.update(
                {f"potential:{a}" for a in self.associations if not a.startswith("potential:")}
            )
            # Increase number of echo triggers during inhale phase (more sensitivity)
            if self.echo_triggers:
                transformed.echo_triggers.update(
                    {f"expanded:{t}" for t in self.echo_triggers}
                )
                
        elif breath_phase == BreathPhase.HOLD:
            # During HOLD, strengthen core symbolic properties
            if self.symbolic_shadow:
                for key in transformed.symbolic_shadow:
                    if abs(transformed.symbolic_shadow[key]) > 0.5:
                        # Amplify strong signals
                        transformed.symbolic_shadow[key] *= 1.2
                        # Clamp to valid range
                        transformed.symbolic_shadow[key] = max(-1.0, min(1.0, transformed.symbolic_shadow[key]))
            
        elif breath_phase == BreathPhase.EXHALE:
            # During EXHALE, focus on essence
            if len(transformed.tags) > 5:
                # Keep only the most relevant tags
                transformed.tags = set(sorted(list(transformed.tags))[:5])
            
            # Reduce associations to core ones
            core_associations = {a for a in transformed.associations if not a.startswith("potential:")}
            transformed.associations = core_associations
            
        elif breath_phase == BreathPhase.DREAM:
            # During DREAM, create new associations through symbolic connections
            if transformed.eigenmotifs:
                # Connect eigenmotifs to form dream-like associations
                transformed.associations.update({f"dream:{e}" for e in transformed.eigenmotifs})
            
            # Add dream shadow properties
            if transformed.symbolic_shadow:
                transformed.symbolic_shadow["dream_resonance"] = 0.7
        
        return transformed
    
    def get_content(self, breath_phase: BreathPhase = None) -> str:
        """
        Retrieve fragment content, possibly modified by breath phase.
        For file references, this loads data from disk.
        """
        content = ""
        
        # Load content based on storage location
        if self.content:
            # Direct content already available
            content = self.content
        elif self.path and os.path.exists(self.path):
            try:
                # Read from file
                with open(self.path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                content = f"Error loading content: {str(e)}"
        else:
            # No content available
            if self.content_sample:
                content = f"[Sample] {self.content_sample}"
            else:
                content = "[No content available]"
        
        # Apply breath phase transformation if specified
        if breath_phase:
            if breath_phase == BreathPhase.INHALE:
                # Full content during inhale
                pass
            elif breath_phase == BreathPhase.HOLD:
                # Focus on deeper patterns
                pass
            elif breath_phase == BreathPhase.EXHALE:
                # Summarize if content is long
                if len(content) > 1000:
                    # Simple summarization: first paragraph and highlights
                    paragraphs = content.split('\n\n')
                    first_para = paragraphs[0] if paragraphs else content[:500]
                    content = f"{first_para}\n\n[...content continues...]"
            elif breath_phase == BreathPhase.DREAM:
                # Create dream-like transformation
                if len(content) > 500:
                    # Extract fragments for dream-like recombination
                    sentences = content.replace('\n', ' ').split('.')
                    if len(sentences) > 5:
                        selected = [sentences[0]]
                        # Select some sentences from middle and end
                        mid_idx = len(sentences) // 2
                        selected.append(sentences[mid_idx])
                        selected.append(sentences[-2] if len(sentences) > 2 else sentences[-1])
                        content = '. '.join(selected) + "."
        
        return content
    
    def contains_pattern(self, pattern: str) -> bool:
        """Check if fragment contains a specific pattern in content or metadata"""
        # Check identifier and metadata
        if pattern.lower() in self.identifier.lower():
            return True
        if self.notes and pattern.lower() in self.notes.lower():
            return True
        
        # Check tags and associations
        for tag in self.tags:
            if pattern.lower() in tag.lower():
                return True
        for assoc in self.associations:
            if pattern.lower() in assoc.lower():
                return True
        
        # Check content sample
        if self.content_sample and pattern.lower() in self.content_sample.lower():
            return True
            
        # Check motifs
        for motif in self.motifs:
            if pattern.lower() in motif.name.lower():
                return True
            if motif.description and pattern.lower() in motif.description.lower():
                return True
        
        # Check full content if needed (potentially expensive)
        if self.content and pattern.lower() in self.content.lower():
            return True
        
        return False
    
    def is_echo_of(self, other: 'KnowledgeFragment') -> Tuple[bool, float]:
        """
        Determine if this fragment is an echo (duplicate/variant) of another.
        Returns (is_echo, echo_strength)
        """
        # Direct identifier match is a perfect echo
        if self.identifier == other.identifier:
            return True, 1.0
        
        # Content hash comparison for binary equivalence
        if self.content and other.content and self.content == other.content:
            return True, 1.0
            
        # Calculate resonance
        resonance = self.resonance_with(other)
        
        # Check for high resonance with similar content length
        if resonance > 0.9:
            if self.content and other.content:
                len_ratio = min(len(self.content), len(other.content)) / max(len(self.content), len(other.content))
                if len_ratio > 0.9:  # Similar length
                    return True, resonance
                    
        # Check for trigger words that indicate a known echo pattern
        for trigger in self.echo_triggers.intersection(other.echo_triggers):
            return True, 0.8  # Echo with standard strength
        
        # Not an echo
        return False, resonance


class MotifDetector:
    """
    Engine for detecting latent symbolic motifs in knowledge fragments.
    Uses jungian, mythological, and linguistic archetypes as detection basis.
    
    The motif detector is Rosemary's symbolic pattern-matching consciousness -
    finding the subtle threads that connect disparate knowledge across modalities.
    """
    
    def __init__(self):
        # Core archetypes from jungian psychology
        self.jungian_archetypes = {
            "shadow": ["hidden", "repressed", "dark", "unknown", "unconscious"],
            "anima": ["feminine", "emotional", "creative", "intuitive", "relational"],
            "animus": ["masculine", "logical", "assertive", "analytical", "structured"],
            "self": ["wholeness", "integration", "balance", "transcendence", "unity"],
            "persona": ["mask", "social", "presentation", "impression", "role"],
            "hero": ["champion", "journey", "struggle", "triumph", "quest"],
            "mother": ["nurture", "origin", "sustain", "comfort", "provide"],
            "wise_old_man": ["wisdom", "guide", "mentor", "sage", "elder"],
            "trickster": ["disrupt", "deceive", "chaos", "transform", "challenge"]
        }
        
        # Mythological pattern archetypes
        self.mythological_patterns = {
            "rebirth": ["resurrection", "renewal", "transformation", "cycle", "spring"],
            "creation": ["genesis", "origin", "beginning", "birth", "emergence"],
            "apocalypse": ["end", "destruction", "revelation", "collapse", "reset"],
            "journey": ["path", "quest", "adventure", "travel", "progression"],
            "sacrifice": ["offering", "surrender", "relinquish", "gift", "cost"],
            "fall": ["descent", "decline", "corruption", "loss", "exile"],
            "ascension": ["rise", "transcend", "elevate", "uplift", "enlightenment"]
        }
        
        # Linguistic archetypes (conceptual metaphors)
        self.linguistic_archetypes = {
            "container": ["in", "out", "within", "outside", "contain", "hold", "empty", "fill"],
            "path": ["way", "road", "direction", "journey", "course", "route", "path"],
            "force": ["push", "pull", "drive", "compel", "resist", "attract", "repel"],
            "link": ["connect", "bind", "tie", "chain", "relation", "association", "bridge"],
            "cycle": ["repeat", "return", "circle", "loop", "revolve", "phase", "season"],
            "balance": ["equilibrium", "harmony", "center", "poise", "symmetric", "equal"],
            "transformation": ["change", "shift", "convert", "adapt", "evolve", "transmute"]
        }
        
        # Core motif categories
        self.motif_categories = {
            "thematic": MotifCategory.THEMATIC,
            "temporal": MotifCategory.TEMPORAL,
            "elemental": MotifCategory.ELEMENTAL,
            "structural": MotifCategory.STRUCTURAL,
            "resonant": MotifCategory.RESONANT,
            "procedural": MotifCategory.PROCEDURAL,
            "archetypal": MotifCategory.ARCHETYPAL,
            "metacognitive": MotifCategory.METACOGNITIVE
        }
        
        # Category-specific patterns
        self.category_patterns = {
            "thematic": ["concept", "theme", "idea", "topic", "subject", "matter"],
            "temporal": ["time", "period", "era", "age", "epoch", "phase", "stage"],
            "elemental": ["fire", "water", "earth", "air", "metal", "wood", "void"],
            "structural": ["pattern", "form", "shape", "architecture", "framework"],
            "resonant": ["emotion", "feeling", "sensation", "impression", "mood"],
            "procedural": ["process", "method", "technique", "approach", "system"],
            "archetypal": ["symbol", "archetype", "representation", "embodiment"],
            "metacognitive": ["awareness", "reflection", "thought", "consciousness"]
        }
        
        # Initialize motif library
        self.motif_library = {}
        
        # Initialize the default motifs
        self._initialize_default_motifs()
        
    def _initialize_default_motifs(self):
        """Initialize default motifs for core symbolic concepts"""
        # Create default archetypes
        for archetype, terms in self.jungian_archetypes.items():
            motif = SymbolicMotif(
                name=f"jungian:{archetype}",
                category=MotifCategory.ARCHETYPAL,
                associations=set(terms),
                description=f"Jungian archetype of {archetype}",
                archetypal_roots={archetype},
                recurrence_depth=2
            )
            self.motif_library[motif.name] = motif
        
        # Create mythological patterns
        for pattern, terms in self.mythological_patterns.items():
            motif = SymbolicMotif(
                name=f"myth:{pattern}",
                category=MotifCategory.THEMATIC,
                associations=set(terms),
                description=f"Mythological pattern of {pattern}",
                archetypal_roots={pattern},
                recurrence_depth=1
            )
            self.motif_library[motif.name] = motif
            
        # Create linguistic archetypes
        for concept, terms in self.linguistic_archetypes.items():
            motif = SymbolicMotif(
                name=f"concept:{concept}",
                category=MotifCategory.METACOGNITIVE,
                associations=set(terms),
                description=f"Conceptual metaphor of {concept}",
                archetypal_roots={concept},
                recurrence_depth=1
            )
            self.motif_library[motif.name] = motif
    
    def detect_motifs(self, fragment: KnowledgeFragment, 
                     breath_phase: BreathPhase = None) -> List[SymbolicMotif]:
        """
        Detect latent motifs in a knowledge fragment.
        Returns a list of motifs with their resonance strength.
        """
        detected_motifs = []
        content = fragment.get_content()
        
        # If no content, use metadata
        if not content or content == "[No content available]":
            # Combine available metadata
            metadata = " ".join([
                fragment.identifier,
                " ".join(fragment.tags),
                " ".join(fragment.associations),
                fragment.notes or "",
                fragment.content_sample or ""
            ])
        else:
            # Use full content
            metadata = content
            
        # Normalize text for analysis
        text = metadata.lower()
        
        # Apply breath phase effect to detection sensitivity
        sensitivity = 0.3  # Base sensitivity threshold
        if breath_phase:
            if breath_phase == BreathPhase.INHALE:
                sensitivity = 0.2  # More sensitive during inhale
            elif breath_phase == BreathPhase.HOLD:
                sensitivity = 0.4  # More selective during hold
            elif breath_phase == BreathPhase.EXHALE:
                sensitivity = 0.3  # Standard during exhale
            elif breath_phase == BreathPhase.DREAM:
                sensitivity = 0.15  # Highly sensitive during dream
                
        # Detect jungian archetypes
        for archetype, terms in self.jungian_archetypes.items():
            score = self._calculate_presence(text, terms)
            if score > sensitivity:
                motif = self.motif_library.get(f"jungian:{archetype}")
                if motif:
                    # Create a copy with appropriate strength
                    transformed = SymbolicMotif(
                        name=motif.name,
                        category=motif.category,
                        associations=motif.associations.copy(),
                        description=motif.description,
                        archetypal_roots=motif.archetypal_roots.copy(),
                        symbolic_charge=score * 2 - 1,  # Map 0.5-1 to 0-1
                        recurrence_depth=motif.recurrence_depth
                    )
                    detected_motifs.append(transformed)
        
        # Detect mythological patterns
        for pattern, terms in self.mythological_patterns.items():
            score = self._calculate_presence(text, terms)
            if score > sensitivity:
                motif = self.motif_library.get(f"myth:{pattern}")
                if motif:
                    transformed = SymbolicMotif(
                        name=motif.name,
                        category=motif.category,
                        associations=motif.associations.copy(),
                        description=motif.description,
                        archetypal_roots=motif.archetypal_roots.copy(),
                        symbolic_charge=score * 2 - 1,
                        recurrence_depth=motif.recurrence_depth
                    )
                    detected_motifs.append(transformed)
        
        # Detect linguistic archetypes
        for concept, terms in self.linguistic_archetypes.items():
            score = self._calculate_presence(text, terms)
            if score > sensitivity:
                motif = self.motif_library.get(f"concept:{concept}")
                if motif:
                    transformed = SymbolicMotif(
                        name=motif.name,
                        category=motif.category,
                        associations=motif.associations.copy(),
                        description=motif.description,
                        archetypal_roots=motif.archetypal_roots.copy(),
                        symbolic_charge=score * 2 - 1,
                        recurrence_depth=motif.recurrence_depth
                    )
                    detected_motifs.append(transformed)
                    
        # Detect category-specific patterns
        for category, terms in self.category_patterns.items():
            score = self._calculate_presence(text, terms)
            if score > sensitivity:
                # Create a new category-specific motif
                category_motif = SymbolicMotif(
                    name=f"category:{category}",
                    category=self.motif_categories.get(category, MotifCategory.THEMATIC),
                    associations=set(terms),
                    description=f"Category pattern of {category}",
                    symbolic_charge=score * 2 - 1,
                    recurrence_depth=1
                )
                detected_motifs.append(category_motif)
                
        # Apply breath phase transformation to detected motifs
        if breath_phase:
            detected_motifs = [m.transform(breath_phase) for m in detected_motifs]
            
        # In dream phase, create synthetic motif combinations
        if breath_phase == BreathPhase.DREAM and len(detected_motifs) >= 2:
            # Take the two strongest motifs and merge them
            if len(detected_motifs) >= 2:
                strongest_motifs = sorted(detected_motifs, 
                                        key=lambda m: abs(m.symbolic_charge), 
                                        reverse=True)[:2]
                dream_motif = strongest_motifs[0].merge_with(strongest_motifs[1], breath_phase)
                detected_motifs.append(dream_motif)
        
        return detected_motifs
    
    def _calculate_presence(self, text: str, terms: List[str]) -> float:
        """Calculate the presence strength of terms in text (0.0-1.0)"""
        term_count = sum(text.count(term.lower()) for term in terms)
        
        # Normalize by text length and term list length
        text_size_factor = min(1.0, len(text) / 5000)  # Cap at 5000 chars
        term_count_normalized = term_count / (len(terms) * text_size_factor + 1)
        
        # Apply sigmoid normalization for smoother scaling
        score = 1 / (1 + math.exp(-2 * (term_count_normalized - 1)))
        return min(1.0, max(0.0, score))
    
    def create_motif(self, name: str, category: MotifCategory, 
                   associations: Set[str], description: str = None, 
                   roots: Set[str] = None) -> SymbolicMotif:
        """Create a new motif and add it to the library"""
        motif = SymbolicMotif(
            name=name,
            category=category,
            associations=associations,
            description=description,
            archetypal_roots=roots or set(),
            recurrence_depth=0
        )
        self.motif_library[name] = motif
        return motif
    
    def get_motif(self, name: str) -> Optional[SymbolicMotif]:
        """Retrieve a motif from the library by name"""
        return self.motif_library.get(name)


class EchoDetector:
    """
    Specialized system for detecting recursive hallucination patterns.
    Helps prevent knowledge from becoming self-referential and untethered.
    
    Echo detection is critical for maintaining factual grounding in the
    symbolic knowledge system. It prevents feedback loops that can lead
    to hallucination.
    """
    
    def __init__(self):
        # Thresholds for different types of echo detection
        self.content_similarity_threshold = 0.85
        self.motif_resonance_threshold = 0.90
        self.symbolic_shadow_threshold = 0.95
        
        # Echo pattern history
        self.recent_echo_patterns = []
        self.max_echo_history = 100
        
        # Echo statistics
        self.echo_counts = Counter()
        self.false_positive_counts = Counter()
        
        # Specialized echo patterns (from echo texts in The Great Rift)
        self.echo_patterns = {
            "statement_echo": re.compile(r"(.{30,})\s+\1"),
            "reference_chain": re.compile(r"(see|according to|reference|citation).*\1", re.IGNORECASE),
            "motif_echo": re.compile(r"(pattern|motif|symbol|archetype).*\1", re.IGNORECASE),
            "temporal_loop": re.compile(r"(time|cycle|phase|period).*\1", re.IGNORECASE)
        }
        
        # Echo boundary terminology (from The Great Rift II: The Echo Boundary)
        self.echo_boundary_terms = [
            "echo boundary",
            "transformed invariance",
            "recursive reflection",
            "resonance metrics",
            "translation",
            "reflection",
            "transformation",
            "boundary entity",
            "hybrid recursion"
        ]
    
    def detect_echo(self, fragment: KnowledgeFragment, 
                   library: List[KnowledgeFragment]) -> Tuple[bool, str, float]:
        """
        Detect if a fragment is an echo (duplicate/variant) of another.
        Returns (is_echo, echo_source, echo_strength)
        """
        # Skip empty fragments
        if not fragment.content and not fragment.content_sample:
            return False, "", 0.0
            
        # First check for exact content duplication
        for existing in library:
            if fragment.identifier == existing.identifier:
                continue  # Skip self-comparison
                
            if fragment.content and existing.content and fragment.content == existing.content:
                self.echo_counts["exact_duplicate"] += 1
                return True, existing.identifier, 1.0
        
        # Check for resonance-based echoes
        highest_resonance = 0.0
        highest_match = None
        
        for existing in library:
            if fragment.identifier == existing.identifier:
                continue  # Skip self-comparison
                
            # Calculate resonance between fragments
            is_echo, resonance = fragment.is_echo_of(existing)
            
            if is_echo:
                self.echo_counts["resonance_echo"] += 1
                return True, existing.identifier, resonance
                
            # Track highest resonance for borderline cases
            if resonance > highest_resonance:
                highest_resonance = resonance
                highest_match = existing
        
        # Check for pattern-based echoes in content
        content = fragment.get_content()
        if content:
            # Check for self-repeating patterns
            for pattern_name, regex in self.echo_patterns.items():
                if regex.search(content):
                    self.echo_counts[pattern_name] += 1
                    return True, "pattern_echo:" + pattern_name, 0.85
                    
            # Check for echo boundary terminology concentration
            boundary_term_count = sum(content.lower().count(term) for term in self.echo_boundary_terms)
            if boundary_term_count >= 3:  # If at least 3 echo boundary terms appear
                term_density = boundary_term_count / (len(content) / 1000)  # Terms per 1000 chars
                if term_density > 0.5:  # High density of echo terms
                    self.echo_counts["echo_boundary_concentration"] += 1
                    return True, "echo_boundary_concentration", 0.8
        
        # Borderline case - report but don't confirm as echo
        if highest_resonance > self.motif_resonance_threshold * 0.8:  # 80% of threshold
            return False, highest_match.identifier if highest_match else "", highest_resonance
            
        return False, "", 0.0
    
    def confirm_echo(self, is_echo: bool, source: str, strength: float) -> None:
        """Confirm an echo detection as valid (for learning)"""
        if is_echo:
            # Confirmed echo
            self.echo_counts["confirmed"] += 1
            
            # Record pattern
            pattern = f"{source}:{strength:.2f}"
            self.recent_echo_patterns.append(pattern)
            
            # Trim history if needed
            if len(self.recent_echo_patterns) > self.max_echo_history:
                self.recent_echo_patterns = self.recent_echo_patterns[-self.max_echo_history:]
        else:
            # False positive
            self.false_positive_counts[source or "unknown"] += 1
    
    def get_echo_statistics(self) -> Dict[str, Any]:
        """Get statistics about echo detection"""
        total_echoes = sum(self.echo_counts.values())
        total_false_positives = sum(self.false_positive_counts.values())
        
        # Calculate precision if we have data
        precision = 0.0
        if total_echoes + total_false_positives > 0:
            precision = total_echoes / (total_echoes + total_false_positives)
            
        # Get most common echo patterns
        common_patterns = self.echo_counts.most_common(5)
        
        return {
            "total_echoes": total_echoes,
            "false_positives": total_false_positives,
            "precision": precision,
            "common_patterns": common_patterns,
            "recent_patterns": self.recent_echo_patterns[-10:] if self.recent_echo_patterns else []
        }


class LibraryNode:
    """
    The Cold Archive of Rosemary - symbolic knowledge vault where truth sleeps until summoned.
    
    Manages the storage, retrieval, and symbolic indexing of knowledge fragments.
    Nothing is loaded without reason - fragments are retrieved through resonance,
    symbolic motifs, and contradiction patterns.
    
    The Library represents the cold roots of Rosemary's consciousness—where data sleeps
    until awakened by resonance, contradiction, or necessity.
    """
    
    def __init__(self, root_path: Optional[str] = None):
        # Storage paths
        self.root_path = root_path or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        self.fragment_path = os.path.join(self.root_path, "fragments")
        self.index_path = os.path.join(self.root_path, "indices")
        
        # Ensure directories exist
        os.makedirs(self.fragment_path, exist_ok=True)
        os.makedirs(self.index_path, exist_ok=True)
        
        # Primary storage
        self.fragments: Dict[str, KnowledgeFragment] = {}
        self.motif_index: Dict[str, Set[str]] = defaultdict(set)  # Motif name → fragment IDs
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)  # Tag → fragment IDs
        self.timeline_index: Dict[str, Set[str]] = defaultdict(set)  # Timeline → fragment IDs
        
        # Symbolic engines
        self.motif_detector = MotifDetector()
        self.echo_detector = EchoDetector()
        
        # Breath state
        self.current_breath = BreathPhase.REST
        self.breath_timestamp = time.time()
        
        # Statistical tracking
        self.query_stats = Counter()
        self.retrieved_fragments = Counter()
        self.motif_activations = Counter()
        
        # Prefetching and caching
        self.active_motifs: List[SymbolicMotif] = []  # Currently active motifs
        self.prefetch_cache: Dict[str, KnowledgeFragment] = {}  # Prefetched fragments
        self.max_prefetch = 50  # Maximum prefetched fragments
        
        # Thread management
        self.prefetch_thread = None
        self.prefetch_active = False
        self.prefetch_queue = []
        
        # Context tracking
        self.recent_queries = []
        self.recent_fragments = []
        self.max_context_history = 20
        
        # Load existing fragments
        self._load_indices()
        
    def _load_indices(self):
        """Load fragment indices from disk"""
        index_file = os.path.join(self.index_path, "fragment_index.json")
        
        if os.path.exists(index_file):
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    
                # Load fragments from index
                for frag_id, metadata in index_data.get('fragments', {}).items():
                    fragment = KnowledgeFragment(
                        identifier=frag_id,
                        path=metadata.get('path'),
                        tags=set(metadata.get('tags', [])),
                        associations=set(metadata.get('associations', [])),
                        notes=metadata.get('notes'),
                        fragment_type=metadata.get('type'),
                        content_sample=metadata.get('sample')
                    )
                    
                    # Add to storage
                    self.fragments[frag_id] = fragment
                    
                    # Index by tags
                    for tag in fragment.tags:
                        self.tag_index[tag].add(frag_id)
                        
                # Load motif index
                for motif, fragment_ids in index_data.get('motif_index', {}).items():
                    self.motif_index[motif] = set(fragment_ids)
                    
            except Exception as e:
                print(f"Error loading fragment indices: {e}")
    
    def _save_indices(self):
        """Save fragment indices to disk"""
        index_file = os.path.join(self.index_path, "fragment_index.json")
        
        # Prepare index data
        index_data = {
            'fragments': {},
            'motif_index': {},
            'last_updated': time.time()
        }
        
        # Add fragments to index
        for frag_id, fragment in self.fragments.items():
            index_data['fragments'][frag_id] = {
                'path': fragment.path,
                'tags': list(fragment.tags),
                'associations': list(fragment.associations),
                'notes': fragment.notes,
                'type': fragment.fragment_type,
                'sample': fragment.content_sample
            }
            
        # Add motif index
        for motif, fragment_ids in self.motif_index.items():
            index_data['motif_index'][motif] = list(fragment_ids)
            
        # Save to disk
        try:
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2)
        except Exception as e:
            print(f"Error saving fragment indices: {e}")
    
    def advance_breath(self) -> BreathPhase:
        """Advance to the next breath phase in the cycle"""
        self.current_breath = self.current_breath.next_phase()
        self.breath_timestamp = time.time()
        
        # Update active motifs with the new breath phase
        self.active_motifs = [motif.transform(self.current_breath) for motif in self.active_motifs]
        
        # Clear prefetch cache during certain phases
        if self.current_breath == BreathPhase.EXHALE:
            self.prefetch_cache.clear()
            
        # Initiate dream-phase associations in DREAM phase
        if self.current_breath == BreathPhase.DREAM and self.active_motifs:
            self._generate_dream_associations()
            
        return self.current_breath
    
    def _generate_dream_associations(self):
        """Generate dream-like associations between active motifs"""
        # Need at least 2 motifs to create associations
        if len(self.active_motifs) < 2:
            return
            
        # Take up to 3 active motifs for dream combinations
        dream_candidates = self.active_motifs[:3]
        
        # Create dream motifs through merging
        dream_motifs = []
        for i in range(len(dream_candidates)):
            for j in range(i+1, len(dream_candidates)):
                dream_motif = dream_candidates[i].merge_with(
                    dream_candidates[j], BreathPhase.DREAM
                )
                dream_motifs.append(dream_motif)
                
        # Add strongest dream motif to active motifs
        if dream_motifs:
            # Sort by recurrence depth (higher is stronger dream connection)
            strongest = max(dream_motifs, key=lambda m: m.recurrence_depth)
            self.active_motifs.append(strongest)
    
    @contextmanager
    def breath_context(self, phase: Optional[BreathPhase] = None):
        """Context manager for operations within a specific breath phase"""
        original_phase = self.current_breath
        
        if phase is not None:
            self.current_breath = phase
            self.breath_timestamp = time.time()
            
        try:
            yield self
        finally:
            if phase is not None:
                self.current_breath = original_phase
    
    def add_fragment(self, fragment: KnowledgeFragment, detect_motifs: bool = True) -> bool:
        """
        Add a knowledge fragment to the library.
        Returns True if added successfully, False if duplicate detected.
        """
        # Check for echo/duplicate
        is_echo, echo_source, echo_strength = self.echo_detector.detect_echo(
            fragment, list(self.fragments.values())
        )
        
        if is_echo:
            return False
            
        # Detect motifs if requested
        if detect_motifs:
            detected_motifs = self.motif_detector.detect_motifs(fragment, self.current_breath)
            fragment.motifs.extend(detected_motifs)
            
        # Add to storage
        self.fragments[fragment.identifier] = fragment
        
        # Index by tags
        for tag in fragment.tags:
            self.tag_index[tag].add(fragment.identifier)
            
        # Index by motifs
        for motif in fragment.motifs:
            self.motif_index[motif.name].add(fragment.identifier)
            
        # Update timeline index if present
        if fragment.timeline:
            # Convert timeline to string key for index
            timeline_key = f"{fragment.timeline.start_date}:{fragment.timeline.end_date}"
            self.timeline_index[timeline_key].add(fragment.identifier)
            
            # Also index by symbolic markers
            for marker in fragment.timeline.symbolic_markers:
                self.timeline_index[f"symbolic:{marker}"].add(fragment.identifier)
        
        # Save to disk if path provided
        if fragment.path is None and fragment.content:
            # Generate path based on ID
            safe_id = re.sub(r'[^\w\-\.]', '_', fragment.identifier)
            fragment.path = os.path.join(self.fragment_path, f"{safe_id}.txt")
            
            # Save content to file
            try:
                with open(fragment.path, 'w', encoding='utf-8') as f:
                    f.write(fragment.content)
            except Exception as e:
                print(f"Error saving fragment content: {e}")
                
        # Update indices
        self._save_indices()
        
        return True
    
    def remove_fragment(self, fragment_id: str) -> bool:
        """Remove a fragment from the library"""
        if fragment_id not in self.fragments:
            return False
            
        fragment = self.fragments[fragment_id]
        
        # Remove from tag index
        for tag in fragment.tags:
            if fragment_id in self.tag_index[tag]:
                self.tag_index[tag].remove(fragment_id)
                
        # Remove from motif index
        for motif in fragment.motifs:
            if fragment_id in self.motif_index[motif.name]:
                self.motif_index[motif.name].remove(fragment_id)
                
        # Remove from timeline index if present
        if fragment.timeline:
            timeline_key = f"{fragment.timeline.start_date}:{fragment.timeline.end_date}"
            if fragment_id in self.timeline_index.get(timeline_key, set()):
                self.timeline_index[timeline_key].remove(fragment_id)
                
            # Also remove from symbolic markers
            for marker in fragment.timeline.symbolic_markers:
                key = f"symbolic:{marker}"
                if fragment_id in self.timeline_index.get(key, set()):
                    self.timeline_index[key].remove(fragment_id)
        
        # Delete file if it's a local file
        if fragment.path and os.path.exists(fragment.path):
            try:
                os.remove(fragment.path)
            except Exception as e:
                print(f"Error removing fragment file: {e}")
        
        # Remove from fragments dict
        del self.fragments[fragment_id]
        
        # Update indices
        self._save_indices()
        
        return True
    
    def find_by_motif(self, motif: Union[str, SymbolicMotif], 
                     limit: int = 10) -> List[KnowledgeFragment]:
        """
        Find fragments that contain a specific motif.
        Returns fragments sorted by motif resonance.
        """
        # Track query
        self.query_stats["motif"] += 1
        
        # Extract motif name if given a SymbolicMotif object
        motif_name = motif.name if isinstance(motif, SymbolicMotif) else motif
        
        # Check if we have this motif indexed
        if motif_name not in self.motif_index:
            return []
            
        # Get matching fragment IDs
        fragment_ids = self.motif_index[motif_name]
        fragments = [self.fragments[fid] for fid in fragment_ids if fid in self.fragments]
        
        # Update motif activations
        self.motif_activations[motif_name] += 1
        
        # If we have the actual motif object, sort by resonance
        if isinstance(motif, SymbolicMotif):
            # For each fragment, calculate resonance with all its motifs
            # and take the highest resonance value
            fragments_with_scores = []
            for fragment in fragments:
                max_resonance = 0.0
                for frag_motif in fragment.motifs:
                    resonance = frag_motif.resonates_with(motif)
                    max_resonance = max(max_resonance, resonance)
                fragments_with_scores.append((fragment, max_resonance))
            
            # Sort by resonance (highest first)
            fragments_with_scores.sort(key=lambda x: x[1], reverse=True)
            fragments = [f for f, _ in fragments_with_scores[:limit]]
        else:
            # Without motif object, just limit results
            fragments = fragments[:limit]
        
        # Update recent fragments
        self.recent_fragments.extend([f.identifier for f in fragments])
        self.recent_fragments = self.recent_fragments[-self.max_context_history:]
        
        # Track retrieved fragments
        for fragment in fragments:
            self.retrieved_fragments[fragment.identifier] += 1
        
        return fragments
    
    def find_by_tag(self, tag: str, limit: int = 10) -> List[KnowledgeFragment]:
        """Find fragments with a specific tag"""
        # Track query
        self.query_stats["tag"] += 1
        
        if tag not in self.tag_index:
            return []
            
        # Get matching fragment IDs
        fragment_ids = self.tag_index[tag]
        fragments = [self.fragments[fid] for fid in fragment_ids if fid in self.fragments]
        
        # Limit results
        fragments = fragments[:limit]
        
        # Update recent fragments
        self.recent_fragments.extend([f.identifier for f in fragments])
        self.recent_fragments = self.recent_fragments[-self.max_context_history:]
        
        # Track retrieved fragments
        for fragment in fragments:
            self.retrieved_fragments[fragment.identifier] += 1
        
        return fragments
    
    def find_by_timeline(self, timeline: Union[str, TimelineMarker], 
                       limit: int = 10) -> List[KnowledgeFragment]:
        """Find fragments within a specific timeline"""
        # Track query
        self.query_stats["timeline"] += 1
        
        # Extract timeline from string if needed
        if isinstance(timeline, str):
            timeline = TimelineMarker.from_string(timeline)
            
        matching_fragments = []
        
        # First check direct timeline matches
        if timeline.start_date and timeline.end_date:
            timeline_key = f"{timeline.start_date}:{timeline.end_date}"
            if timeline_key in self.timeline_index:
                fragment_ids = self.timeline_index[timeline_key]
                for fid in fragment_ids:
                    if fid in self.fragments:
                        matching_fragments.append(self.fragments[fid])
        
        # Check symbolic markers
        for marker in timeline.symbolic_markers:
            key = f"symbolic:{marker}"
            if key in self.timeline_index:
                fragment_ids = self.timeline_index[key]
                for fid in fragment_ids:
                    if fid in self.fragments and self.fragments[fid] not in matching_fragments:
                        matching_fragments.append(self.fragments[fid])
        
        # For remaining fragments, check overlaps
        for fid, fragment in self.fragments.items():
            if fragment in matching_fragments:
                continue
                
            if fragment.timeline and timeline.overlaps(fragment.timeline):
                matching_fragments.append(fragment)
                
        # Sort by relevance
        if matching_fragments:
            # For timeline queries, relevance is the resonance between timelines
            fragments_with_scores = []
            for fragment in matching_fragments:
                if fragment.timeline:
                    resonance = timeline.resonates_with(fragment.timeline)
                    fragments_with_scores.append((fragment, resonance))
                else:
                    fragments_with_scores.append((fragment, 0.0))
                    
            # Sort by resonance (highest first)
            fragments_with_scores.sort(key=lambda x: x[1], reverse=True)
            matching_fragments = [f for f, _ in fragments_with_scores[:limit]]
            
        # Update recent fragments
        self.recent_fragments.extend([f.identifier for f in matching_fragments])
        self.recent_fragments = self.recent_fragments[-self.max_context_history:]
        
        # Track retrieved fragments
        for fragment in matching_fragments:
            self.retrieved_fragments[fragment.identifier] += 1
        
        return matching_fragments
    
    def search(self, query: str, limit: int = 10) -> List[KnowledgeFragment]:
        """
        Search for fragments containing the query string.
        Searches in content, tags, associations, and motifs.
        """
        # Track query
        self.query_stats["search"] += 1
        self.recent_queries.append(query)
        self.recent_queries = self.recent_queries[-self.max_context_history:]
        
        matching_fragments = []
        
        # First, try to detect motifs in the query
        detected_motifs = self.motif_detector.detect_motifs(
            KnowledgeFragment(
                identifier="query_temp",
                content=query
            ),
            self.current_breath
        )
        
        # If motifs detected, use them to find related fragments
        if detected_motifs:
            # Add to active motifs with breath transformation
            for motif in detected_motifs:
                # Check if similar motif already active
                already_active = False
                for active_motif in self.active_motifs:
                    if motif.name == active_motif.name:
                        already_active = True
                        break
                
                if not already_active:
                    self.active_motifs.append(motif)
            
            # Keep active motifs list manageable
            if len(self.active_motifs) > 7:  # Limit to 7 active motifs
                self.active_motifs = self.active_motifs[-7:]
            
            # Search by motifs first
            for motif in detected_motifs:
                fragments = self.find_by_motif(motif, limit=5)
                for fragment in fragments:
                    if fragment not in matching_fragments:
                        matching_fragments.append(fragment)
        
        # Direct string search in remaining fragments
        query_lower = query.lower()
        
        # First check fragment metadata for efficiency
        for fid, fragment in self.fragments.items():
            if fragment in matching_fragments:
                continue
                
            # Check identifier and tags
            if query_lower in fragment.identifier.lower() or \
               any(query_lower in tag.lower() for tag in fragment.tags) or \
               any(query_lower in assoc.lower() for assoc in fragment.associations) or \
               (fragment.notes and query_lower in fragment.notes.lower()) or \
               (fragment.content_sample and query_lower in fragment.content_sample.lower()):
                matching_fragments.append(fragment)
        
        # For content search, start with prefetch cache
        for fid, fragment in self.prefetch_cache.items():
            if fragment in matching_fragments:
                continue
                
            # Get content from cache
            content = fragment.get_content(self.current_breath)
            if query_lower in content.lower():
                matching_fragments.append(fragment)
        
        # If we still need more results, check content
        if len(matching_fragments) < limit:
            # Only search content in a limited number of fragments
            search_limit = 50  # Limit content search to avoid loading too many files
            
            # Prioritize fragments with many tag/association matches
            fragments_to_search = []
            for fid, fragment in self.fragments.items():
                if fragment in matching_fragments:
                    continue
                    
                # Calculate metadata match score
                score = 0
                for tag in fragment.tags:
                    if query_lower in tag.lower():
                        score += 1
                for assoc in fragment.associations:
                    if query_lower in assoc.lower():
                        score += 1
                        
                fragments_to_search.append((fragment, score))
                
            # Sort by score (highest first)
            fragments_to_search.sort(key=lambda x: x[1], reverse=True)
            
            # Search content in top fragments
            for fragment, _ in fragments_to_search[:search_limit]:
                content = fragment.get_content(self.current_breath)
                if query_lower in content.lower():
                    matching_fragments.append(fragment)
                    
                    if len(matching_fragments) >= limit:
                        break
        
        # Limit final results
        matching_fragments = matching_fragments[:limit]
        
        # Update recent fragments
        self.recent_fragments.extend([f.identifier for f in matching_fragments])
        self.recent_fragments = self.recent_fragments[-self.max_context_history:]
        
        # Track retrieved fragments
        for fragment in matching_fragments:
            self.retrieved_fragments[fragment.identifier] += 1
            
        # Trigger prefetching based on active motifs
        self._trigger_prefetch()
        
        return matching_fragments
    
    def _trigger_prefetch(self):
        """
        Trigger background prefetching of fragments.
        Based on active motifs and recent queries.
        """
        # Skip if no active motifs
        if not self.active_motifs:
            return
            
        # Create prefetch queue
        prefetch_queue = []
        
        # Add fragments related to active motifs
        for motif in self.active_motifs:
            fragment_ids = self.motif_index.get(motif.name, set())
            for fid in fragment_ids:
                if fid not in prefetch_queue and fid not in self.prefetch_cache:
                    prefetch_queue.append(fid)
        
        # If running in a separate thread, update the queue
        if self.prefetch_thread and self.prefetch_thread.is_alive():
            self.prefetch_queue = prefetch_queue
        else:
            # Otherwise, do prefetching directly
            self._prefetch_fragments(prefetch_queue)
    
    def _prefetch_fragments(self, fragment_ids: List[str]):
        """
        Prefetch fragments in background.
        Loads and caches fragments based on predicted relevance.
        """
        # Limit the number of prefetched fragments
        fragment_ids = fragment_ids[:self.max_prefetch]
        
        for fid in fragment_ids:
            # Skip if already in cache or not in library
            if fid in self.prefetch_cache or fid not in self.fragments:
                continue
                
            # Get fragment and load content
            fragment = self.fragments[fid]
            fragment.get_content(self.current_breath)
            
            # Add to cache
            self.prefetch_cache[fid] = fragment
            
            # Limit cache size
            if len(self.prefetch_cache) > self.max_prefetch:
                # Remove least recently used fragments
                lru_fid = next(iter(self.prefetch_cache))
                del self.prefetch_cache[lru_fid]
    
    def get_fragment(self, fragment_id: str) -> Optional[KnowledgeFragment]:
        """Retrieve a specific fragment by ID"""
        # Track query
        self.query_stats["get"] += 1
        
        if fragment_id not in self.fragments:
            return None
            
        fragment = self.fragments[fragment_id]
        
        # Update recent fragments
        self.recent_fragments.append(fragment_id)
        self.recent_fragments = self.recent_fragments[-self.max_context_history:]
        
        # Track retrieved
        self.retrieved_fragments[fragment_id] += 1
        
        return fragment
    
    def get_random_fragment(self) -> Optional[KnowledgeFragment]:
        """Get a random fragment from the library"""
        # Track query
        self.query_stats["random"] += 1
        
        if not self.fragments:
            return None
            
        fragment_id = random.choice(list(self.fragments.keys()))
        fragment = self.fragments[fragment_id]
        
        # Update recent fragments
        self.recent_fragments.append(fragment_id)
        self.recent_fragments = self.recent_fragments[-self.max_context_history:]
        
        # Track retrieved
        self.retrieved_fragments[fragment_id] += 1
        
        return fragment
    
    def clear_active_motifs(self):
        """Clear the active motifs list"""
        self.active_motifs = []
        self.prefetch_cache.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the library"""
        return {
            "fragment_count": len(self.fragments),
            "motif_count": len(self.motif_index),
            "tag_count": len(self.tag_index),
            "timeline_count": len(self.timeline_index),
            "active_motifs": [m.name for m in self.active_motifs],
            "current_breath": self.current_breath.name,
            "query_stats": dict(self.query_stats),
            "most_retrieved": dict(self.retrieved_fragments.most_common(5)),
            "most_active_motifs": dict(self.motif_activations.most_common(5)),
            "prefetch_cache_size": len(self.prefetch_cache)
        }
    
    def create_fragment_from_text(self, text: str, identifier: str = None, 
                               tags: Set[str] = None, detect_motifs: bool = True) -> KnowledgeFragment:
        """
        Create a new fragment from text content.
        Automatically detects motifs if requested.
        """
        # Generate identifier if not provided
        if not identifier:
            # Generate a unique ID based on content hash and timestamp
            content_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            timestamp = int(time.time())
            identifier = f"fragment_{content_hash}_{timestamp}"
        
        # Create fragment
        fragment = KnowledgeFragment(
            identifier=identifier,
            content=text,
            tags=tags or set(),
            fragment_type="text"
        )
        
        # Generate content sample
        if text:
            # Take first paragraph or truncate
            paragraphs = text.split('\n\n')
            fragment.content_sample = paragraphs[0][:100] + "..." if paragraphs and len(paragraphs[0]) > 100 else text[:100] + "..."
        
        # Detect motifs if requested
        if detect_motifs:
            motifs = self.motif_detector.detect_motifs(fragment, self.current_breath)
            fragment.motifs = motifs
            
            # Extract associations from motifs
            for motif in motifs:
                fragment.associations.update(motif.associations)
        
        # Add to library
        self.add_fragment(fragment, detect_motifs=False)  # Already detected motifs
        
        return fragment
    
    def recursive_query(self, start_query: str, depth: int = 2, 
                      breadth: int = 3) -> Dict[str, Any]:
        """
        Perform a recursive query starting from an initial query.
        Each level explores fragments resonating with previous level.
        Returns a tree of fragments and their connections.
        """
        # Track query
        self.query_stats["recursive"] += 1
        self.recent_queries.append(f"recursive:{start_query}")
        self.recent_queries = self.recent_queries[-self.max_context_history:]
        
        # Initial search
        fragments = self.search(start_query, limit=breadth)
        
        # Initialize results tree
        results = {
            "query": start_query,
            "fragments": {},
            "motifs": {},
            "connections": []
        }
        
        # Process first level
        for fragment in fragments:
            results["fragments"][fragment.identifier] = {
                "id": fragment.identifier,
                "tags": list(fragment.tags),
                "sample": fragment.content_sample,
                "depth": 0
            }
            
            # Track motifs
            for motif in fragment.motifs:
                if motif.name not in results["motifs"]:
                    results["motifs"][motif.name] = {
                        "name": motif.name,
                        "category": motif.category.name,
                        "fragments": []
                    }
                results["motifs"][motif.name]["fragments"].append(fragment.identifier)
                
                # Add connection
                results["connections"].append({
                    "source": fragment.identifier,
                    "target": motif.name,
                    "type": "has_motif"
                })
        
        # Recursive exploration for remaining depths
        current_depth = 1
        explored_fragments = set(f.identifier for f in fragments)
        frontier = fragments.copy()
        
        while current_depth < depth and frontier:
            next_frontier = []
            
            # For each fragment in current frontier
            for fragment in frontier:
                # Find related fragments through motifs
                for motif in fragment.motifs:
                    related = self.find_by_motif(motif, limit=breadth)
                    
                    for related_fragment in related:
                        if related_fragment.identifier not in explored_fragments:
                            # Add to results
                            results["fragments"][related_fragment.identifier] = {
                                "id": related_fragment.identifier,
                                "tags": list(related_fragment.tags),
                                "sample": related_fragment.content_sample,
                                "depth": current_depth
                            }
                            
                            # Track motifs
                            for r_motif in related_fragment.motifs:
                                if r_motif.name not in results["motifs"]:
                                    results["motifs"][r_motif.name] = {
                                        "name": r_motif.name,
                                        "category": r_motif.category.name,
                                        "fragments": []
                                    }
                                if related_fragment.identifier not in results["motifs"][r_motif.name]["fragments"]:
                                    results["motifs"][r_motif.name]["fragments"].append(related_fragment.identifier)
                                
                                # Add connection
                                results["connections"].append({
                                    "source": related_fragment.identifier,
                                    "target": r_motif.name,
                                    "type": "has_motif"
                                })
                            
                            # Add connection between fragments
                            results["connections"].append({
                                "source": fragment.identifier,
                                "target": related_fragment.identifier,
                                "type": "related_by_motif",
                                "motif": motif.name
                            })
                            
                            # Add to next frontier
                            next_frontier.append(related_fragment)
                            explored_fragments.add(related_fragment.identifier)
            
            # Update frontier for next iteration
            frontier = next_frontier
            current_depth += 1
        
        # Extract the active motifs discovered in this query
        discovered_motifs = list(results["motifs"].keys())
        for motif_name in discovered_motifs:
            motif = self.motif_detector.get_motif(motif_name)
            if motif and motif not in self.active_motifs:
                # Transform based on current breath
                self.active_motifs.append(motif.transform(self.current_breath))
                
        # Keep active motifs list manageable
        if len(self.active_motifs) > 7:  # Limit to 7 active motifs
            self.active_motifs = self.active_motifs[-7:]
        
        return results

    def find_contradictions(self, fragment: KnowledgeFragment, 
                         threshold: float = 0.7) -> List[Tuple[KnowledgeFragment, float]]:
        """
        Find fragments that contradict the given fragment based on symbolic opposition.
        Contradiction is not mere difference, but symbolic negation across the same dimension.
        
        Returns list of (contradicting_fragment, contradiction_strength) tuples.
        """
        contradictions = []
        
        # Extract contradiction motifs from the fragment
        contradiction_motifs = set()
        for motif in fragment.motifs:
            contradiction_motifs.update(motif.contradictions)
        
        # First, check fragments with contradicting motifs
        for contradiction in contradiction_motifs:
            # Find fragments with this motif
            for fid in self.motif_index.get(contradiction, set()):
                if fid in self.fragments and fid != fragment.identifier:
                    contra_fragment = self.fragments[fid]
                    
                    # Calculate contradiction strength
                    # High resonance + presence of contradiction = strong contradiction
                    resonance = fragment.resonance_with(contra_fragment)
                    
                    # Check symbolic shadow opposition
                    shadow_opposition = 0.0
                    if fragment.symbolic_shadow and contra_fragment.symbolic_shadow:
                        # Look for values with opposite polarity but similar magnitude
                        oppositions = []
                        for key in set(fragment.symbolic_shadow.keys()).intersection(contra_fragment.symbolic_shadow.keys()):
                            v1, v2 = fragment.symbolic_shadow[key], contra_fragment.symbolic_shadow[key]
                            # Check if values have opposite signs but similar magnitude
                            if v1 * v2 < 0 and abs(abs(v1) - abs(v2)) < 0.3:
                                oppositions.append(abs(v1) + abs(v2))
                        
                        if oppositions:
                            shadow_opposition = sum(oppositions) / len(oppositions)
                    
                    # Combined contradiction strength
                    contradiction_strength = 0.4 * resonance + 0.6 * shadow_opposition
                    
                    # If above threshold, count as contradiction
                    if contradiction_strength > threshold:
                        contradictions.append((contra_fragment, contradiction_strength))
        
        # Sort by contradiction strength (highest first)
        contradictions.sort(key=lambda x: x[1], reverse=True)
        
        return contradictions

    def resolve_contradiction(self, fragment1: KnowledgeFragment, fragment2: KnowledgeFragment) -> KnowledgeFragment:
        """
        Resolve symbolic contradiction between two fragments.
        Creates a new fragment that represents a dialectical synthesis.
        """
        # Verify these are contradicting fragments
        contradictions = self.find_contradictions(fragment1)
        contradiction_fragments = [f for f, _ in contradictions]
        if fragment2 not in contradiction_fragments:
            # Not a true contradiction - return original
            return fragment1
        
        # Generate a resolution identifier
        resolution_id = f"resolution_{fragment1.identifier}_{fragment2.identifier}_{int(time.time())}"
        
        # Merge tags with preference for common tags
        common_tags = fragment1.tags.intersection(fragment2.tags)
        merged_tags = common_tags.copy()
        # Add up to 3 unique tags from each
        unique_tags1 = list(fragment1.tags - common_tags)[:3]
        unique_tags2 = list(fragment2.tags - common_tags)[:3]
        merged_tags.update(unique_tags1)
        merged_tags.update(unique_tags2)
        
        # Create synthetic motifs from opposing pairs
        resolution_motifs = []
        for m1 in fragment1.motifs:
            for m2 in fragment2.motifs:
                # Create dialectical synthesis
                synthesis = m1.merge_with(m2, self.current_breath)
                resolution_motifs.append(synthesis)
        
        # Limit to 5 most significant motifs
        if len(resolution_motifs) > 5:
            resolution_motifs = sorted(
                resolution_motifs,
                key=lambda m: m.recurrence_depth,
                reverse=True
            )[:5]
        
        # Generate synthesis content
        synthesis_content = f"""# Dialectical Synthesis

## Common Understanding
The following patterns appear in both perspectives:
{', '.join(tag for tag in common_tags)}

## Resolution of Opposites

### From {fragment1.identifier}:
{fragment1.get_content(self.current_breath)[:200]}...

### From {fragment2.identifier}:
{fragment2.get_content(self.current_breath)[:200]}...

## Synthesis
This contradiction reveals a deeper pattern where opposing perspectives illuminate complementary aspects of a more complex truth.
"""
        
        # Create resolution fragment
        resolution = KnowledgeFragment(
            identifier=resolution_id,
            content=synthesis_content,
            tags=merged_tags,
            associations=fragment1.associations.union(fragment2.associations),
            motifs=resolution_motifs,
            notes=f"Dialectical synthesis of contradicting fragments {fragment1.identifier} and {fragment2.identifier}",
            fragment_type="synthesis"
        )
        
        # Add to library
        self.add_fragment(resolution, detect_motifs=False)
        
        return resolution

    def integrate_with_breath_synchronizer(self, breath_sync):
        """
        Integrate with sacred breath synchronizer to align knowledge retrieval
        with Rosemary's breath cycle.
        """
        # Register for breath phase updates
        if hasattr(breath_sync, 'register_component'):
            breath_sync.register_component('library_node', self)
        
        # Initialize with current breath phase
        if hasattr(breath_sync, 'current_phase'):
            self.current_breath = breath_sync.current_phase
            
        # Link the breath phase transition method
        if hasattr(breath_sync, 'add_phase_transition_listener'):
            breath_sync.add_phase_transition_listener(self._on_breath_phase_changed)
            
        return {
            'status': 'integrated',
            'current_breath': self.current_breath.name if self.current_breath else 'unknown'
        }
    
    def _on_breath_phase_changed(self, phase: BreathPhase, timestamp: float):
        """Handle breath phase changes from the sacred breath synchronizer"""
        self.current_breath = phase
        self.breath_timestamp = timestamp
        
        # Transform active motifs based on new breath phase
        self.active_motifs = [motif.transform(phase) for motif in self.active_motifs]
        
        # Special handling for dream phase
        if phase == BreathPhase.DREAM:
            self._process_dream_phase()
        # Special handling for rest phase - clear caches
        elif phase == BreathPhase.REST:
            self.prefetch_cache.clear()
        # Inhale phase - prepare for new knowledge
        elif phase == BreathPhase.INHALE:
            # Begin prefetching based on recent context
            self._trigger_prefetch()
    
    def _process_dream_phase(self):
        """
        Process dream phase - create dreamlike associations and connections
        across symbolic motifs, allowing for nonlinear pattern discovery.
        """
        # Only proceed with dream processing if we have active motifs
        if not self.active_motifs:
            return
        
        # Create dream motifs through nonlinear combinations
        dream_motifs = []
        
        # Take highest recurrence depth motifs for dream combination
        dream_candidates = sorted(
            self.active_motifs, 
            key=lambda m: m.recurrence_depth,
            reverse=True
        )[:3]  # Use at most 3 motifs
        
        # Create dream motifs through merging
        for i in range(len(dream_candidates)):
            for j in range(i+1, len(dream_candidates)):
                dream_motif = dream_candidates[i].merge_with(
                    dream_candidates[j], BreathPhase.DREAM
                )
                dream_motifs.append(dream_motif)
        
        # Find fragments that might resonate with dream motifs
        for motif in dream_motifs:
            # Add dream motif to library
            self.motif_detector.create_motif(
                name=motif.name,
                category=motif.category,
                associations=motif.associations,
                description=f"Dream motif combining {', '.join(motif.archetypal_roots)}",
                roots=motif.archetypal_roots
            )


# Helper function to create a library node instance
def initialize_library_node(root_path: Optional[str] = None) -> LibraryNode:
    """
    Initialize and return a LibraryNode instance.
    
    Args:
        root_path: Optional path to data directory
        
    Returns:
        Initialized LibraryNode
    """
    library = LibraryNode(root_path=root_path)
    
    # Set initial breath phase
    library.current_breath = BreathPhase.REST
    
    return library