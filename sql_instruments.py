import os, json, pymssql, asyncio, autogen, torch
from datetime import datetime
import util
from sklearn.metrics.pairwise import cosine_similarity
from transformers import BertTokenizer, BertModel
from config import STATIC_DIR, bge_model_path, base_url
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from agents import data_engineer
import pandas as pd
import psycopg2
from psycopg2.sql import SQL, Identifier
from plot import plot
bge_model = AutoModelForSequenceClassification.from_pretrained(bge_model_path)
bge_tokenizer = AutoTokenizer.from_pretrained(bge_model_path)

class AgentInstruments:
    """
    Base class for multli-agent instruments that are tools, state, and functions that an agent can use across the lifecycle of conversations
    """

    def __init__(self) -> None:
        self.session_id = None
        self.messages = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def sync_messages(self, messages: list):
        """
        Syncs messages with the orchestrator
        """
        raise NotImplementedError

    # def make_agent_chat_file(self, team_name: str):
    #     return os.path.join(self.root_dir, f"agent_chats_{team_name}.json")

    # def make_agent_cost_file(self, team_name: str):
    #     return os.path.join(self.root_dir, f"agent_cost_{team_name}.json")

    @property
    def root_dir(self):
        return os.path.join(STATIC_DIR, self.session_id)

class PostgresAgentInstruments(AgentInstruments):
    """
    Unified Toolset for the Postgres Data Analytics Multi-Agent System

    Advantages:
        - All agents have access to the same state and functions
        - Gives agent functions awareness of changing context
        - Clear and concise capabilities for agents
        - Clean database connection management

    Guidelines:
        - Agent Functions should not call other agent functions directly
            - Instead Agent Functions should call external lower level modules
        - Prefer 1 to 1 mapping of agents and their functions
        - The state lifecycle lives between all agent orchestrations
    """

    def __init__(self, db_url: str, session_id: str) -> None:
        super().__init__()

        self.db_url = db_url
        self.db = None
        self.session_id = session_id
        self.messages = []
        self.innovation_index = 0

    def __enter__(self):
        """
        Support entering the 'with' statement
        """
        self.reset_files()
        self.db = PostgresManager()
        self.db.connect_with_url(self.db_url)
        return self, self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Support exiting the 'with' statement
        """
        self.db.close()

    def sync_messages(self, messages: list):
        """
        Syncs messages with the orchestrator
        """
        self.messages = messages

    def reset_files(self):
        """
        Clear everything in the root_dir
        """

        # if it does not exist create it
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir)

        # for fname in os.listdir(self.root_dir):
        #     os.remove(os.path.join(self.root_dir, fname))

    def get_file_path(self, fname: str):
        """
        Get the full path to a file in the root_dir
        """
        return os.path.join(self.root_dir, fname)

    # -------------------------- Agent Properties -------------------------- #

    @property
    def run_sql_results_file(self):
        return self.get_file_path("run_sql_results.json")

    @property
    def sql_query_file(self):
        return self.get_file_path("sql_query.sql")

    # -------------------------- Agent Functions -------------------------- #

    def run_sql(self, sql: str) -> str:
        """
        Run a SQL query against the postgres database
        """
        results_as_json = self.db.run_sql(sql)

        fname = self.run_sql_results_file

        # dump these results to a file
        with open(fname, "w") as f:
            f.write(results_as_json)

        with open(self.sql_query_file, "w") as f:
            f.write(sql)

        return "Successfully delivered results to json file"

    def validate_run_sql(self):
        """
        validate that the run_sql results file exists and has content
        """
        fname = self.run_sql_results_file

        with open(fname, "r") as f:
            content = f.read()

        if not content:
            return False, f"File {fname} is empty"

        return True, ""

    def write_file(self, content: str):
        fname = self.get_file_path(f"write_file.txt")
        return util.write_file(fname, content)

    def write_json_file(self, json_str: str):
        fname = self.get_file_path(f"write_json_file.json")
        return util.write_json_file(fname, json_str)

    def write_yml_file(self, json_str: str):
        fname = self.get_file_path(f"write_yml_file.yml")
        return util.write_yml_file(fname, json_str)

    def write_innovation_file(self, content: str):
        fname = self.get_file_path(f"{self.innovation_index}_innovation_file.json")
        util.write_file(fname, content)
        self.innovation_index += 1
        return f"Successfully wrote innovation file. You can check my work."

    def validate_innovation_files(self):
        """
        loop from 0 to innovation_index and verify file exists with content
        """
        for i in range(self.innovation_index):
            fname = self.get_file_path(f"{i}_innovation_file.json")
            with open(fname, "r") as f:
                content = f.read()
                if not content:
                    return False, f"File {fname} is empty"

        return True, ""

class PostgresManager:
    def __init__(self):
        self.conn = None
        self.cur = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

    def connect_with_url(self, url):
        self.conn = psycopg2.connect(url)
        self.cur = self.conn.cursor()

    def upsert(self, table_name, _dict):
        columns = _dict.keys()
        values = [SQL("%s")] * len(columns)
        upsert_stmt = SQL(
            "INSERT INTO {} ({}) VALUES ({}) ON CONFLICT (id) DO UPDATE SET {}"
        ).format(
            Identifier(table_name),
            SQL(", ").join(map(Identifier, columns)),
            SQL(", ").join(values),
            SQL(", ").join(
                [
                    SQL("{} = EXCLUDED.{}").format(Identifier(k), Identifier(k))
                    for k in columns
                ]
            ),
        )
        self.cur.execute(upsert_stmt, list(_dict.values()))
        self.conn.commit()

    def delete(self, table_name, _id):
        delete_stmt = SQL("DELETE FROM {} WHERE id = %s").format(Identifier(table_name))
        self.cur.execute(delete_stmt, (_id,))
        self.conn.commit()

    def get(self, table_name, _id):
        select_stmt = SQL("SELECT * FROM {} WHERE id = %s").format(
            Identifier(table_name)
        )
        self.cur.execute(select_stmt, (_id,))
        return self.cur.fetchone()

    def get_all(self, table_name):
        select_all_stmt = SQL("SELECT * FROM {}").format(Identifier(table_name))
        self.cur.execute(select_all_stmt)
        return self.cur.fetchall()

    # def run_sql(self, sql):
    #     self.cur.execute(sql)
    #     return self.cur.fetchall()

    def run_sql(self, sql) -> str:
        self.cur.execute(sql)
        columns = [desc[0] for desc in self.cur.description]
        res = self.cur.fetchall()

        list_of_dicts = [dict(zip(columns, row)) for row in res]

        json_result = json.dumps(list_of_dicts, indent=4, default=self.datetime_handler)

        # # dump these results to a file
        # with open("results.json", "w") as f:
        #     f.write(json_result)

        return json_result

    def datetime_handler(self, obj):
        """
        Handle datetime objects when serializing to JSON.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)  # or just return the object unchanged, or another default value

    def get_table_definition(self, table_name):
        """
        获取表的详细信息，包括列名、数据类型和注释
        返回格式化的字符串，便于理解表结构和编写SQL
        """
        # 首先获取表的注释
        table_comment_query = """
        SELECT description
        FROM pg_catalog.pg_description pd
        JOIN pg_catalog.pg_class pc ON pd.objoid = pc.oid
        WHERE pc.relname = %s AND pd.objsubid = 0
        """
        self.cur.execute(table_comment_query, (table_name,))
        table_comment_result = self.cur.fetchone()
        table_comment = table_comment_result[0] if table_comment_result else ""
        
        # 获取列信息
        query = """
        SELECT 
            a.attname as column_name,
            format_type(a.atttypid, a.atttypmod) as data_type,
            pd.description as comment
        FROM pg_catalog.pg_attribute a
        JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_catalog.pg_description pd ON 
            pd.objoid = a.attrelid AND pd.objsubid = a.attnum
        WHERE c.relname = %s
            AND n.nspname = 'public'
            AND a.attnum > 0
            AND NOT a.attisdropped
        ORDER BY a.attnum
        """
        
        self.cur.execute(query, (table_name,))
        columns = self.cur.fetchall()
        
        # 格式化表信息
        if table_comment:
            result = f"- {table_name} 表 – {table_comment}：\n"
        else:
            result = f"- {table_name} 表：\n"
        
        for col in columns:
            col_name = col[0]
            data_type = col[1]
            comment = col[2] if col[2] else ""
            
            result += f"{col_name} | {data_type} | {comment}\n"
        
        return result

    def get_all_table_names(self):
        get_all_tables_stmt = (
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
        )
        self.cur.execute(get_all_tables_stmt)
        return [row[0] for row in self.cur.fetchall()]

    def get_table_definitions_for_prompt(self):
        table_names = self.get_all_table_names()
        definitions = []
        for table_name in table_names:
            definitions.append(self.get_table_definition(table_name))
        return "\n\n".join(definitions)

    def get_table_definitions_for_prompt_MOCK(self):
        return """CREATE TABLE users (
        id integer,
        created timestamp without time zone,
        updated timestamp without time zone,
        authed boolean,
        plan text,
        name text,
        email text
        );

        CREATE TABLE jobs (
        id integer,
        created timestamp without time zone,
        updated timestamp without time zone,
        parentuserid integer,
        status text,
        totaldurationms bigint
            );"""

    def get_table_definition_map_for_embeddings(self):
        table_names = self.get_all_table_names()
        definitions = {}
        for table_name in table_names:
            definitions[table_name] = self.get_table_definition(table_name)
        return definitions

    def close(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()


class DatabaseEmbedder:
    
    def __init__(self, db: PostgresManager, rerank: bool):
        # self.tokenizer = BertTokenizer.from_pretrained("bert-base-uncased", local_files_only=True)
        # self.model = BertModel.from_pretrained("bert-base-uncased", local_files_only=True)
        
        if rerank:
            self.model = bge_model
            self.tokenizer = bge_tokenizer
        else:
            self.tokenizer = BertTokenizer.from_pretrained("bert-base-uncased", local_files_only=True)
            self.model = BertModel.from_pretrained("bert-base-uncased", local_files_only=True)
        self.map_name_to_embeddings = {}
        self.map_name_to_table_def = {}
        self.db = db
        self.rerank = rerank

    def get_similar_table_defs_for_prompt(self, prompt: str, n_similar=5, n_foreign=0):
        map_table_name_to_table_def = self.db.get_table_definition_map_for_embeddings()
        for name, table_def in map_table_name_to_table_def.items():
            self.add_table(name, table_def)

        similar_tables = self.get_similar_tables(prompt, n=n_similar)

        table_definitions = self.get_table_definitions_from_names(similar_tables)

        if n_foreign > 0:
            foreign_table_names = self.db.get_foreign_tables(similar_tables, n=3)

            table_definitions = self.get_table_definitions_from_names(
                foreign_table_names + similar_tables
            )

        return table_definitions

    def add_table(self, table_name: str, text_representation: str):
        
        if self.rerank:
            self.map_name_to_embeddings[table_name] = None
        else:
            self.map_name_to_embeddings[table_name] = self.compute_embeddings(
                text_representation
            )

        self.map_name_to_table_def[table_name] = text_representation

    def compute_embeddings(self, text):

        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, padding=True, max_length=512
        )
        outputs = self.model(**inputs)
        return outputs["pooler_output"].detach().numpy()


    def get_similar_tables_via_rerank(self,query,n=5):
        self.model.eval()
        with torch.no_grad():
            result = {}
            for tab, tab_def in self.map_name_to_table_def.items():
                inputs_1 = self.tokenizer([[query, tab]], padding=True, truncation=True, return_tensors='pt', max_length=512)
                scores_1 = self.model(**inputs_1, return_dict=True).logits.view(-1, ).float()[0]
                inputs_2 = self.tokenizer([[query, tab_def]], padding=True, truncation=True, return_tensors='pt', max_length=512)
                scores_2 = self.model(**inputs_2, return_dict=True).logits.view(-1, ).float()[0]
                score = 0.7*scores_1 + 0.3*scores_2
                probs = torch.sigmoid(score)
                result[tab] = probs
            sorted_results = sorted(result.items(), key=lambda x: x[1], reverse=True)
            final_result = [x[0] for x in sorted_results]
            return final_result[:n]
    def get_similar_tables_via_embeddings(self, query, n=3):

        query_embedding = self.compute_embeddings(query)
        similarities = {
            table: cosine_similarity(query_embedding, emb)[0][0]
            for table, emb in self.map_name_to_embeddings.items()
        }
        return sorted(similarities, key=similarities.get, reverse=True)[:n]

    def get_similar_table_names_via_word_match(self, query: str):

        tables = []

        for table_name in self.map_name_to_table_def.keys():
            if table_name.lower() in query.lower():
                tables.append(table_name)

        return tables

    def get_similar_tables(self, query: str, n=3):

        if self.rerank:
            similar_tables_via_embeddings = self.get_similar_tables_via_rerank(query, n)
        else:
            similar_tables_via_embeddings = self.get_similar_tables_via_embeddings(query, n)
        similar_tables_via_word_match = self.get_similar_table_names_via_word_match(
            query
        )
        temp_list = similar_tables_via_embeddings + similar_tables_via_word_match
        unique_list = list(dict.fromkeys(temp_list))
        return unique_list

    def get_table_definitions_from_names(self, table_names: list) -> str:

        table_defs = [
            self.map_name_to_table_def[table_name] for table_name in table_names
        ]
        return "\n\n".join(table_defs)

class sql_analyze_father:
    def __init__(self, data_engineer:autogen.AssistantAgent, client_id: str, db_param: dict, table_name=[]) -> None:
        self.sql_generator = data_engineer
        self.db_param = db_param
        self.client_id = client_id
        self.table_name = table_name
    def get_sql(self, content):
        sql = content['content']
        if sql.startswith("SQL query:\n"):
            return sql.split(':')[1].strip()
        elif '```' in sql:
            return sql.split('```')[1].strip('sql')
        else:
            return sql
    
    def add_cap_ref(self,
        prompt: str, prompt_suffix: str, cap_ref: str, cap_ref_content: str, note: str, example: str
    ) -> str:
        new_prompt = f"""{prompt} {prompt_suffix}\n\n{cap_ref}\n\n{cap_ref_content}\n\n{note}\n\n{example}"""
        return new_prompt
    async def run_sql_analyze(self, raw_prompt):
        with PostgresAgentInstruments(self.db_param, self.client_id) as (agent_instruments, db):
            map_table_name_to_table_def = db.get_table_definition_map_for_embeddings()
            database_embedder = DatabaseEmbedder(db, rerank=True)
            for name, table_def in map_table_name_to_table_def.items():
                database_embedder.add_table(name, table_def)
            if not self.table_name or self.table_name==[]:
                similar_tables = database_embedder.get_similar_tables(raw_prompt, n=5)

                table_definitions = database_embedder.get_table_definitions_from_names(
                    similar_tables
                )
            else:
                table_definitions = database_embedder.get_table_definitions_from_names(
                    self.table_name
                )

            prompt = f"问题: {raw_prompt}" + "\n" + f"表的信息:\n {table_definitions}"

            messages = [{'role': 'user', 'content': prompt}]
            results = '[]'
            i = 0
            try:
                while i < 3 and (len(results)==0 or results == '[]' or not results or 'Error occurred' in results ):
                    sql_reply = await data_engineer.a_generate_reply(messages=messages)
                    sql_reply = sql_reply if isinstance(sql_reply, dict) else {'role':'assistant', 'content':sql_reply}
                    sql = self.get_sql(sql_reply)
                    if 'i dont know' in sql.lower():
                        i +=1 
                        continue
                    messages.append({'role':'assistant','content': sql})
                    results = db.run_sql(sql)
                    messages.append({'role':'user','content': 'sql结果:' + results})
                    i += 1
                # if i == 3 and (len(results)==0 or results == '[]' or not results or 'Error occurred' in results):
                #     del messages[-6:]
                #     if 'I dont know' in sql:
                #         messages.append({'role':'assistant','content':f'根据所提供的问题和表的信息的关联不够, 我无法召回相关的数据'})
                #     else:
                #         messages.append({'role':'assistant','content':f'生成sql出现了问题,结果为: {results}'})
                # else:
                #     del messages[-2*i:-2]
                
            except Exception as e:
                print(e)

            return sql, results


if __name__ == '__main__':
    pass