import datetime
import os
import shutil
import zipfile
from multiprocessing import Queue
from pathlib import Path

import grader.utils.constants as grader_const
import pandas as pd
from grader.exceptions import GraderError
from grader.grader import Grader, GradingResult
from grader.models.check_result import CheckResult, NonScoredCheckResult, ScoredCheckResult
from grader.utils.logger import setup_logger
from grader.utils.virtual_environment import VirtualEnvironmentError
from streamlit.runtime.uploaded_file_manager import UploadedFile

import web.constants as const


def run_grader(conn: Queue, run_id: str, project_root: str) -> None:
    """
    Run the grading process and send results back through the connection.
    :param conn: The multiprocessing queue to send results through.
    :param run_id: A unique identifier for the grading run.
    """
    log = setup_logger(run_id)

    os.makedirs(project_root, exist_ok=True)

    if "CONFIG_PATH" not in os.environ:
        conn.put((1, [], []))
        return

    config_path = os.getenv("CONFIG_PATH", "")

    try:
        grader = Grader(logger=log, config_path=config_path)
    except (GraderError, VirtualEnvironmentError):
        conn.put((1, [], []))
        return

    try:
        results = grader.grade(project_root, run_id)
    except (GraderError, VirtualEnvironmentError) as exc:
        # TODO - Add exception message
        conn.put((1, [], [str(exc)]))
        return

    conn.put((0, results, []))


def convert_results(grading_result: GradingResult) -> pd.DataFrame:
    """
    Convert a list of CheckResult objects into a pandas DataFrame.

    :param check_results: The list of CheckResult objects to convert.
    :return: A pandas DataFrame representing the check results.
    """
    results = pd.DataFrame([__convert_result(result) for result in grading_result.results])

    results = pd.concat(
        [
            results,
            pd.DataFrame(
                [{"name": "Total", "score": grading_result.total_score, "max_score": grading_result.max_score}]
            ),
        ],
    ).reset_index(drop=True)
    return results


def __convert_result(check_result: CheckResult) -> dict:
    match check_result:
        case ScoredCheckResult(name, score, _, _, max_score):
            return {
                "name": name,
                "score": score,
                "max_score": max_score,
            }
        case NonScoredCheckResult(name, result, _, _):
            return {"name": name, "result": result}
        case _:
            raise ValueError("Unknown CheckResult type")


def generate_run_id() -> str:
    """
    Generate a unique run ID based on the current date and time.

    :return: A string representing the run ID.
    """
    now = datetime.datetime.now()
    return "run" + now.strftime("%y%m%d%H%M%S") + str(now.microsecond)[:3]


def handle_upload(file_obj: UploadedFile, run_id: str) -> str:
    """
    Handle the uploaded zip file by extracting its contents to a staging directory.
    :param file_obj: The uploaded zip file object.
    """

    root_dir = os.getenv("ROOT_DIR", "/tmp/pygrader")

    if not os.path.exists(root_dir):
        os.makedirs(root_dir)

    zip_file_path = os.path.join(root_dir, const.ARCHIVE_NAME.format(run_id=run_id))

    try:
        # Use read() instead of getbuffer() to avoid holding references
        with open(zip_file_path, "wb") as f:
            f.write(file_obj.read())

        project_dir = os.path.join(root_dir, const.PROJECT_DIR.format(run_id=run_id))
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(project_dir)

        # If the unzipped folder contains only one subfolder (except MACOS subdirectories), use that as the project root
        project_root_dir = Path(project_dir)
        subdirs = [
            directory
            for directory in project_root_dir.iterdir()
            if directory.is_dir() and directory.name not in grader_const.IGNORE_DIRS
        ]

        if len(subdirs) == 1:
            project_dir = str(subdirs[0])
    finally:
        # Always remove the temporary zip file
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)

    return project_dir


def collect_log(run_id: str) -> None:
    """
    Collect the log file associated with the given run ID and move it to the logs directory.

    :param run_id: The unique identifier for the grading run.
    """
    logs_dir_path = os.path.join(os.getenv("ROOT_DIR", "/tmp/pygrader"), const.LOGS_DIR)
    if not os.path.exists(logs_dir_path):
        os.makedirs(logs_dir_path)

    log_file = f"{run_id}.log"
    if os.path.exists(log_file):
        shutil.move(log_file, logs_dir_path)


def remove_project(run_id: str) -> None:
    """
    Remove the project directory and log file associated with the given run ID.
    :param run_id: The unique identifier for the grading run.
    """
    root_dir = os.getenv("ROOT_DIR", "/tmp/pygrader")
    project_dir = os.path.join(root_dir, const.PROJECT_DIR.format(run_id=run_id))

    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)


def get_information_from_checks(results: GradingResult) -> dict[str, tuple[str, str]]:
    return {result.name: (result.info, result.error) for result in results.results}
