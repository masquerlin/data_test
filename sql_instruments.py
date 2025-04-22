import os, json, pymssql, asyncio, autogen, torch
from datetime import datetime
import util
from util import get_db_param, json_to_excel, json_to_dataframe
from sklearn.metrics.pairwise import cosine_similarity
from transformers import BertTokenizer, BertModel
from config import STATIC_DIR, bge_model_path
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from agents import data_engineer, sql_answer
from prompt import POSTGRES_TABLE_DEFINITIONS_CAP_REF, NOTE, EXAMPLE
from util import plot_data

plot_instance = plot_data()

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
    """
    A class to manage postgres connections and queries
    """

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
        self.conn = pymssql.connect(**url)
        self.cur = self.conn.cursor()

    def close(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

    def run_sql(self, sql) -> str:
        """
        Run a SQL query against the postgres database
        """
        try:
            self.cur.execute(sql)
            columns = [desc[0] for desc in self.cur.description]
            res = self.cur.fetchall()

            list_of_dicts = [dict(zip(columns, row)) for row in res]

            json_result = json.dumps(list_of_dicts, indent=4, ensure_ascii=False, default=self.datetime_handler)

            return json_result

        except Exception as e:
            return f'Error occurred when execute the sql: {str(e)} Please construct a new SQL query.'


    def datetime_handler(self, obj):
        """
        Handle datetime objects when serializing to JSON.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)  # or just return the object unchanged, or another default value

    def get_table_definition(self, table_name):
        """
        Generate the 'create' definition for a table
        """

        get_def_stmt = """
            SELECT 
                t.name AS tablename,
                c.column_id AS attnum,
                c.name AS attname,
                TYPE_NAME(c.system_type_id) AS data_type
            FROM 
                sys.tables t
            JOIN 
                sys.columns c ON t.object_id = c.object_id
            WHERE 
                t.name = %s  -- Assuming @TableName is a parameter
                AND SCHEMA_NAME(t.schema_id) = 'dbo'  -- Assuming you're interested in dbo schema
            ORDER BY 
                c.column_id;
        """
        self.cur.execute(get_def_stmt, (table_name,))
        rows = self.cur.fetchall()
        create_table_stmt = "CREATE TABLE {} (\n".format(table_name)
        for row in rows:
            create_table_stmt += "{} {},\n".format(row[2], row[3])
        create_table_stmt = create_table_stmt.rstrip(",\n") + "\n);"
        return create_table_stmt

    def get_all_table_names(self):
        """
        Get all table names in the database
        """
        get_all_tables_stmt = (
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE';"
        )
        self.cur.execute(get_all_tables_stmt)
        return [row[0] for row in self.cur.fetchall()]

    def get_table_definitions_for_prompt(self):
        """
        Get all table 'create' definitions in the database
        """
        table_names = self.get_all_table_names()
        definitions = []
        for table_name in table_names:
            definitions.append(self.get_table_definition(table_name))
        return "\n\n".join(definitions)

    def get_table_definition_map_for_embeddings(self):
        """
        Creates a map of table names to table definitions
        """
        table_names = self.get_all_table_names()
        definitions = {}
        for table_name in table_names:
            definitions[table_name] = self.get_table_definition(table_name)
        return definitions

    def get_related_tables(self, table_list, n=2):
        """
        Get tables that have foreign keys referencing the given table
        """

        related_tables_dict = {}

        for table in table_list:
            # Query to fetch tables that have foreign keys referencing the given table
            self.cur.execute(
                """
                SELECT 
                    OBJECT_NAME(fk.parent_object_id) AS table_name
                FROM 
                    sys.foreign_keys fk
                WHERE 
                    fk.referenced_object_id = OBJECT_ID(%s)
                ORDER BY 
                    table_name
                OFFSET 0 ROWS FETCH NEXT %s ROWS ONLY;
                """,
                (table, n),
            )

            related_tables = [row[0] for row in self.cur.fetchall()]

            # Query to fetch tables that the given table references
            self.cur.execute(
                """
                SELECT 
                    OBJECT_NAME(fk.parent_object_id) AS table_name
                FROM 
                    sys.foreign_keys fk
                WHERE 
                    fk.referenced_object_id = OBJECT_ID(%s)
                ORDER BY 
                    table_name
                OFFSET 0 ROWS FETCH NEXT %s ROWS ONLY;
                """,
                (table, n),
            )

            related_tables += [row[0] for row in self.cur.fetchall()]

            related_tables_dict[table] = related_tables

        # convert dict to list and remove dups
        related_tables_list = []
        for table, related_tables in related_tables_dict.items():
            related_tables_list += related_tables

        related_tables_list = list(set(related_tables_list))

        return related_tables_list


class DatabaseEmbedder:
    """
    This class is responsible for embedding database table definitions and
    computing similarity between user queries and table definitions.
    """

    def __init__(self, db: PostgresManager, rerank: bool):
        # self.tokenizer = BertTokenizer.from_pretrained("bert-base-uncased", local_files_only=True)
        # self.model = BertModel.from_pretrained("bert-base-uncased", local_files_only=True)
        
        if rerank:
            self.model = AutoModelForSequenceClassification.from_pretrained(bge_model_path)
            self.tokenizer = AutoTokenizer.from_pretrained(bge_model_path)
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
        """
        Add a table to the database embedder.
        Map the table name to its embedding and text representation.
        """
        if self.rerank:
            self.map_name_to_embeddings[table_name] = None
        else:
            self.map_name_to_embeddings[table_name] = self.compute_embeddings(
                text_representation
            )

        self.map_name_to_table_def[table_name] = text_representation

    def compute_embeddings(self, text):
        """
        Compute embeddings for a given text using the BERT model.
        """
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
            print(f'similarity : {result}')
            sorted_results = sorted(result.items(), key=lambda x: x[1], reverse=True)
            final_result = [x[0] for x in sorted_results]
            return final_result[:n]
    def get_similar_tables_via_embeddings(self, query, n=3):
        """
        Given a query, find the top 'n' tables that are most similar to it.

        Args:
        - query (str): The user's natural language query.
        - n (int, optional): Number of top tables to return. Defaults to 3.

        Returns:
        - list: Top 'n' table names ranked by their similarity to the query.
        """
        # Compute the embedding for the user's query
        query_embedding = self.compute_embeddings(query)
        # Calculate cosine similarity between the query and all tables
        similarities = {
            table: cosine_similarity(query_embedding, emb)[0][0]
            for table, emb in self.map_name_to_embeddings.items()
        }
        # Rank tables based on their similarity scores and return top 'n'
        return sorted(similarities, key=similarities.get, reverse=True)[:n]

    def get_similar_table_names_via_word_match(self, query: str):
        """
        if any word in our query is a table name, add the table to a list
        """

        tables = []

        for table_name in self.map_name_to_table_def.keys():
            if table_name.lower() in query.lower():
                tables.append(table_name)

        return tables

    def get_similar_tables(self, query: str, n=3):
        """
        combines results from get_similar_tables_via_embeddings and get_similar_table_names_via_word_match
        """
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
        """
        Given a list of table names, return their table definitions.
        """
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
                print(f'similar_tables  {similar_tables}')
                table_definitions = database_embedder.get_table_definitions_from_names(
                    similar_tables
                )
            else:
                table_definitions = database_embedder.get_table_definitions_from_names(
                    self.table_name
                )

            prompt = f"Please meet the needs of the user: {raw_prompt}, "
            prompt = self.add_cap_ref(
                prompt,
                f"and use these {POSTGRES_TABLE_DEFINITIONS_CAP_REF} to satisfy the database query.Please ensure that SQL has the highest efficiency and conforms to the syntax of the database.",
                POSTGRES_TABLE_DEFINITIONS_CAP_REF,
                table_definitions, NOTE, EXAMPLE
            )

            messages = [{'role': 'user', 'content': prompt}]
            results = '[]'
    
            i = 0
            try:
                while i < 3 and (len(results)==0 or results == '[]' or 'Error occurred' in results ):
                    sql_reply = await data_engineer.a_generate_reply(messages=messages)
                    sql_reply = sql_reply if isinstance(sql_reply, dict) else {'role':'assistant', 'content':sql_reply}
                    sql = self.get_sql(sql_reply)
                    if 'I dont know' in sql:
                        i +=1 
                        continue

                    messages.append({'role':'user','content': sql})
                    results = db.run_sql(sql)
                    messages.append({'role':'assistant','content': results})
                    i += 1
                print(f'messages before *****{messages}')
                if i == 3 and (len(results)==0 or results == '[]' or 'Error occurred' in results):
                    del messages[-6:]
                    if 'I dont know' in sql:
                        messages.append({'role':'assistant','content':f'根据所提供的问题和表的信息的关联不够, 我无法召回相关的数据'})
                    else:
                        messages.append({'role':'assistant','content':f'生成sql出现了问题,结果为: {results}'})
                else:
                    del messages[-2*i:-2]
                print('\n ---------------- \n')
                print(f'messages after *****{messages}')
                
            except Exception as e:
                print(e)
            data_sql = messages[-1].get('content')
            summary_messages = [{'role':'user','content':raw_prompt}, {'role':'assistant','content':f'生成的sql: \n {sql} \n 执行的数据结果: {data_sql}'}]
            print(summary_messages)
            summary = await sql_answer.a_generate_reply(messages=summary_messages)
            summary_content = summary['content'] if isinstance(summary, dict) else summary
            print(f'final_answer: \n {summary_content}\n')
            return sql, results, summary_content
    
    def make_data(self, input_data, excel_file, plot_file):
        json_to_excel(input_data, excel_file)
        df = json_to_dataframe(input_data)
        print(df)
        plot_data_html = plot_instance.auto_plot(df, plot_file)
        return df, plot_file


if __name__ == '__main__':
    db_param = get_db_param('sale_database')
    sql_instance = sql_analyze_father(data_engineer=data_engineer, client_id='dalin', db_param=db_param)
    sql, results, summary = asyncio.run(sql_instance.run_sql_analyze(raw_prompt='哪些服装款式在销售中最受欢迎'))
    df, plot_file = sql_instance.make_data(results, './xxx.xlsx', './yyyy.html')
    print(sql,results, summary)
    pass