from multiprocessing import Queue, Process

import streamlit as st

from web.utils import (
    run_grader,
    convert_results,
    generate_run_id,
    handle_upload,
    collect_log,
    remove_project,
    get_information_from_checks,
)


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
            queue = None
            grader = None

            try:
                project_root = handle_upload(project, run_id)

                queue = Queue()  # type: ignore
                grader = Process(target=run_grader, args=(queue, run_id, project_root))
                grader.start()
                grader.join()
                code, results, errors = queue.get()

                if code == 0:
                    st.success(f"Project graded successfully! Run id: {run_id}")
                    st.dataframe(convert_results(results))
                else:
                    st.error(f"An error occurred during grading. Run id: {run_id}")
                    if len(results) > 0:
                        st.error(f"Details: {'\n'.join(results)}")

                    if len(errors) > 0:
                        st.error(f"Errors: {'\n'.join(errors)}")

                check_to_info = get_information_from_checks(results)
                if len(check_to_info) > 0:
                    with st.expander("More information..."):
                        for check in check_to_info:
                            info, error = check_to_info[check]
                            if info != "":
                                with st.expander(f"{check}: info", icon=":material/info:"):
                                    st.write(info)
                            if error != "":
                                with st.expander(f"{check}: error", icon=":material/warning:"):
                                    st.write(error)

                # Add expander for errors
            finally:
                # Always cleanup resources
                if queue is not None:
                    queue.close()
                    queue.join_thread()
                if grader is not None:
                    grader.terminate()
                    grader.join()
                    grader.close()

                # Cleanup files
                collect_log(run_id)
                remove_project(run_id)
    else:
        st.info("Please upload a project to get started.")
