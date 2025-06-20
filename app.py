import streamlit as st
import pandas as pd
import sqlite3
import openai
import matplotlib.pyplot as plt

# Groq API
openai.api_key = "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"
openai.api_base = "https://api.groq.com/openai/v1"


# App Layout
st.set_page_config(page_title="SQL Chatbot", layout="wide")
st.title("Data Analytics Chatbot ")

uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.subheader("Preview of Data")
    st.dataframe(df.head())

    # In-memory SQLite DB
    conn = sqlite3.connect(":memory:")
    df.to_sql("my_table", conn, index=False, if_exists='replace')

    # Get user question
    with st.form("question_form"):
        user_question = st.text_input("Ask a question about your data:")

        col1, col2 = st.columns([1, 15])
        with col1:
                reset = st.form_submit_button("Reset")
        with col2:
                submitted = st.form_submit_button("Submit")

    if reset:
        st.session_state.clear()
        st.rerun()

    if submitted and user_question:
        # the prompt
        schema = ", ".join(df.columns)
        prompt = f"""You are an expert data analyst.
                        Generate an SQL query (SQLite syntax only) for the question:
                        '{user_question}'
                        Table name is: my_table
                        Columns are: {schema}
                        Only return valid SQL query. No explanation or markdown.
                        """

        with st.spinner("Generating SQL with Groq..."):
            try:
                response = openai.ChatCompletion.create(
                    model="llama3-8b-8192",
                    messages=[{"role": "user", "content": prompt}]
                )
                sql_query = response['choices'][0]['message']['content'].strip().strip("`").strip()
                st.code(sql_query, language="sql")

                # Allow user to edit SQL before running
                edited_query = st.text_area("Edit SQL query before execution (optional):", value=sql_query, height=300)

                # Run the edited SQL
                try:
                    result = pd.read_sql_query(edited_query, conn)
                    st.subheader("Query Output")

                    col1, col2 = st.columns([1, 3])

                    with col1:
                        st.markdown("**Query Result**")
                        st.dataframe(result)

                    with col2:
                        if len(result.columns) == 2:
                            st.markdown("**Visualization**")

                            plot_type = st.selectbox("Choose Plot Type", ["bar", "line", "area", "scatter"])

                            plt.style.use("ggplot")
                            fig, ax = plt.subplots(figsize=(4, 2))

                            x_col = result.columns[0]
                            y_col = result.columns[1]

                            # Check if y is numeric
                            if not pd.api.types.is_numeric_dtype(result[y_col]):
                                st.warning(f"Cannot plot because '{y_col}' is not numeric.")
                            elif plot_type == "scatter" and not pd.api.types.is_numeric_dtype(result[x_col]):
                                st.warning("Scatter plot needs both x and y to be numeric.")
                            else:
                                try:
                                    if plot_type != "scatter":
                                        result.plot(kind=plot_type, x=x_col, y=y_col, ax=ax, legend=False)
                                    else:
                                        result.plot(kind="scatter", x=x_col, y=y_col, ax=ax)

                                    ax.tick_params(axis='both', which='major', labelsize=4)
                                    ax.set_xlabel(x_col, fontsize=6)
                                    ax.set_ylabel(y_col, fontsize=6)
                                    plt.xticks(rotation=45)
                                    st.pyplot(fig, use_container_width=False)

                                except Exception as plot_err:
                                    st.error(f"Plotting Error: {plot_err}")


                except Exception as sql_error:
                    st.error(f"SQL Execution Error: {sql_error}")

            except Exception as e:
                st.error(f"API or Response Error: {e}")
