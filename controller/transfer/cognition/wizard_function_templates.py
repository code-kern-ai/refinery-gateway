REFERENCE_CHUNKS_SENT = """
def ac(record):
    # e.g. use spacy sentences to create a list
    return [r.text for r in record["@@target_attribute@@"].sents]
"""

REFERENCE_CHUNKS_SPLIT = """
def ac(record):
    splits = [t.strip() for t in record["@@target_attribute@@"].text.split("\\n")]
    return [val for val in splits if len(val) > 0]
"""

MAPPING_WRAPPER = """
def @@target_name@@(record):
    #this is a wrapper to map the labels to your project
    result = bricks_base_function(record)
    if result in my_custom_mapping:
        result = my_custom_mapping[result]
    if result:
        return result
"""
