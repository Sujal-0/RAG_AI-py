"""Entity Extractor Engine.

Extracts Named Entities (Organizations, Products, Dates, etc.) using spaCy.
Abstracts the provider so an LLM or custom NER model could be plugged in later.
"""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("app")

class BaseEntityExtractor(ABC):
    @abstractmethod
    def extract(self, text: str) -> dict[str, list[str]]:
        pass

class SpacyEntityExtractor(BaseEntityExtractor):
    """Uses spaCy to extract entities deterministically."""
    
    def __init__(self):
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            logger.warning(f"spaCy NER unavailable: {e}. Entity extraction will be degraded.")
            self.nlp = None

    def extract(self, text: str) -> dict[str, list[str]]:
        entities = {
            "organizations": [],
            "people": [],
            "technologies": [],
            "dates": [],
            "locations": []
        }
        
        if not self.nlp:
            return entities
            
        doc = self.nlp(text)
        
        orgs = set()
        people = set()
        dates = set()
        locs = set()
        
        for ent in doc.ents:
            if ent.label_ == "ORG":
                orgs.add(ent.text)
            elif ent.label_ == "PERSON":
                people.add(ent.text)
            elif ent.label_ == "DATE":
                dates.add(ent.text)
            elif ent.label_ in ("GPE", "LOC"):
                locs.add(ent.text)
                
        entities["organizations"] = list(orgs)
        entities["people"] = list(people)
        entities["dates"] = list(dates)
        entities["locations"] = list(locs)
        
        logger.debug(
            "Entity Extraction Complete", 
            extra={"structured_log": True, "stage": "EntityExtractor", "entities": entities}
        )
        
        return entities
