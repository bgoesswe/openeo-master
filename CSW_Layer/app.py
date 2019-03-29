from data.dependencies.csw import CSWHandler
from flask import Flask
from flask import request
from requests import post

app = Flask(__name__)

CSW_SERVER = "https://csw.eodc.eu"

@app.route("/", methods = ['GET', 'POST'])
def hello():
    response = {}
    response["args"] = request.args
    response["form"] = request.form
    response["files"] = request.files
    response["values"] = request.values

    print(str(response))

    return str(response)

@app.route("/mockup", methods = ['GET', 'POST', 'DELETE'])
def mockup():


    #handler = CSWHandler("https://csw.eodc.eu")

    #result = handler.get_all_products()

    return str(result)

app.run(debug=True, port=5000) #run app in debug mode on port 5000
#handler = CSWHandler("https://csw.eodc.eu")

#result = handler.get_all_products()

#print("Finished !")