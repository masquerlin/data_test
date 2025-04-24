import requests
import json

def send_sql_request(question, host="http://localhost", port=8067):
    """
    发送 POST 请求到 /sql 端点，生成 SQL 并获取结果。

    :param question: 用户的问题或查询语句
    :param host: 服务器地址，默认为 "http://localhost"
    :param port: 服务器端口号，默认为 8067
    :return: 返回包含 SQL、数据文件 URL 和图表文件 URL 的字典
    """
    # 构建完整的 URL
    url = f"{host}:{port}/sql"

    # 定义要发送的 JSON 数据
    data = {
        "question": question
    }

    try:
        # 发送 POST 请求
        response = requests.post(url, json=data)

        # 检查请求是否成功
        if response.status_code == 200:
            # 解析返回的 JSON 数据
            result = response.json()
            return result
        else:
            # 如果请求失败，抛出异常或返回错误信息
            return {
                "error": f"请求失败，状态码: {response.status_code}",
                "message": response.text
            }
    except requests.exceptions.RequestException as e:
        # 处理网络请求异常
        return {
            "error": "网络请求异常",
            "message": str(e)
        }

# 示例调用
if __name__ == "__main__":
    question = "在什么路段出现比较多的违停?"
    result = send_sql_request(question)
    if "error" in result:
        print("请求失败:", result)
    else:
        print("生成的SQL语句:", result["sql"])
        print("数据文件URL:", result["data"])
        print("图表文件URL:", result["fig"])