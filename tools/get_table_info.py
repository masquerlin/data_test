import pandas as pd
df = pd.read_excel('/mnt/e/data_test/data/third/2025021902TEST.xls')
df.to_csv('/mnt/e/data_test/data/third/2025021902TEST.csv',header=True,index=False)