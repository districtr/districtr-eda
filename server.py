import os.path
import flask
from flask import Flask
from flask import request
from flask_cors import CORS
import json
import geopandas as gpd
import gerrychain

app = Flask(__name__)
CORS(app)

import os.path

state_shapefile_paths = {
    "iowa": './shapefiles/IA_counties/IA_counties.shp',
    "texas": './shapefiles/TN_vtds/TN_vtds.shp',
}

@app.route('/', methods=['POST'])
# Takes a Districtr JSON and returns whether or not it's contiguous and number of cut edges.
def plan_metrics():
    #print("Request received")
    #print(request)
    plan = request.get_json()
    #print(plan)
    
    state = plan['placeId'] # get the state of the Districtr plan
    # Check if we already have a dual graph of the state
    dual_graph_path = f"./dual_graphs/{state}_dual.json"

    if os.path.isfile(dual_graph_path):
        state_graph = gerrychain.Graph.from_json(dual_graph_path)
    else:
        print("No dual graph found, generating our own.")
        try:
            state_shapefile_path = state_shapefile_paths[state]
            state_graph = gerrychain.Graph.from_file(state_shapefile_path)
            state_graph.to_json(f'./dual_graphs/{state}_dual.json')
        except ValueError:
            return ("Don't have either dual graph or shapefile for this state")
    # OK, so now we are guaranteed to have the state graph.
    # Form the partition with the JSON path (requires state graph)
    # partition = gerrychain.Partition.from_districtr_file(state_graph, JSON_PATH, 
    #                                                     updaters=None)

    # This is taken from the Districtr function from_districtr_file
    # https://gerrychain.readthedocs.io/en/latest/_modules/gerrychain/partition/partition.html
    id_column_key = plan["idColumn"]["key"]
    districtr_assignment = plan["assignment"]
    try:
        node_to_id = {node: str(state_graph.nodes[node][id_column_key]) for node in state_graph}
    except KeyError:
        raise TypeError(
            "The provided graph is missing the {} column, which is "
            "needed to match the Districtr assignment to the nodes of the graph."
        )
    assignment = {node: districtr_assignment[node_to_id[node]] for node in state_graph}
    partition = gerrychain.Partition(state_graph, assignment, None)

    # Now that we have the partition, calculate all the different metrics
    cut_edges = (partition['cut_edges'])
    contiguity = (gerrychain.constraints.contiguity.contiguous(partition))


    response = flask.jsonify({'cut_edges': str(cut_edges), 'contiguity': contiguity})
    #response.headers.add('Access-Control-Allow-Origin', '*')
    return response
    '''

    response = flask.jsonify({'message': 'hello'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response
    '''

