import autogen, os
from config import llm_config, llm_dict
from prompt import plot_system_prompt,sql_system

plot_agent = autogen.AssistantAgent(
    name='plot',
    system_message=plot_system_prompt,
    llm_config=llm_config
)

data_engineer = autogen.AssistantAgent(
    name="Engineer",
    llm_config=llm_dict.get(os.getenv('SQL_MODEL', 'max')),
    system_message=sql_system,
    code_execution_config=False,
    human_input_mode="NEVER",
)
