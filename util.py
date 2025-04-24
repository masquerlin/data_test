
import json
import csv
import yaml
from datetime import datetime
import pandas as pd
import re
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


if __name__ == '__main__':
    pass