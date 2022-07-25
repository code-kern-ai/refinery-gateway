def get_restricted_endpoints():
    """
    List of restricted endpoints
    It is divided by blocks of endpoint groups with a single #
    Doubled use of # is to comment out endpoints of the blacklist

    # attribute -> name of block
    ## create_attribute endpoint commented out of blacklist

    """
    return [
        # attribute
        "create_attribute",
        "delete_attribute",
        "delete_attribute",
        "add_running_id",
        # data_slice
        "create_data_slice",
        "delete_data_slice",
        "update_data_slice",
        "create_oulier_slice",
        "update_slice_type_manual",
        # embedding
        "create_attribute_level_embedding",
        "create_token_level_embedding",
        "delete_embedding",
        # information_source
        "create_information_source",
        "delete_information_source",
        "toggle_information_source",
        "update_information_source",
        "set_all_information_source_selected",
        # knowledge_base 17
        "create_knowledge_base",
        "update_knowledge_base",
        "delete_knowledge_base",
        # knowledge_term
        "add_term_to_knowledge_base",
        "update_term",
        "delete_term",
        "blacklist_term",
        "blacklist_term",
        # labeling_task_label 25
        "create_label",
        "delete_label",
        "update_label_hotkey",
        "update_label_color",
        # labeling_task
        "create_labeling_task",
        "update_labeling_task",
        "delete_labeling_task",
        # misc
        "update_config",
        "post_event",
        # notification
        "create_notification",
        # organization 36
        "add_user_to_organization",
        "remove_user_from_organization",
        "create_organization",
        "delete_organization",
        # payload
        "create_payload",
        # project
        "create_project",
        "create_sample_project",
        "delete_project",
        "update_project_status",
        "update_project_name_and_description",
        "update_project_tokenizer",
        # record_label_association
        "add_classification_labels_to_record",
        "add_extraction_label_to_record",
        "set_gold_star_annotation_for_task",
        "delete_record_label_association_by_ids",
        "remove_gold_star_annotation_for_task",
        "update_rla_is_valid_manual",
        # record
        "delete_record",
        # tokenization_mutation
        "create_attribute_token_statistics",
        "tokenize_project",
        "tokenize_record",
        # transfer
        "export",
        "export_project",
        "export_knowledge_base",
        "upload_credentials_and_id",
        "prepare_project_export",
        "last_project_export_credentials",
        # upload task
        "upload_task_by_id",
        # zero shot
        "zero_shot_project",
        "create_zero_shot_information_source",
    ]
