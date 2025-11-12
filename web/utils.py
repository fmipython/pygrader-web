import datetime
import os
import shutil
import zipfile
from multiprocessing import Queue

import pandas as pd
from streamlit.runtime.uploaded_file_manager import UploadedFile

import web.constants as const
from grader.checks.abstract_check import ScoredCheckResult, NonScoredCheckResult, CheckResult
from grader.grader import Grader, GraderError
from grader.utils.logger import setup_logger


def run_grader(conn: Queue, run_id: str) -> None:
    """
    Run the grading process and send results back through the connection.
    :param conn: The multiprocessing queue to send results through.
    :param run_id: A unique identifier for the grading run.
    """
    log = setup_logger(run_id)

    root_dir = os.getenv("ROOT_DIR", "/tmp/pygrader")
    project_root = os.path.join(root_dir, const.PROJECT_DIR.format(run_id=run_id))

    os.makedirs(project_root, exist_ok=True)

    if "CONFIG_PATH" not in os.environ:
        conn.put((1, []))
        return

    config_path = os.getenv("CONFIG_PATH", "")

    try:
        grader = Grader(run_id, project_root, config_path, log)
    except GraderError:
        conn.put((1, []))
        return

    results = grader.grade()

    conn.put((0, results))


def convert_results(check_results: list[CheckResult]) -> pd.DataFrame:
    """
    Convert a list of CheckResult objects into a pandas DataFrame.

    :param check_results: The list of CheckResult objects to convert.
    :return: A pandas DataFrame representing the check results.
    """
    return pd.DataFrame([__convert_result(result) for result in check_results])


def __convert_result(check_result: CheckResult) -> dict:
    match check_result:
        case ScoredCheckResult(name, score, max_score):
            return {
                "name": name,
                "score": score,
                "max_score": max_score,
            }
        case NonScoredCheckResult(name, result):
            return {
                "name": name,
                "result": result,
            }
        case _:
            raise ValueError("Unknown CheckResult type")


def generate_run_id() -> str:
    """
    Generate a unique run ID based on the current date and time.
    :return: A string representing the run ID.
    """
    now = datetime.datetime.now()
    return "run" + now.strftime("%y%m%d%H%M%S") + str(now.microsecond)[:3]


def handle_upload(file_obj: UploadedFile, run_id: str) -> None:
    """
    Handle the uploaded zip file by extracting its contents to a staging directory.
    :param file_obj: The uploaded zip file object.
    """

    root_dir = os.getenv("ROOT_DIR", "/tmp/pygrader")

    if not os.path.exists(root_dir):
        os.makedirs(root_dir)

    zip_file_path = os.path.join(root_dir, const.ARCHIVE_NAME.format(run_id=run_id))
    with open(zip_file_path, "wb") as f:
        f.write(file_obj.getbuffer())

    project_dir = os.path.join(root_dir, const.PROJECT_DIR.format(run_id=run_id))
    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
        zip_ref.extractall(project_dir)

    os.remove(zip_file_path)


def collect_log(run_id: str) -> None:
    """
    Collect the log file associated with the given run ID and move it to the logs directory.

    :param run_id: The unique identifier for the grading run.
    """
    logs_dir_path = os.path.join(os.getenv("ROOT_DIR", "/tmp/pygrader"), const.LOGS_DIR)
    if not os.path.exists(logs_dir_path):
        os.makedirs(logs_dir_path)

    shutil.copy2(f"{run_id}.log", logs_dir_path)


def remove_project(run_id: str) -> None:
    """
    Remove the project directory and log file associated with the given run ID.
    :param run_id: The unique identifier for the grading run.
    """
    root_dir = os.getenv("ROOT_DIR", "/tmp/pygrader")
    project_dir = os.path.join(root_dir, const.PROJECT_DIR.format(run_id=run_id))

    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)
