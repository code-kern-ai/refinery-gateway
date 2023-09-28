REFERENCE_CHUNKS = """
def ac(record):
    # e.g. use spacy sentences to create a list
    return [r.text for r in record["@@target_attribute@@"].sents]
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
