import os
from html.parser import HTMLParser
from submodules.model import UploadTask, enums
from submodules.model.business_objects import knowledge_term, organization
from submodules.model.business_objects import general
from controller.upload_task import manager as upload_task_manager
from submodules.s3 import controller as s3
import pandas as pd


def _parse_html_tables_to_dataframe(path: str) -> pd.DataFrame:
    """Parse the first HTML table from a file using stdlib html.parser only (no lxml).
    Avoids pd.read_html so we do not trigger lxml/XXE-related parsers.
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        html_content = f.read()

    class TableParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.in_table = False
            self.in_row = False
            self.in_cell = False
            self.current_row: list[str] = []
            self.rows: list[list[str]] = []
            self.current_cell_text: list[str] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag == "table":
                self.in_table = True
                self.rows = []
            elif self.in_table and tag == "tr":
                self.in_row = True
                self.current_row = []
            elif self.in_table and self.in_row and tag in ("td", "th"):
                self.in_cell = True
                self.current_cell_text = []

        def handle_endtag(self, tag: str) -> None:
            if tag == "table":
                self.in_table = False
            elif tag == "tr":
                if self.in_table and self.current_row:
                    self.rows.append(self.current_row)
                self.in_row = False
            elif tag in ("td", "th") and self.in_cell:
                self.current_row.append("".join(self.current_cell_text).strip())
                self.in_cell = False

        def handle_data(self, data: str) -> None:
            if self.in_cell:
                self.current_cell_text.append(data)

    parser = TableParser()
    parser.feed(html_content)
    if not parser.rows:
        return pd.DataFrame()
    return pd.DataFrame(parser.rows[1:], columns=parser.rows[0])


def import_knowledge_base_file(project_id: str, task: UploadTask) -> None:
    upload_task_manager.update_task(project_id, task.id, state=enums.UploadStates.PENDING.value)
    general.commit()

    file_type = task.file_name.rsplit("_", 1)[0].rsplit(".", 1)[1]
    list_id = task.file_name.rsplit("_", 1)[1]

    existing_items = knowledge_term.get_by_knowledge_base(list_id)
    existing_names = {str(row.value) for row in existing_items}
    org_id = organization.get_id_by_project_id(project_id)

    download_file_name = s3.download_object(
        org_id, project_id + "/" + f"{task.id}/{task.file_name}", file_type
    )
    if file_type in ["csv", "txt", "text"]:
        df = pd.read_csv(download_file_name)
    elif file_type == "xlsx":
        df = pd.read_excel(download_file_name)
    elif file_type == "html":
        df = _parse_html_tables_to_dataframe(download_file_name)
    elif file_type == "json":
        df = pd.read_json(download_file_name)

    if os.path.exists(download_file_name):
        os.remove(download_file_name)

    try:
        import_exported_file(project_id, list_id, df)
    except Exception:
        general.rollback()
        term_list = set(df["value"].unique())
        to_add = term_list - existing_names
        knowledge_term.create_by_value_list(
            project_id, list_id, to_add, with_commit=True
        )

    upload_task_manager.update_task(project_id, task.id, state=enums.UploadStates.IN_PROGRESS.value)
    task.state = enums.UploadStates.DONE.value
    general.commit()


def import_exported_file(
    project_id: str, knowledge_base_id: str, df: pd.DataFrame
) -> None:
    """Make use of the EAFP principle here
    try to import by making use of the structure of exported knowledge terms
    if the structure does not fit an exception gets raised
    and the original import flow is continued
    """
    for value in df["terms"]:
        term = knowledge_term.get_by_value(knowledge_base_id, value.get("value"))
        if term:
            term.comment = value["comment"]
            term.blacklisted = value["blacklisted"]
        else:
            knowledge_term.create(
                project_id,
                knowledge_base_id,
                value["value"],
                value["comment"],
                value["blacklisted"],
            )
