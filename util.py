
import json
import csv
import yaml
from datetime import datetime
from config import db_list_2
import pandas as pd
import re
from pyecharts.charts import Page, Grid, Bar, Line, Scatter, Pie
from pyecharts import options as opts
from pyecharts.globals import ThemeType
import pandas as pd
import numpy as np
from autogen.code_utils import CODE_BLOCK_PATTERN

def json_to_excel(jsons, excel_name):
    data = json.loads(jsons)
    df = pd.DataFrame(data)
    
    with pd.ExcelWriter(excel_name, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)

def json_to_dataframe(jsons):
    # 解析 JSON 字符串
    data = json.loads(jsons)
    
    # 将数据转换为 DataFrame
    df = pd.DataFrame(data)
    
    return df
def json_to_csv(jsons, csv_name):
    data = json.loads(jsons)
    fieldnames = list(data[0].keys())
    with open(csv_name, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # 写入列名
        writer.writeheader()

        # 写入数据
        writer.writerows(data)

def get_timestamp():
    now = datetime.now()
    hours = now.hour
    minutes = now.minute
    seconds = now.second

    short_time_mm_ss = f"{hours:02}_{minutes:02}_{seconds:02}"
    return short_time_mm_ss

def get_db_param(db_name):
    for db in db_list_2:
        print(db)
        if db['database'] == db_name:
            return db

    return None


def write_file(fname, content):
    with open(fname, "w") as f:
        f.write(content)


def write_json_file(fname, json_str: str):
    # convert ' to "
    json_str = json_str.replace("'", '"')

    # Convert the string to a Python object
    data = json.loads(json_str)

    # Write the Python object to the file as JSON
    with open(fname, "w") as f:
        json.dump(data, f, indent=4)


def write_yml_file(fname, json_str: str):
    # Try to replace single quotes with double quotes for JSON
    cleaned_json_str = json_str.replace("'", '"')

    # Safely convert the JSON string to a Python object
    try:
        data = json.loads(cleaned_json_str)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return

    # Write the Python object to the file as YAML
    with open(fname, "w") as f:
        yaml.dump(data, f)

def extract_code_blocks(message):
    """(Experimental) Extract code blocks from a message. If no code blocks are found,
    return an empty list.

    Args:
        message (str): The message to extract code blocks from.

    Returns:
        List[CodeBlock]: The extracted code blocks or an empty list.
    """
    if message == None:
        return 
    text = message
    match = re.findall(CODE_BLOCK_PATTERN, text, flags=re.DOTALL)
    if not match:
        return []
    code_blocks = []
    for lang, code in match:
        if lang == 'python' or lang == 'py':
            code_blocks.append(code)
    return code_blocks

def get_task(text):
    if isinstance(text, dict):
        text = text.get('content')
    result = []
    pattern = r'#(.*?)#'
    matches = re.findall(pattern, text)
    for i, match in enumerate(matches, 1):
            print(f"{match}")
            result.append(match)
    return result

class plot_data:
    def __init__(self):
        pass

    def auto_plot(self, df, filename):
        """
        Automatically generate plots for numeric and categorical columns in a DataFrame using pyecharts.

        Args:
            df (pandas.DataFrame): DataFrame containing data to plot.

        Returns:
            pyecharts.charts.Page: A Page object containing all generated charts.
        """
        time_index = pd.api.types.is_datetime64_any_dtype(df.index)
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        category_cols = df.select_dtypes(include=['object']).columns.tolist()
        time_cols = df.select_dtypes(include=[np.datetime64]).columns.tolist()

        # 创建Page对象
        page = Page(layout=Page.SimplePageLayout)
        page.page_title = "Data Visualization Report"

        # 通用的初始化选项，设置宽度为50%
        common_init_opts = opts.InitOpts(
            theme=ThemeType.LIGHT,
            width= "1900px",
            height= "1200px",
        )

        # 通用的全局选项
        # common_global_opts = {
        #     "toolbox_opts": opts.ToolboxOpts(),
        #     "datazoom_opts": [opts.DataZoomOpts()],
        # }
        common_global_opts = {
            # "legend_opts": opts.LegendOpts(pos_top="10%"),
            "toolbox_opts": opts.ToolboxOpts(pos_top="5%"),
            # "datazoom_opts": [opts.DataZoomOpts()],
        }
        charts = []
        # Distribution of Numeric Columns
        if len(numeric_cols) > 0:
            bar = (
                Bar(init_opts=common_init_opts)
                .add_xaxis(numeric_cols)
                .add_yaxis("Mean", df[numeric_cols].mean().tolist(), label_opts=opts.LabelOpts(position="top"))
                .add_yaxis("Median", df[numeric_cols].median().tolist(), label_opts=opts.LabelOpts(position="top"))
                .set_global_opts(
                    title_opts=opts.TitleOpts(title="Distribution of Numeric Columns", padding=[0, 0, 20, 0], pos_top="5%"),
                    xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-45)),
                    legend_opts=opts.LegendOpts(pos_top="10%"),
                    **common_global_opts
                )
            )
            charts.append(bar)

        # Scatter Plots for Numeric Columns
        if len(numeric_cols) > 1:
            for i in range(len(numeric_cols)-1):
                for j in range(i+1, len(numeric_cols)):
                    scatter = (
                        Scatter(init_opts=common_init_opts)
                        .add_xaxis(df[numeric_cols[i]].tolist())
                        .add_yaxis(
                            numeric_cols[j],
                            df[[numeric_cols[i], numeric_cols[j]]].values.tolist(),
                            label_opts=opts.LabelOpts(is_show=False),
                        )
                        .set_global_opts(
                            title_opts=opts.TitleOpts(title=f"{numeric_cols[i]} vs {numeric_cols[j]} Scatter Plot", padding=[0, 0, 20, 0], pos_top="5%"),
                            xaxis_opts=opts.AxisOpts(type_="value", name=numeric_cols[i]),
                            yaxis_opts=opts.AxisOpts(type_="value", name=numeric_cols[j]),
                            legend_opts=opts.LegendOpts(pos_top="10%"),
                            **common_global_opts
                        )
                    )
                    charts.append(scatter)

        # Bar Charts for Categorical vs Numeric Columns
        if len(category_cols) > 0 and len(numeric_cols) > 0:
            for cat_col in category_cols:
                for num_col in numeric_cols:
                    bar = (
                        Bar(init_opts=common_init_opts)
                        .add_xaxis(df[cat_col].unique().tolist())
                        .add_yaxis(num_col, df.groupby(cat_col)[num_col].mean().tolist(), label_opts=opts.LabelOpts(position="top"))
                        .set_global_opts(
                            title_opts=opts.TitleOpts(title=f"{num_col} Distribution by {cat_col}", padding=[0, 0, 20, 0], pos_top="5%"),
                            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-45)),
                            legend_opts=opts.LegendOpts(pos_top="10%"),
                            **common_global_opts
                        )
                    )
                    charts.append(bar)

        # Time Series Plots
        if time_index or len(time_cols) > 0:
            if time_index:
                time_data = df.index
            elif len(time_cols) > 0:
                time_data = df[time_cols[0]]
            
            line = Line(init_opts=common_init_opts)
            line.add_xaxis(time_data.astype(str).tolist())
            for num_col in numeric_cols:
                line.add_yaxis(num_col, df[num_col].tolist(), is_smooth=True)
            line.set_global_opts(
                title_opts=opts.TitleOpts(title=f"{', '.join(numeric_cols)} Trends Over Time", padding=[0, 0, 20, 0], pos_top="5%"),
                xaxis_opts=opts.AxisOpts(type_="category", name="Time"),
                yaxis_opts=opts.AxisOpts(type_="value", name="Values"),
                legend_opts=opts.LegendOpts(pos_top="10%"),
                **common_global_opts
            )
            charts.append(line)

        # Pie Chart for Numeric Columns
        if len(numeric_cols) > 1:
            sum_values = df[numeric_cols].sum()
            pie = (
                Pie(init_opts=common_init_opts)
                .add(
                    series_name="Sum Distribution",
                    data_pair=list(zip(numeric_cols, sum_values.tolist())),
                    radius=["40%", "75%"],
                )
                .set_global_opts(
                    title_opts=opts.TitleOpts(title="Sum Distribution of Numeric Columns", padding=[0, 0, 20, 0], pos_top="5%"),
                    legend_opts=opts.LegendOpts(pos_left="15%", pos_top="15%"),
                    **common_global_opts
                )
                .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c}"))
            )
            charts.append(pie)

        for i in range(0, len(charts)):
            grid = Grid(init_opts=opts.InitOpts(theme=ThemeType.ROMA, width='700px',height='600px'))
            grid.add(charts[i], grid_opts=opts.GridOpts(pos_left="100px", pos_right="200px", pos_top="100px", pos_bottom='100px'))
            page.add(grid)
        page.render(filename)
        return f'data have saved in {filename}'

if __name__ == '__main__':
    pass