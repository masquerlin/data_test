# put your config here
import argparse, os, sys
from dotenv import load_dotenv
def load_env_from_single_arg():
    """
    通过命令行参数 --env <路径> 加载环境变量文件。
    若不传 --env，则不加载。
    """
    if "--env" in sys.argv:
        try:
            idx = sys.argv.index("--env")
            env_path = sys.argv[idx + 1]
            load_dotenv(dotenv_path=env_path)
            print(f"✔ 加载环境变量文件: {env_path}")
            return True, env_path
        except IndexError:
            print("❌ 错误：--env 后缺少路径")
    else:
        print("⚠ 未传 --env，未加载任何环境变量")
    return False, None
load_env_from_single_arg()

port = int(os.getenv('PORT',8067))
file_url = os.getenv('FILE_URL',f"http://10.41.1.220:{port}")
api_key = os.getenv('API_KEY')
base_url = os.getenv('BASE_URL','https://dashscope.aliyuncs.com/compatible-mode/v1')
llm_config={
    "config_list": [
        {
            "model": os.getenv('MODEL', 'qwen-max'), # Same as in vLLM command
            "api_key": api_key, # Not needed
            "base_url": base_url  # Your vLLM URL, with '/v1' added
        }
    ],
    "cache_seed": None, # Turns off caching, useful for testing different models
    "temperature": float(os.getenv('MODEL_TEM_TURE',0.5)),
}
llm_config_ds={
    "config_list": [
        {
            "model": os.getenv('THINK_MODEL', 'deepseek-r1'), # Same as in vLLM command
            "api_key": api_key, # Not needed
            "base_url": base_url  # Your vLLM URL, with '/v1' added
        }
    ],
    "cache_seed": None, # Turns off caching, useful for testing different models
    "temperature": float(os.getenv('THINK_MODEL_TEM_TURE',0.7)),
}
llm_config_plus={
    "config_list": [
        {
            "model": os.getenv('PLUS_MODEL', 'qwen-plus'), # Same as in vLLM command
            "api_key": api_key, # Not needed
            "base_url": base_url  # Your vLLM URL, with '/v1' added
        }
    ],
    "cache_seed": None, # Turns off caching, useful for testing different models
    "temperature": float(os.getenv('PLUS_MODEL_TEM_TURE',0.7)),
}

llm_config_turbo={
    "config_list": [
        {
            "model": os.getenv('TURBO_MODEL', 'qwen-plus'), # Same as in vLLM command
            "api_key": api_key, # Not needed
            "base_url": base_url  # Your vLLM URL, with '/v1' added
        }
    ],
    "cache_seed": None, # Turns off caching, useful for testing different models
    "temperature": float(os.getenv('TURBO_MODEL_TEM_TURE',0.7)),
}

llm_dict = {'deepseek':llm_config_ds, 'turbo':llm_config_turbo, 'plus':llm_config_plus,'max':llm_config,}
STATIC_DIR = os.getenv('STATIC_DIR','/workspace')
BASE_UPLOAD_DIRECTORY = os.getenv('BASE_UPLOAD_DIRECTORY','/app/workspace')

db_list_2 = [{
            "host": "10.41.1.220",
            "database": "sale_database",
            "user": "sa",
            "password": "wangdalin@666",
            "port": "1433"
        },
        {
            "host": "10.41.1.220",
            "database": "cooperation",
            "user": "sa",
            "password": "wangdalin@666",
            "port": "1433",
        }]

db_cn_map = {'sale_database':{
    'name':'销售数据库','table_cn_map':{
        'sale':'销售数据'}}, 
        'cooperation':{'name':'商业往来数据库','table_cn_map':{
        'SupplierPurchases':'供应商数据'}}}
def reverse_cn_map(cn_map):
    # 创建中文找英文的结构
    en_to_cn_map = {}
    for db_key, db_value in cn_map.items():
        db_name_cn = db_value.get('name', db_key)
        en_to_cn_map[db_name_cn] = {
            'name': db_key,
            'table_cn_map': {}
        }

        for table_key, table_value in db_value['table_cn_map'].items():
            table_name_cn = table_value
            en_to_cn_map[db_name_cn]['table_cn_map'][table_name_cn] = table_key
    return en_to_cn_map
db_en_map = reverse_cn_map(db_cn_map)
bge_model_path = os.getenv('BGE_MODEL', '/model/bge-reranker-v2-m3',)
if __name__ == '__main__':
    db_en_map = reverse_cn_map(db_cn_map)
    print(db_en_map)