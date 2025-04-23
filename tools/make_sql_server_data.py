import os
import psycopg2
import pandas as pd
from datetime import datetime
import numpy as np
# PostgreSQL 配置
HOST = '0.0.0.0'
USER = 'wangdalin'
PASSWORD = 'wangdalin@666'
DATABASE = 'transportation'
PORT = 5432  # PostgreSQL 默认端口

DATA_DIR = '/mnt/e/data_test/data/第二部分'  # sql 和 csv 文件都放在这里
db_url = f"postgresql://{USER}:{PASSWORD.replace('@', '%40')}@{HOST}:{PORT}/{DATABASE}"
def insert_data():
    # 连接数据库
    conn = psycopg2.connect(host=HOST, user=USER, password=PASSWORD, dbname=DATABASE, port=PORT)
    conn.autocommit = True
    cursor = conn.cursor()

    files = os.listdir(DATA_DIR)
    sql_files = {os.path.splitext(f)[0]: f for f in files if f.endswith('.sql')}
    csv_files = {os.path.splitext(f)[0]: f for f in files if f.endswith('.csv')}
    common_basenames = set(sql_files.keys()) & set(csv_files.keys())

    for base in common_basenames:
        sql_path = os.path.join(DATA_DIR, sql_files[base])
        csv_path = os.path.join(DATA_DIR, csv_files[base])

        print(f"\n处理文件对: {sql_files[base]} <-> {csv_files[base]}")
        with open(sql_path, 'r', encoding='utf-8') as f:
            create_sql = f.read()

        try:
            cursor.execute(create_sql)
            print(f"✅ 表 {base} 创建成功")
        except Exception as e:
            print(f"❌ 表 {base} 创建失败：{e}")
            continue
        # 读取CSV文件
        df = pd.read_csv(csv_path)
        print(f"数据类型信息:\n{df.dtypes}")
        
        # 自定义日期时间转换函数
        def convert_datetime(date_str):
            if pd.isna(date_str) or date_str is None or date_str == 'nan' or date_str == 'nat':
                return None
                
            if not isinstance(date_str, str):
                return date_str
                
            try:
                # 检查是否包含毫秒
                if '.' in date_str:
                    # 格式如 "29/4/2022 23:26:52.831085"
                    dt = datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S.%f")
                else:
                    # 格式如 "27/9/2022 16:24:40"
                    dt = datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
                return dt
            except ValueError:
                try:
                    # 尝试其他可能的格式
                    dt = pd.to_datetime(date_str, dayfirst=True)
                    return dt.to_pydatetime()
                except:
                    # 如果转换失败，返回原值
                    return date_str
        
        # 处理所有NaN和NaT值
        df = df.replace({np.nan: None, pd.NaT: None})
        # 处理字符串'nan'和'nat'值
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].apply(lambda x: None if isinstance(x, str) and x.lower() in ['nan', 'nat'] else x)
        
        # 检查并转换日期时间列
        for col in df.columns:
            # 检查列中是否包含可能的日期时间数据
            non_null_values = df[col].dropna()
            if len(non_null_values) > 0:
                sample_val = non_null_values.iloc[0]
                if isinstance(sample_val, str) and ('/' in sample_val or '-' in sample_val) and (':' in sample_val):
                    try:
                        # 使用自定义函数转换日期格式
                        df[col] = df[col].apply(convert_datetime)
                        print(f"转换日期时间列: {col}")
                    except Exception as e:
                        print(f"无法转换日期时间列 {col}: {e}")
        
        # 检查整数列的范围，并根据需要调整大数值
        for col in df.select_dtypes(include=['int64', 'float64']).columns:
            non_null_values = df[col].dropna()
            if len(non_null_values) > 0:
                max_val = non_null_values.max()
                if max_val > 2147483647:  # PostgreSQL int4 (INTEGER) 的最大值
                    print(f"警告: 列 {col} 包含大于INTEGER最大值的数据，将转换为BIGINT兼容格式")
                    # 将数据转换为字符串以避免在Python中截断
                    df[col] = df[col].apply(lambda x: str(int(x)) if pd.notnull(x) else None)
        
        cols = ', '.join(df.columns)
        placeholders = ', '.join(['%s'] * len(df.columns))
        insert_sql = f'INSERT INTO {base} ({cols}) VALUES ({placeholders})'

        error_count = 0
        success_count = 0
        
        for i, (_, row) in enumerate(df.iterrows()):
            # 将行数据转换为列表
            values = []
            for val in row:
                if isinstance(val, pd.Timestamp):
                    values.append(val.to_pydatetime())
                elif pd.isna(val):
                    values.append(None)
                else:
                    values.append(val)
            
            try:
                cursor.execute(insert_sql, tuple(values))
                success_count += 1
                if success_count % 1000 == 0:
                    print(f"已成功插入 {success_count} 行数据")
            except Exception as e:
                error_count += 1
                if error_count <= 5:  # 只打印前几个错误，避免日志过多
                    print(f"第 {i+1} 行插入失败: {e}")
                    print(f"失败的行数据: {values}")
                elif error_count == 6:
                    print("更多错误被省略...")
        
        if error_count > 0:
            print(f"❌ 数据插入 {base} 部分失败: {error_count} 行失败, {success_count} 行成功")
            conn.rollback()
        else:
            print(f"✅ 数据插入 {base} 全部成功: {success_count} 行")

    cursor.close()
    conn.close()
def make_database():
    # 连接默认数据库创建 transportation 数据库
    conn = psycopg2.connect(host=HOST, user=USER, password=PASSWORD, dbname='postgres', port=PORT)
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        cursor.execute(f"CREATE DATABASE {DATABASE}")
        print(f"✅ 数据库 {DATABASE} 创建成功")
    except Exception as e:
        print(f"❌ 创建数据库失败：{e}")

    cursor.close()
    conn.close()

# 示例调用
# make_database()
insert_data()
