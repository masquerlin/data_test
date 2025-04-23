import plotly
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from config import llm_config
import re, autogen
from agents import plot_agent
def extract_python_code(markdown_string: str) -> str:
        # Strip whitespace to avoid indentation errors in LLM-generated code
        markdown_string = markdown_string.strip()

        # Regex pattern to match Python code blocks
        pattern = r"```[\w\s]*python\n([\s\S]*?)```|```([\s\S]*?)```"

        # Find all matches in the markdown string
        matches = re.findall(pattern, markdown_string, re.IGNORECASE)

        # Extract the Python code from the matches
        python_code = []
        for match in matches:
            python = match[0] if match[0] else match[1]
            python_code.append(python.strip())

        if len(python_code) == 0:
            return markdown_string

        return python_code[0]
def sanitize_plotly_code(raw_plotly_code: str) -> str:
        # Remove the fig.show() statement from the plotly code
        plotly_code = raw_plotly_code.replace("fig.show()", "")

        return plotly_code

async def generate_plotly_code(
        question: str = None, sql: str = None, df_metadata: str = None, **kwargs
    ) -> str:
    user_msg = """user's question: {question};
                    The DataFrame was produced using this query: {sql};
                    pandas DataFrame 'df': \n{df_metadata}""".format(question=question, sql=sql, df_metadata=df_metadata)

    plotly_code = await plot_agent.a_generate_reply(messages=[{'role':'user', 'content': user_msg}])

    return sanitize_plotly_code(extract_python_code(plotly_code))

async def get_plotly_figure(
        plotly_code: str, df: pd.DataFrame, dark_mode: bool = True
    ) -> plotly.graph_objs.Figure:
        """
        **Example:**
        ```python
        fig = vn.get_plotly_figure(
            plotly_code="fig = px.bar(df, x='name', y='salary')",
            df=df
        )
        fig.show()
        ```
        Get a Plotly figure from a dataframe and Plotly code.

        Args:
            df (pd.DataFrame): The dataframe to use.
            plotly_code (str): The Plotly code to use.

        Returns:
            plotly.graph_objs.Figure: The Plotly figure.
        """
        ldict = {"df": df, "px": px, "go": go}
        try:
            exec(plotly_code, globals(), ldict)

            fig = ldict.get("fig", None)
        except Exception as e:
            # Inspect data types
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            categorical_cols = df.select_dtypes(
                include=["object", "category"]
            ).columns.tolist()

            # Decision-making for plot type
            if len(numeric_cols) >= 2:
                # Use the first two numeric columns for a scatter plot
                fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1])
            elif len(numeric_cols) == 1 and len(categorical_cols) >= 1:
                # Use a bar plot if there's one numeric and one categorical column
                fig = px.bar(df, x=categorical_cols[0], y=numeric_cols[0])
            elif len(categorical_cols) >= 1 and df[categorical_cols[0]].nunique() < 10:
                # Use a pie chart for categorical data with fewer unique values
                fig = px.pie(df, names=categorical_cols[0])
            else:
                # Default to a simple line plot if above conditions are not met
                fig = px.line(df)

        if fig is None:
            return None

        if dark_mode:
            fig.update_layout(template="plotly_dark")

        return fig
    
async def plot(question: str = None, sql: str = None, df: pd.DataFrame = None,):
    plot_code = await generate_plotly_code(question=question, sql=sql, df_metadata=f"Running df.dtypes gives:\n {df.dtypes}")
    fig = await get_plotly_figure(plotly_code=plot_code, df=df, dark_mode=False)
    return fig