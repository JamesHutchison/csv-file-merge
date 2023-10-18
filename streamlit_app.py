from io import StringIO
from pathlib import Path
from typing import Any, Iterable, cast

import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.globals import set_debug
from langchain.llms.openai import OpenAI

from table_merger.table_mergers import (
    ColumnMapping,
    ColumnTransformations,
    TableMergeOperation,
    TableMergerManager,
)
from table_merger.types import IncomingColName, TemplateColName

set_debug(True)

st.set_page_config(page_title="CSV Merger")


@st.cache_data
def get_api_key() -> str:
    api_key_path = Path(".api_key")
    if api_key_path.exists():
        incoming_api_key = api_key_path.read_text().strip()
    else:
        incoming_api_key = ""
    return incoming_api_key


def api_key_change():
    if len(st.session_state["open_ai_key"]) == 51:
        st.session_state["valid_api_key"] = True
    else:
        st.session_state["valid_api_key"] = False


api_key = st.sidebar.text_input(
    "OpenAI API Key",
    key="open_ai_key",
    type="password",
    value=get_api_key(),
    max_chars=51,
    on_change=api_key_change,
).strip()

st.session_state["valid_api_key"] = len(st.session_state["open_ai_key"]) == 51

if "output_file" not in st.session_state:
    st.session_state["output_file"] = StringIO()
if "merger_manager" not in st.session_state:
    st.session_state["merger_manager"] = None
if "active_operation" not in st.session_state:
    st.session_state["active_operation"] = None
if "template_ready" not in st.session_state:
    st.session_state["template_ready"] = False
if "user_selected_mapping" not in st.session_state:
    st.session_state["user_selected_mapping"] = None
if "transform_code" not in st.session_state:
    st.session_state["transform_code"] = None
if "table_data" not in st.session_state:
    st.session_state["table_data"] = None


def get_llm():
    return OpenAI(
        openai_api_key=st.session_state["open_ai_key"],
        max_tokens=1000,
        temperature=0.0,
    )


def get_gpt4():
    return ChatOpenAI(
        model="gpt-4",
        openai_api_key=st.session_state["open_ai_key"],
        max_tokens=1000,
        temperature=0.0,
    )


def main() -> None:
    active_operation: TableMergeOperation | None
    column_transformation: ColumnTransformations | None

    st.title("CSV file merger")
    if st.session_state["valid_api_key"]:
        st.write(
            "To begin, upload a template file with the columns and sample data in the format you require."
        )
        template_file = st.file_uploader("Template CSV file")
    else:
        st.error("Invalid OpenAI API key")
        template_file = None
    template_ready = False
    if template_file is not None:
        table_merger, template_ready = handle_uploaded_template_file(
            StringIO(template_file.getvalue().decode("utf-8"))
        )
        st.session_state["merger_manager"] = table_merger
        st.session_state["template_ready"] = template_ready
    input_file = None
    if template_ready:
        st.write("Upload file to merge")
        input_file = st.file_uploader("Input CSV file")
    if input_file is not None:
        active_operation = None
        user_selected_mapping = {}
        if st.session_state.get("active_operation"):
            active_operation = st.session_state["active_operation"]
            user_selected_mapping = st.session_state["user_selected_mapping"]
        else:
            result = handle_uploaded_input_file(StringIO(input_file.getvalue().decode("utf-8")))
            if result:
                active_operation, user_selected_mapping = result
        st.session_state["active_operation"] = active_operation
        st.session_state["user_selected_mapping"] = user_selected_mapping

        if active_operation and not st.session_state.get("transform_code"):
            do_apply = st.button("Apply", key="apply_mapping")
            if do_apply and active_operation:
                if user_mapping := validated_user_column_mapping(
                    table_merger, user_selected_mapping
                ):
                    apply_column_mapping(active_operation, user_mapping)
                    # TODO: finish, need to present to user
                    column_transformation = (
                        active_operation.create_suggested_transformation_operations(get_gpt4())
                    )
                    st.session_state["transform_code"] = column_transformation
    if (column_transformation := st.session_state.get("transform_code")) and (
        active_operation := st.session_state.get("active_operation")
    ):
        st.markdown("## Column Transformations")

        # Define the header using columns
        header_cols = st.columns(2)
        header_cols[0].markdown("**Column Name**")
        header_cols[1].markdown("**Transformation**")

        # Dictionary to store user transformations
        user_transformations_dict = {}

        for row in column_transformation.transformations:
            with st.container():  # Ensures a fresh container for every loop iteration
                cols = st.columns(2)  # Create columns, adjust the number based on the layout

                # Display column name
                cols[0].markdown(row.column_name)

                # Display the transformation text field pre-populated with the transformation value
                user_transformations_dict[row.column_name] = cols[1].text_input(
                    "", value=row.python_lambda_body, key=row.column_name
                )

        # Single Apply button for all transformations
        if st.button("Apply transformations and add data", key="apply_transforms_and_add_data"):
            active_operation.assign_column_transformations(user_transformations_dict)
            write_to_streamlit(active_operation, active_operation.apply())
            ready_next_file()

    # Prepare data for Streamlit table
    table_data = st.session_state.get("table_data") or []
    if table_data:
        # Render the table in Streamlit
        st.table(table_data)


def ready_next_file() -> None:
    st.session_state["active_operation"] = None
    st.session_state["user_selected_mapping"] = None
    st.session_state["transform_code"] = None


def handle_uploaded_template_file(uploaded_file: StringIO) -> Any:
    if st.session_state.get("merger_manager"):
        table_merger = st.session_state["merger_manager"]
    else:
        table_merger = TableMergerManager(get_llm())
    if not (template_ready := st.session_state.get("template_ready", False)):
        template_ready = table_merger.ready(template_file=uploaded_file)
    return table_merger, template_ready


def handle_uploaded_input_file(
    uploaded_file: StringIO,
) -> tuple[TableMergeOperation, dict] | None:
    table_merger: TableMergerManager = st.session_state["merger_manager"]

    operation = table_merger.prep_csv_file_from_text_io(uploaded_file)
    if operation.errors:
        for error in operation.errors:
            st.error(error)
    else:
        st.write("Calculating info...")
        operation.create_suggested_merge_info(get_gpt4())
        assert operation.suggested_merge_info

        user_selected_mapping = {}
        column_map: ColumnMapping
        st.markdown("## Column Mapping")

        # Define the header using columns
        header_cols = st.columns(4)
        header_cols[1].markdown("**Template**")
        header_cols[0].markdown("**Incoming**")
        header_cols[2].markdown("**Confidence**")
        header_cols[3].markdown("**Resolve Ambiguity**")

        for column_map in operation.suggested_merge_info.column_mapping:
            with st.container():  # Ensures a fresh container for every loop iteration
                cols = st.columns(4)  # Create columns, adjust the number based on the layout

                cols[0].markdown(column_map.template_column)
                cols[1].markdown(column_map.incoming_column)
                cols[2].markdown(column_map.confidence)

                # For the selectbox
                if column_map.ambiguous_with:
                    column_names = list({column_map.incoming_column, *column_map.ambiguous_with})
                    column_names.sort()
                    selected_column = cols[3].selectbox(
                        "", column_names, index=column_names.index(column_map.incoming_column)
                    )
                else:
                    cols[3].write("")  # Empty space for alignment
                    selected_column = column_map.incoming_column
            user_selected_mapping[column_map.template_column] = selected_column

        return operation, user_selected_mapping

    for error in table_merger.errors:
        st.error(error)
    return None


def write_to_streamlit(operation: TableMergeOperation, rows: Iterable[dict]):
    column_mapping = operation.actual_column_mapping
    assert column_mapping

    # Read the CSV data using DictReader and map the columns
    # mapped_rows = []
    # reader = DictReader(operation.in_file)
    # for row in reader:
    #     mapped_row = {
    #         template_col: row[incoming_col]
    #         for template_col, incoming_col in column_mapping.items()
    #     }
    #     mapped_rows.append(mapped_row)

    table_data = st.session_state.get("table_data") or []
    template_column_names = [col.name for col in operation.template_column_info]
    if not table_data:
        table_data.append(template_column_names)

    # Append mapped rows to table_data, ensuring consistent order
    for mapped_row in rows:
        table_data.append([mapped_row[col_name] for col_name in template_column_names])

    st.session_state["table_data"] = table_data


def validated_user_column_mapping(
    table_merger: TableMergerManager,
    user_selected_mapping: dict[TemplateColName, IncomingColName | None],
) -> dict[TemplateColName, IncomingColName] | None:
    selected_incoming_columns = set(user_selected_mapping.values())

    if (
        len(selected_incoming_columns) == len(table_merger.template_columns)
        and None not in selected_incoming_columns
    ):
        return cast(dict[TemplateColName, IncomingColName], user_selected_mapping)
    return None


def apply_column_mapping(
    operation: TableMergeOperation,
    user_selected_mapping: dict[TemplateColName, IncomingColName],
) -> None:
    operation.assign_column_mapping(user_selected_mapping)


# def apply_column_header(template_columns: list[str]) -> None:
#     if not template_columns:
#         return
#     if st.session_state["dictwriter"] is None:
#         dictwriter = DictWriter(st.session_state["output_file"], fieldnames=template_columns)
#         st.session_state["dictwriter"] = dictwriter


# def write_input_to_output(operation: TableMergeOperation) -> None:
#     if st.session_state["dictwriter"] is None:
#         return
#     if not operation.errors:
#         dr = DictReader(operation.in_file)
#         dw: DictWriter = st.session_state["dictwriter"]
#         for row in dr:
#             dw.writerow(row)
#     else:
#         for error in operation.errors:
#             st.error(error)


if __name__ == "__main__":
    main()
