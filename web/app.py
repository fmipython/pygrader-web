from multiprocessing import Queue, Process

import streamlit as st

from web.utils import run_grader, convert_results, generate_run_id, handle_upload, collect_log, remove_project


def run_app() -> None:
    """
    Main logic for the streamlit app.
    """
    st.title("Pygrader Web Interface")
    st.write("Welcome to the Pygrader web application.")

    st.divider()
    # Additional UI components and logic would go here

    project = st.file_uploader("Upload a project", type=["zip"])

    if project is not None:
        with st.spinner("Grading project..."):
            run_id = generate_run_id()

            handle_upload(project, run_id)

            queue = Queue()  # type: ignore
            grader = Process(target=run_grader, args=(queue, run_id))
            grader.start()
            grader.join()
            code, results = queue.get()
            queue.close()

            collect_log(run_id)
            remove_project(run_id)

            if code == 0:
                st.success("Project graded successfully!")
                st.dataframe(convert_results(results))
            else:
                st.error(f"An error occurred during grading. Run id: {run_id}")
    else:
        st.info("Please upload a project to get started.")
