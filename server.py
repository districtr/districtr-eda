from flask import Flask
from flask import request
import sys
import json
import geopandas as gpd
import gerrychain
import networkx as nx
import matplotlib.pyplot as plt

app = Flask(__name__)

import os.path

state_shapefile_paths = {
    "iowa": './shapefiles/IA_counties/IA_counties.shp',
    "texas": './shapefiles/TN_vtds/TN_vtds.shp',
}

@app.route('/', methods=['POST'])
# Takes a Districtr JSON and returns whether or not it's contiguous and number of cut edges.
def plan_metrics():
    #JSON_PATH = './incomplete-islands.json'
    # Consider now that we've received a request
    plan = request.json
    state = plan['placeId'] # get the state of the Districtr plan
    # Check if we already have a dual graph of the state
    try:
        with open(f"./dual_graphs/{state}_dual.json", 'r') as f:
            state_graph = gerrychain.Graph.from_json(f)
    except FileNotFoundError: # otherwise, generate it
        try:
            state_shapefile_path = state_shapefile_paths[state]
            state_graph = gerrychain.Graph.from_file(state_shapefile_path)
            state_graph.to_json(f'./dual_graphs/{state}_dual.json')
        except ValueError:
            return("Don't have either dual graph or shapefile for this state")
    # OK, so now we are guaranteed to have the state graph.
    # Form the partition with the JSON path (requires state graph
    partition = gerrychain.Partition.from_districtr_file(state_graph, JSON_PATH, 
                                                         updaters=None)
    # Now that we have the partition, calculate all the different metrics
    print(partition['cut_edges'])
    print(gerrychain.constraints.contiguity.contiguous(partition))




