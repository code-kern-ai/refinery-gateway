from submodules.model.business_objects import upload_task


def clean_up_database() -> None:
    upload_task.remove_all_keys(with_commit=True)