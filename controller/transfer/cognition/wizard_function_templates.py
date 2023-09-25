REFERENCE_CHUNKS = """
def ac(record):
    # e.g. use spacy sentences to create a list
    return [r.text for r in record["reference"].sents]
"""
