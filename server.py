from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from config import STATIC_DIR, BASE_UPLOAD_DIRECTORY, db_url, file_url, port
from sql_instruments import sql_analyze_father
from agents import data_engineer
import time
import pandas as pd 
from plot import plot
import json
import uvicorn
import os
app = FastAPI()
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount(STATIC_DIR, StaticFiles(directory=BASE_UPLOAD_DIRECTORY), name="static")
app.add_middleware(
   CORSMiddleware,
   allow_origins=["*"],
   allow_credentials=True,
   allow_methods=["*"],
   allow_headers=["*"],
)

@app.post("/sql")
async def gen_sql(request:Request):
    data = await request.json()
    question = data['question']
    sql_instance = sql_analyze_father(data_engineer=data_engineer,client_id='new', db_param=db_url)
    sql, results = await sql_instance.run_sql_analyze(raw_prompt=question)
    time_str = str(int(time.time()))
    csv_file_name = time_str + '.csv'
    fig_file_name = time_str + '.html'
    df = pd.DataFrame(json.loads(results))
    df.to_csv(os.path.join(BASE_UPLOAD_DIRECTORY, csv_file_name))
    print(os.path.join(BASE_UPLOAD_DIRECTORY, csv_file_name))
    fig = await plot(question=question, sql=sql, df=df)
    fig.write_html(os.path.join(BASE_UPLOAD_DIRECTORY, fig_file_name))
    
    
    return JSONResponse(content={
        "sql":sql,
        "data":file_url + STATIC_DIR + '/' + csv_file_name,
        "fig": file_url + STATIC_DIR + '/' + fig_file_name, 
        "sql_result":results
        
    })

if __name__ == '__main__':
    uvicorn.run(app=app, host='0.0.0.0', port=port)
