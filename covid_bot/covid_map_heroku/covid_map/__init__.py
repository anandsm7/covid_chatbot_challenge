from flask import Flask

app = Flask(__name__)

from covid_map import routes

