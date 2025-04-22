import autogen, os
from autogen.agentchat import UserProxyAgent, ConversableAgent
from config import llm_config, llm_dict
from prompt import analyze_detect_prompt, function_detect_prompt
from termcolor import colored
# define your agent here


DATA_ENGINEER_PROMPT = "You are an professional SQL engineer, Generate the initial SQL based on the requirements provided. Just return SQL query.The database type is SQL Server."
SUMMARY_PROMPT = "A text summarization expert, skilled at extracting the core essence from dialogue content."


coder = autogen.AssistantAgent(
    name="Coder",  # the default assistant agent is capable of solving problems with code
    llm_config=llm_config,
)
critic = autogen.AssistantAgent(
    name="Critic",
    system_message="""Critic. You are a helpful assistant highly skilled in evaluating the quality of a given visualization code by providing a score from 1 (bad) - 10 (good) while providing clear rationale. YOU MUST CONSIDER VISUALIZATION BEST PRACTICES for each evaluation. Specifically, you can carefully evaluate the code across the following dimensions
- bugs (bugs):  are there bugs, logic errors, syntax error or typos? Are there any reasons why the code may fail to compile? How should it be fixed? If ANY bug exists, the bug score MUST be less than 5.
- Data transformation (transformation): Is the data transformed appropriately for the visualization type? E.g., is the dataset appropriated filtered, aggregated, or grouped  if needed? If a date field is used, is the date field first converted to a date object etc?
- Goal compliance (compliance): how well the code meets the specified visualization goals?
- Visualization type (type): CONSIDERING BEST PRACTICES, is the visualization type appropriate for the data and intent? Is there a visualization type that would be more effective in conveying insights? If a different visualization type is more appropriate, the score MUST BE LESS THAN 5.
- Data encoding (encoding): Is the data encoded appropriately for the visualization type?
- aesthetics (aesthetics): Are the aesthetics of the visualization appropriate for the visualization type and the data?

YOU MUST PROVIDE A SCORE for each of the above dimensions.
{bugs: 0, transformation: 0, compliance: 0, type: 0, encoding: 0, aesthetics: 0}
Do not suggest code.
Finally, based on the critique above, suggest a concrete list of actions that the coder should take to improve the code.
""",
    llm_config=llm_config,
)

sql_agent = autogen.AssistantAgent(
    name='Sql',
    system_message="""Sql, You are a helpful assistant highly skilled in generating sql.""",
    llm_config=llm_config,
)


data_engineer = autogen.AssistantAgent(
    name="Engineer",
    llm_config=llm_dict.get(os.getenv('SQL_MODEL', 'max')),
    system_message=DATA_ENGINEER_PROMPT,
    code_execution_config=False,
    human_input_mode="NEVER",
)

sql_answer = autogen.AssistantAgent(
    name='sql_answer',
    system_message="""Answer the user's question according to the data""",
    llm_config=llm_config,
)

code_answer = autogen.AssistantAgent(
    name='code_answer',
    system_message="""Answer the user's question according to the code and the output of the code execution""",
    llm_config=llm_config,
)

# fnc_user_proxy = custom_proxy(
#     name="user_proxy",
#     is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
#     human_input_mode="NEVER",
#     max_consecutive_auto_reply=2,
#     code_execution_config=False
# )
# fnc_chatbot = fnc_agent(
#     name="chatbot",
#     system_message=function_detect_prompt,
#     llm_config=llm_config
# )

fnc_user_proxy = UserProxyAgent(
    name="user_proxy",
    is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
    human_input_mode="NEVER",
    max_consecutive_auto_reply=2,
    code_execution_config=False
)
fnc_chatbot = ConversableAgent(
    name="chatbot",
    system_message=function_detect_prompt,
    llm_config=llm_dict.get(os.getenv('FUNC_MODEL', 'max'))
)