import os.path
import flask
from flask import Flask
from flask import request
from flask_cors import CORS
import json
import geopandas as gpd
import gerrychain
import networkx as nx
import time

app = Flask(__name__)
CORS(app)

import os.path
dir_path = os.path.dirname(os.path.realpath(__file__))

state_shapefile_paths = {
    "iowa": f'{dir_path}/shapefiles/IA_counties/IA_counties.shp',
    "texas": f'{dir_path}/shapefiles/TX_vtds/TX_vtds.shp',
}

def form_assignment_from_state_graph(districtr_assignment, node_to_id, state_graph):
    '''
    Converts a Districtr graph assignment (which node belongs to which district)
    into an assignment that works with Gerrychain
    Requires a Districtr graph assignment, 
    a mapping of Districtr nodes to Gerrychain nodes,
    and the appropriate state dual graph.
    Assigns all unassigned nodes to a district -1.
    Returns an assignment of each node in the state graph to to a district.
    '''
    assignment = {}
    for node in state_graph:
        node_id = node_to_id[node]
        if node_id in districtr_assignment:
            if isinstance(districtr_assignment[node_id], list):
                assert(len(districtr_assignment[node_id]) == 1)
                assignment[node] = districtr_assignment[node_id][0]
            else:
                assignment[node] = districtr_assignment[node_id]
        else:
            # We assign to -1
            assignment[node] = -1
    return assignment

cached_gerrychain_graphs = {}

@app.route('/', methods=['POST'])
# Takes a Districtr JSON and returns whether or not it's contiguous and number of cut edges.
def plan_metrics():
    plan = request.get_json()
    
    state = plan['placeId'] # get the state of the Districtr plan
    # Check if we already have a dual graph of the state
    dual_graph_path = f"{dir_path}/dual_graphs/mggg-dual-graphs/{state}.json"
    print(dual_graph_path)

    if state in cached_gerrychain_graphs:
        start = time.time()
        print("Retrieving the state graph from memory..")
        state_graph = cached_gerrychain_graphs[state]
        end = time.time()
        print(f"Time taken to retrieve the state graph from memory: {end-start}")
    elif os.path.isfile(dual_graph_path):
        # TODO timeit this --- how long does it take to load into memory?
        # this takes the vast majority of the time
        start = time.time()
        state_graph = gerrychain.Graph.from_json(dual_graph_path)
        print("Caching the state graph...")
        cached_gerrychain_graphs[state] = state_graph
        end = time.time()
        print(f"Time taken to load into gerrychain Graph from json: {end-start}")
    else:
        response = flask.jsonify({'error': "Don't have dual graph for this state"})
        return response
        '''
        print("No dual graph found, generating our own.")
        try:
            state_shapefile_path = state_shapefile_paths[state]
            state_graph = gerrychain.Graph.from_file(state_shapefile_path)
            state_graph.to_json(f'{dir_path}/dual_graphs/{state}_dual.json')
            print("Dual graph generated!")
        except GeometryError as e:
            print(e)
        except ValueError:
            response = flask.jsonify({'error': "Don't have either dual graph or shapefile for this state"})
            return response
        '''

    # OK, so now we are guaranteed to have the state graph.
    # Form the partition with the JSON path (requires state graph)
    # This is taken from the Districtr function from_districtr_file
    # https://gerrychain.readthedocs.io/en/latest/_modules/gerrychain/partition/partition.html
    id_column_key = plan["idColumn"]["key"]
    districtr_assignment = plan["assignment"]

    try:
        node_to_id = {node: str(state_graph.nodes[node][id_column_key]) for node in state_graph}
    except KeyError:
        response = flask.jsonify({'error':
            "The provided graph is missing the {} column, which is "
            "needed to match the Districtr assignment to the nodes of the graph."
        })
        return response

    # If everything checks out, form a Partition
    # TODO timeit this --- how long does it take?
    start_1 = time.time()
    assignment = form_assignment_from_state_graph(districtr_assignment, node_to_id, state_graph)
    end_1 = time.time()
    print(f"Time taken to form assignment from dual graph: {end_1-start_1}")

    # TODO timeit this --- how long does it take?
    start_2 = time.time()
    partition = gerrychain.Partition(state_graph, assignment, None)
    end_2 = time.time()
    print(f"Time taken to form partition from assignment: {end_2 - start_2}")

    # Now that we have the partition, calculate all the different metrics

    # Calculate cut edges
    cut_edges = (partition['cut_edges'])

    # Split districts
    # TODO timeit this --- how long does it take?
    start_3 = time.time()
    split_districts = []
    for part in gerrychain.constraints.contiguity.affected_parts(partition):
        if part != -1:
            part_contiguous = nx.is_connected(partition.subgraphs[part])
            if not part_contiguous:
                split_districts.append(part)
    end_3 = time.time()
    print(f"Time taken to get split districts: {end_3 - start_3}")

    # Contiguity
    contiguity = (len(split_districts) == 0)

    response = flask.jsonify({'cut_edges': len(cut_edges), 'contiguity': contiguity, 'split': split_districts})
    return response