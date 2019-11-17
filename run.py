'''
Z:/apiserver_v2/run.py
Purpose: 

Maxta Inc, 2018
Proprietary
'''

from api import app

#app.run(host='0.0.0.0', port=4040, debug=True, threaded=True)
app.run(host='0.0.0.0', port=4040, threaded=True)
