from submodules.model.business_objects import upload_task
import os, shutil

def clean_up_database() -> None:
    upload_task.remove_all_keys(with_commit=True)

def clean_up_disk() -> None:
    folder = 'tmp'
    for filename in os.listdir(folder):
        if filename == '.gitkeep':
            continue
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))