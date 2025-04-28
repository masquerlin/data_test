import autogen, os
from config import llm_config, llm_dict
from prompt import *

plot_agent = autogen.AssistantAgent(
    name='plot',
    system_message=plot_system_prompt,
    llm_config=llm_dict.get('max')
)

data_engineer = autogen.AssistantAgent(
    name="Engineer",
    llm_config=llm_dict.get(os.getenv('SQL_MODEL', 'ds')),
    system_message=sql_system,
    code_execution_config=False,
    human_input_mode="NEVER",
)
