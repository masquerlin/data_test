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
file_url = os.getenv('FILE_URL',f"http://localhost:{port}")
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
HOST = '0.0.0.0'
USER = 'wangdalin'
PASSWORD = 'wangdalin@666'
DATABASE = 'transportation'
PORT = 5432  # PostgreSQL 默认端口
DATA_DIR = '/mnt/e/data_test/data/第二部分'  # sql 和 csv 文件都放在这里
db_url = f"postgresql://{USER}:{PASSWORD.replace('@', '%40')}@{HOST}:{PORT}/{DATABASE}"

bge_model_path = os.getenv('BGE_MODEL', '/model/bge-reranker-v2-m3',)

if __name__ == '__main__':
    pass