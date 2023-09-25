LANGUAGE_DETECTION = """
from langdetect import detect

ATTRIBUTE: str = "reference" #only text attributes

def Language(record):
    text = record[ATTRIBUTE].text # SpaCy document, hence we need to call .text to get the string
    return detect(text) # e.g. "en"
"""

REFERENCE_CHUNKS = """
def reference_chunks(record):
    # e.g. use spacy sentences to create a list
    return [r.text for r in record["reference"].sents]
"""
