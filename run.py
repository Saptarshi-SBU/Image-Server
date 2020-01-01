'''
Z:/apiserver_v2/run.py
Purpose: 
'''
import logging
from api import app

app.logger.setLevel(logging.DEBUG)
#app.run(host='0.0.0.0', port=4040, debug=True, threaded=True)
app.run(host='0.0.0.0', port=4040, threaded=True)
