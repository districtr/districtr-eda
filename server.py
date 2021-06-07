import os.path
from os import system
import base64
import io
import time
from random import randint
from contextlib import contextmanager
import os

## server monitoring
#import newrelic.agent
#newrelic.agent.initialize('/home/mggg/newrelic.ini')

import flask
from flask import Flask
from flask import request
from flask import send_file
from flask_cors import CORS
import json
import geopandas as gpd
import gerrychain
import networkx as nx
import matplotlib.pyplot as plt
import fiona
from fiona.crs import from_epsg
import pandas as pd
import requests

# mongodb
from pymongo import MongoClient, ReadPreference
client = MongoClient(open('/home/mggg/districtr-eda/.env2').read().strip(), connectTimeoutMS=30000, socketTimeoutMS=None, socketKeepAlive=True, connect=False, maxPoolsize=1)
mdb = client.test

# postgresql
import psycopg2
conn_str = open('/home/mggg/districtr-eda/.env', 'r').read().strip()
user = conn_str.split('user=')[1].split(' ')[0]
passw = conn_str.split('password=')[1].split(' ')[0]
host = conn_str.split('host=')[1].split(' ')[0]
port = conn_str.split('port=')[1].split(' ')[0]

@contextmanager
def db():
    con = postgreSQL_pool.getconn()
    cur = con.cursor()
    try:
        yield con, cur
    finally:
        cur.close()
        postgreSQL_pool.putconn(con)

import pickle
from vra import district_vra_effectiveness

app = Flask(__name__)
CORS(app)

dir_path = os.path.dirname(os.path.realpath(__file__))

state_shapefile_paths = {
    # blockgroups and precincts: how do we support both?
    # place.id=alaska will be split into 'alaska' and 'alaska_bg' (when units.id=="blockgroups") on the server
    # just direct them to the correct file for that type
    # if your id already includes _bg it will not double up

    "alabama_bg": f'{dir_path}/shapefiles/alabama/tl_2010_01_bg10.shp',

    "alaska": f'{dir_path}/shapefiles/alaska/alaska_precincts.shp',
        "alaska_bg": f'{dir_path}/shapefiles/alaska/tl_2010_02_bg10.shp',

    "arizona": f'{dir_path}/shapefiles/arizona/az_precincts.shp',
        "arizona_bg": f'{dir_path}/shapefiles/arizona/tl_2010_04_bg10.shp',
        "mesaaz": f'{dir_path}/shapefiles/arizona/mesa2.shp',
        "maricopa": None,
        "nwaz": None,
        "seaz": None,
        "phoenix": None,
        "yuma": None,

    "arkansas_bg": f'{dir_path}/shapefiles/arkansas/tl_2010_05_bg10.shp',
        "little_rock": None,

    # California
    "california_bg": f'{dir_path}/shapefiles/california/tl_2010_06_bg10.shp',
        'lax_bg': f'{dir_path}/shapefiles/lax/tl_2010_06037_bg10.shp',
        'ccsanitation': f'{dir_path}/shapefiles/ccsani/CentralSan_Census_Block.shp',
        'ccsanitation2': f'{dir_path}/shapefiles/ccsani/CentralSan_Census_Block.shp',
        'napa': None,
        'napaschools': None,
        'ontarioca': None,
        'ca_amador': f'{dir_path}/shapefiles/california/Amador_county.shp',
        'ca_lockwood': f'{dir_path}/shapefiles/california/lockwood_blocks.shp',
        'ca_alturas': f'{dir_path}/shapefiles/california/alturas_blocks.shp',
        'ca_CCosta_bg': f'{dir_path}/shapefiles/california/ContraCosta_county.shp',
        'ca_SanBenito': f'{dir_path}/shapefiles/california/SanBenito_county.shp',
        "ca_SanDiego_bg": f'{dir_path}/shapefiles/california/SanDiego_county.shp',
        "ca_sutter": f'{dir_path}/shapefiles/california/Sutter_county.shp',
        "pasorobles": f'{dir_path}/shapefiles/california/CensusBlocks_2010_1519CVAP.shp',

    "colorado": f'{dir_path}/shapefiles/colorado/co_precincts.shp',
        "colorado_bg": f'{dir_path}/shapefiles/colorado/tl_2010_08_bg10.shp',

    "connecticut": f'{dir_path}/shapefiles/connecticut/CT_precincts.shp',
        "connecticut_bg": f'{dir_path}/shapefiles/connecticut/tl_2010_09_bg10.shp',

    "delaware": f'{dir_path}/shapefiles/delaware/DE_precincts.shp',
        "delaware_bg": f'{dir_path}/shapefiles/delaware/tl_2010_10_bg10.shp',

    'dc_bg': f'{dir_path}/shapefiles/wadc/tl_2010_11_bg10.shp',

    "florida_bg": f'{dir_path}/shapefiles/florida/tl_2010_12_bg10.shp',
        "miamidade": None,
        "miamifl": None,
        "fl_orange_bg": f'{dir_path}/shapefiles/florida/fl_orange.shp',
        "fl_hills_bg": f'{dir_path}/shapefiles/florida/fl_hillsborough.shp',
        "fl_osceola": f'{dir_path}/shapefiles/florida/osceola_blocks.shp',
        "kissimmee": f'{dir_path}/shapefiles/florida/kissimmee_blocks.shp',
        "orlando": f'{dir_path}/shapefiles/florida/orlando_blocks.shp',
        "tampa": f'{dir_path}/shapefiles/florida/tampa_blocks.shp',

    "georgia": f'{dir_path}/shapefiles/georgia/GA_precincts16.shp',
        "georgia_bg": f'{dir_path}/shapefiles/georgia/tl_2010_13_bg10.shp',

    "hawaii": f'{dir_path}/shapefiles/hawaii/HI_precincts.shp',
        "hawaii_bg": f'{dir_path}/shapefiles/hawaii/tl_2010_15_bg10.shp',

    "idaho_bg": f'{dir_path}/shapefiles/idaho/tl_2010_16_bg10.shp',

    "illinois_bg": f'{dir_path}/shapefiles/illinois/tl_2010_17_bg10.shp',
        "chicago": None,

    "indiana": f'{dir_path}/shapefiles/indiana/Indiana.shp',
    "indianaprec": f'{dir_path}/shapefiles/indiana/Indiana.shp',
        "indiana_bg": f'{dir_path}/shapefiles/indiana/tl_2010_18_bg10.shp',

    "iowa": f'{dir_path}/shapefiles/IA_counties/IA_counties.shp',
        "iowa_bg": f'{dir_path}/shapefiles/iowa/tl_2010_19_bg10.shp',

    "kansas_bg": f'{dir_path}/shapefiles/kansas/tl_2010_20_bg10.shp',

    "kentucky_bg": f'{dir_path}/shapefiles/kentucky/tl_2010_21_bg10.shp',

    'louisiana': f'{dir_path}/shapefiles/louisiana/LA_1519.shp',
        "louisiana_bg": f'{dir_path}/shapefiles/louisiana/tl_2010_22_bg10.shp',
        'batonrouge_bg': f'{dir_path}/shapefiles/louisiana/batonrouge.shp',

    'maine': f'{dir_path}/shapefiles/maine/Maine.shp',
        "maine_bg": f'{dir_path}/shapefiles/maine/tl_2010_23_bg10.shp',

    'maryland': f'{dir_path}/shapefiles/maryland/MD_precincts.shp',
        "maryland_bg": f'{dir_path}/shapefiles/maryland/tl_2010_24_bg10.shp',
        "baltimore_bg": f'{dir_path}/shapefiles/maryland/baltimore_bgs_weighted.shp',

    # Massachusetts
    'ma': f'{dir_path}/shapefiles/massachusetts/TOWNSSURVEY_POLYM_GENCOAST.shp',
        'ma_12': f'{dir_path}/shapefiles/massachusetts/MA_precincts12_16.shp',
        'ma_02': f'{dir_path}/shapefiles/massachusetts/MA_precincts_02_10.shp',
        'ma_bg': f'{dir_path}/shapefiles/massachusetts/tl_2010_25_bg10.shp',
        'ma_vra': f'{dir_path}/shapefiles/massachusetts/MA_VRA_Product.shp',
        'lowell': f'{dir_path}/shapefiles/lowell/lowell-contig.shp',

    "michigan": f'{dir_path}/shapefiles/michigan/MI.shp',
        "michigan_bg": f'{dir_path}/shapefiles/michigan/tl_2010_26_bg10.shp',

    "minnesota": f'{dir_path}/shapefiles/minnesota/mn_precincts12_18.shp',
        "minnesota_bg": f'{dir_path}/shapefiles/minnesota/tl_2010_27_bg10.shp',
        "mn2020acs": f'{dir_path}/shapefiles/minnesota/mn-precincts-2020-acs-elections-adjoined.shp',
        'olmsted': None,
        'rochestermn': None,
        'washington_mn_bg': f'{dir_path}/shapefiles/minnesota/tl_2010_27163_bg10.shp',
        'stlouis_mn_bg': f'{dir_path}/shapefiles/minnesota/tl_2010_27137_bg10.shp',

    # Mississippi
        "mississippi_bg": f'{dir_path}/shapefiles/mississippi/tl_2010_28_bg10.shp',

    # Missouri
        "missouri_bg": f'{dir_path}/shapefiles/missouri/tl_2010_29_bg10.shp',

    # Montana
        "montana_bg": f'{dir_path}/shapefiles/montana/tl_2010_30_bg10.shp',

    "nebraska": f'{dir_path}/shapefiles/nebraska/NE.shp',
        "nebraska_bg": f'{dir_path}/shapefiles/nebraska/tl_2010_31_bg10.shp',
    # Nevada
        "nevada_bg": f'{dir_path}/shapefiles/nevada/tl_2010_32_bg10.shp',

    "newhampshire": f'{dir_path}/shapefiles/newhampshire/NH.shp',
        "newhampshire_bg": f'{dir_path}/shapefiles/newhampshire/tl_2010_33_bg10.shp',

    # New Jersey
        "newjersey_bg": f'{dir_path}/shapefiles/newjersey/tl_2010_34_bg10.shp',

    'new_mexico': f'{dir_path}/shapefiles/new_mexico/new_mexico_precincts.shp',
        'new_mexico_bg': f'{dir_path}/shapefiles/new_mexico/tl_2010_35_bg10.shp',
        'santafe': f'{dir_path}/shapefiles/new_mexico/santafe.shp',

    # New York
        "newyork_bg": f'{dir_path}/shapefiles/newyork/tl_2010_36_bg10.shp',

    # North Carolina
    "nc": f'{dir_path}/shapefiles/northcarolina/NC_VTD.shp',
    "northcarolina": f'{dir_path}/shapefiles/northcarolina/NC_VTD.shp',
        "nc_bg": f'{dir_path}/shapefiles/northcarolina/tl_2010_37_bg10.shp',
        "northcarolina_bg": f'{dir_path}/shapefiles/northcarolina/tl_2010_37_bg10.shp',
        "forsyth_nc": f'{dir_path}/shapefiles/forsyth_nc/forsyth-nc.shp',
        "buncombe": f'{dir_path}/shapefiles/northcarolina/buncombe.shp',

    # North Dakota
        "northdakota_bg": f'{dir_path}/shapefiles/northdakota/tl_2010_38_bg10.shp',

    "ohio": f'{dir_path}/shapefiles/ohio/OH_precincts.shp',
        "ohio_bg": f'{dir_path}/shapefiles/ohio/tl_2010_39_bg10.shp',
        "ohse_bg": f'{dir_path}/shapefiles/ohio/se_zone.shp',
        "ohcentral_bg": f'{dir_path}/shapefiles/ohio/oh_centralzone.shp',
        "ohtoledo_bg": f'{dir_path}/shapefiles/ohio/toledo_zone.shp',
        "ohcin_bg": f'{dir_path}/shapefiles/ohio/cincinnati_zone.shp',
        "ohcle_bg": f'{dir_path}/shapefiles/ohio/cleveland_zone.shp',
        "ohakron_bg": f'{dir_path}/shapefiles/ohio/akron_zone.shp',

        "akroncanton": f'{dir_path}/shapefiles/ohio/akron-canton-blocks.shp',
        "cincinnati": f'{dir_path}/shapefiles/ohio/cincinatti-blocks.shp',
        "clevelandeuclid": f'{dir_path}/shapefiles/ohio/cleveland-euclid-blocks.shp',
        "columbus": f'{dir_path}/shapefiles/ohio/columbus-etc-blocks.shp',
        "dayton": f'{dir_path}/shapefiles/ohio/dayton-blocks.shp',
        "limaoh": f'{dir_path}/shapefiles/ohio/lima-blocks.shp',
        "mansfield": f'{dir_path}/shapefiles/ohio/mansfield-blocks.shp',
        "portsmouthoh": f'{dir_path}/shapefiles/ohio/portsmouth-blocks.shp',
        "toledo": f'{dir_path}/shapefiles/ohio/toledo-blocks.shp',
        "youngstown": f'{dir_path}/shapefiles/ohio/youngstown-blocks.shp',

    "oklahoma": f'{dir_path}/shapefiles/oklahoma/OK_precincts.shp',
        "oklahoma_bg": f'{dir_path}/shapefiles/oklahoma/tl_2010_40_bg10.shp',

    "oregon": f'{dir_path}/shapefiles/oregon/OR_precincts.shp',
        "oregon_bg": f'{dir_path}/shapefiles/oregon/tl_2010_41_bg10.shp',
        'portlandor': None,

    "pennsylvania": f'{dir_path}/shapefiles/pennsylvania/PA.shp',
        "pennsylvania_bg": f'{dir_path}/shapefiles/pennsylvania/tl_2010_42_bg10.shp',
        'philadelphia': None,

    "puertorico_prec": f'{dir_path}/shapefiles/puertorico/PR.shp',
        "puertorico_bg": f'{dir_path}/shapefiles/puertorico/tl_2010_72_bg10.shp',

    "rhode_island": f'{dir_path}/shapefiles/rhodeisland/RI_precincts.shp',
        "rhode_island_bg": f'{dir_path}/shapefiles/rhodeisland/tl_2010_44_bg10.shp',

    # South Carolina
        "southcarolina_bg": f'{dir_path}/shapefiles/southcarolina/tl_2010_45_bg10.shp',

    # South Dakota
        "southdakota_bg": f'{dir_path}/shapefiles/southdakota/tl_2010_46_bg10.shp',

    # Tennessee
        "tennessee_bg": f'{dir_path}/shapefiles/tennessee/tl_2010_47_bg10.shp',

    "texas": f'{dir_path}/shapefiles/TX_vtds/TX_vtds.shp',
        "texas_bg": f'{dir_path}/shapefiles/texas/tl_2010_48_bg10.shp',
        "houston_bg": f'{dir_path}/shapefiles/texas/houston-bg.shp',
        "elpasotx": f'{dir_path}/shapefiles/texas/elpasotx-prec.shp',
        "elpasotx_b": f'{dir_path}/shapefiles/texas/tl_2010_48141_tabblock10.shp',

    "utah": f'{dir_path}/shapefiles/utah/UT_precincts.shp',
        "utah_bg": f'{dir_path}/shapefiles/utah/tl_2010_49_bg10.shp',
        "grand_county_2": f'{dir_path}/shapefiles/utah/grandcounty.shp',

    "vermont": f'{dir_path}/shapefiles/vermont/VT_town_results.shp',
        "vermont_bg": f'{dir_path}/shapefiles/vermont/tl_2010_50_bg10.shp',

    "virginia": f'{dir_path}/shapefiles/virginia/VA_precincts.shp',
        "virginia_bg": f'{dir_path}/shapefiles/virginia/tl_2010_51_bg10.shp',
        'vabeach': None,

    # Washington (state)
        "washington": f'{dir_path}/shapefiles/washington/tl_2010_53_bg10.shp',

    # West Virginia
        "westvirginia_bg": f'{dir_path}/shapefiles/westvirginia/tl_2010_54_bg10.shp',

    "wisconsin": f'{dir_path}/shapefiles/wisconsin/WI_ltsb_corrected_final.shp',
        "wisconsin2020": f'{dir_path}/shapefiles/wisconsin/WI.shp',
        "wisco2019acs": f'{dir_path}/shapefiles/wisconsin/WI-2020.shp',
        "wisconsin_bg": f'{dir_path}/shapefiles/wisconsin/tl_2010_55_bg10.shp',

    # wyoming
        "wyoming_bg": f'{dir_path}/shapefiles/wyoming/tl_2010_56_bg10.shp',

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
                #assert(len(districtr_assignment[node_id]) == 1)
                assignment[node] = districtr_assignment[node_id][0]
            else:
                assignment[node] = districtr_assignment[node_id]
        else:
            # We assign to -1
            assignment[node] = -1
    return assignment

cached_gerrychain_graphs = {}

@app.route('/debug_info_tdMnhRDXgKlukM7a', methods=['POST'])
def debug_info():
    proc_id = os.getpid()
    response = flask.jsonify(proc_id)
    return response

state_jsons = {"louisiana": f'{dir_path}/vra-data/louisiana/data.json',
              "la_vra": f'{dir_path}/vra-data/louisiana/data.json',
              "tx_vra": f'{dir_path}/vra-data/texas/data.json'}

# Takes a Districtr JSON and returns vra effectiveness scores for each of the districts.
@app.route('/vra', methods=['POST'])
def vra_effectiveness():
    plan = request.get_json()
    state = plan['placeId'] # get the state of the Districtr plan
    groups = plan["groups"]
    seq_id = plan["seq_id"]

    if state in state_jsons:
        print(state)
        with open(state_jsons[state], "r") as fin:
            st_data = json.load(fin)
            data = st_data["data"]
        if state == "louisiana":
                data["partId"] = "Code"
        else:
            data["partId"] = data["geo_id"]
        rs = {}
        for minority in groups:
            for k, v in st_data["csvs"].items():
                data[k] = pd.read_csv(f'{dir_path}/' + v.format(minority))
            r = district_vra_effectiveness(plan["assignment"], data, minority)
            rs[minority] = r
        response = flask.jsonify({"seq_id": seq_id, "data": rs})
    else:
        response = flask.jsonify({'error': "VRA effectiveness score not supported for this state"})
    print("done")
    return response

@app.route('/demographics', methods=['POST'])
def sideload_columns():
    details = request.get_json()

    shapefile_code = details['id']
    if ('unitType' in details) and ('blockgroups' in details['unitType']) and ('_bg' not in shapefile_code):
        shapefile_code += '_bg'

    keyCol = details['keyColumn']
    units = details['units']

    rows = []
    with fiona.open(state_shapefile_paths[shapefile_code], "r") as source:
        for f in source:
            try:
                if f["properties"][keyCol] in units:
                    rows.append(f["properties"])
            except:
                r = 1

    return flask.jsonify(rows)

@app.route('/shp', methods=['POST'])
def shp_export():
    plan = request.get_json()

    state = plan['placeId'] # get the plan id of the Districtr plan
    shapefile_code = state
    if plan['units']['id'] == 'blockgroups' and '_bg' not in shapefile_code:
        shapefile_code += '_bg'
    elif plan['units']['id'] == 'blocks' and state in ['elpasotx']:
        shapefile_code += '_b'

    if plan['units']['id'] == 'precincts_02_10':
        shapefile_code += '_02'
    elif plan['units']['id'] == 'precincts_12_16':
        shapefile_code += '_12'

    if shapefile_code not in state_shapefile_paths:
        return 'no shapefile available'

    with fiona.open(state_shapefile_paths[shapefile_code], "r") as source:

        # Copy the source schema and add two new properties.
        sink_schema = source.schema
        sink_schema["properties"]["districtr"] = "int"

        randcode = str(randint(1000,9999))

        coi_mode = ("type" in plan["problem"]) and (plan["problem"]["type"] == "community")
        if coi_mode:
            sink_schema["properties"]["community"] = "str"
            if "place" in plan and "landmarks" in plan["place"] and "data" in plan["place"]["landmarks"]:
                with open("/tmp/export-" + randcode + ".geojson", "w") as gjo:
                    gjo.write(json.dumps(plan["place"]["landmarks"]["data"]))
            else:
                system("rm /tmp/export-" + randcode + ".geojson")

        belongto = {}
        pdex = 0
        for part in plan["parts"]:
            belongto[part["id"]] = pdex
            pdex += 1

        # Create a sink for processed features with the same format and
        # coordinate reference system as the source.
        fname = "/tmp/export-" + randcode
        with fiona.open(
            fname + '.shp',
            "w",
            crs=source.crs,
            driver=source.driver,
            schema=sink_schema,
        ) as sink:
            idkey = plan["idColumn"]["key"]

            for f in source:
                ukey = f["properties"][idkey]
                if str(ukey) in plan["assignment"]:
                    f["properties"].update(
                        districtr=plan["assignment"][str(ukey)][0] + 1
                    )
                    if coi_mode:
                        kdex = plan["assignment"][str(ukey)]
                        if isinstance(kdex, list):
                            kdex = kdex[0]
                        f["properties"].update(
                            community=plan["parts"][belongto[kdex]]["name"]
                        )
                elif coi_mode:
                    # don't include unmapped parts of state/city in COI export
                    continue
                else:
                    f["properties"].update(
                        districtr=-1
                    )
                    if ukey in plan["assignment"]:
                        f["properties"].update(
                            districtr=plan["assignment"][ukey][0] + 1
                        )
                    else:
                        try:
                            if int(ukey) in plan["assignment"]:
                                f["properties"].update(
                                    districtr=plan["assignment"][int(ukey)][0] + 1
                                )
                        except:
                            p = 1
                #blank = 1
                sink.write(f)

        system('zip ' + fname + '.zip ' + fname + '.*')
        return send_file(
            open(fname + '.zip', 'rb'),
            mimetype='application/zip',
            as_attachment=True,
            attachment_filename='export.zip')

@app.route('/geojson', methods=['POST'])
def gj_export():
    plan = request.get_json()

    state = plan['placeId'] # get the plan id of the Districtr plan
    shapefile_code = state
    if plan['units']['id'] == 'blockgroups' and '_bg' not in shapefile_code:
        shapefile_code += '_bg'

    if plan['units']['id'] == 'precincts_02_10':
        shapefile_code += '_02'
    elif plan['units']['id'] == 'precincts_12_16':
        shapefile_code += '_12'

    if shapefile_code not in state_shapefile_paths:
        return 'no shapefile available'

    with fiona.open(state_shapefile_paths[shapefile_code], "r") as source:

        # Copy the source schema and add two new properties.
        sink_schema = source.schema
        sink_schema["properties"]["districtr"] = "int"

        randcode = str(randint(1000,9999))

        coi_mode = ("type" in plan["problem"]) and (plan["problem"]["type"] == "community")
        if coi_mode:
            sink_schema["properties"]["community"] = "str"
            if "place" in plan and "landmarks" in plan["place"] and "data" in plan["place"]["landmarks"]:
                with open("/tmp/landmarks-" + randcode + ".geojson", "w") as gjo:
                    gjo.write(json.dumps(plan["place"]["landmarks"]["data"]))
            else:
                system("rm /tmp/landmarks-" + randcode + ".geojson")

        # Create a sink for processed features with the same format and
        # coordinate reference system as the source.
        fname = "/tmp/export-" + randcode
        with fiona.open(
            fname + '.geojson',
            "w",
            crs=source.crs,
            driver="GeoJSON",
            schema=sink_schema,
        ) as sink:
            idkey = plan["idColumn"]["key"]

            for f in source:
                ukey = f["properties"][idkey]
                try:
                    if str(ukey) in plan["assignment"]:
                        f["properties"].update(
                            districtr=plan["assignment"][str(ukey)][0] + 1
                        )
                        if coi_mode:
                            f["properties"].update(
                                community=plan["parts"][plan["assignment"][str(ukey)][0]]["name"]
                            )
                    elif coi_mode:
                        # don't include unmapped parts of state/city in COI export
                        continue
                    else:
                        f["properties"].update(
                            districtr=-1
                        )
                        if int(ukey) in plan["assignment"]:
                            f["properties"].update(
                                districtr=plan["assignment"][int(ukey)][0] + 1
                            )
                except:
                    blank = 1
                sink.write(f)

        system('zip ' + fname + '.zip ' + fname + '.geojson ' + fname.replace('export', 'landmarks') + '.geojson')
        return send_file(
            open(fname + '.zip', 'rb'),
            mimetype='application/zip',
            as_attachment=True,
            attachment_filename='export.zip')

@app.route('/picture2', methods=['GET'])
def pic_gen():
    origin = request.args.get('id', '')
    p = mdb.plans.find_one({ 'simple_id': int(origin) })
    if p is None:
        return 'none found'

    plan = p['plan']
    state = plan['placeId'] # get the plan id of the Districtr plan

    shapefile_code = state
    if plan['units']['id'] == 'blockgroups' and '_bg' not in shapefile_code:
        shapefile_code += '_bg'
        if state in ['indiana', 'colorado', 'michigan']:
            state += '_bg'
    elif plan['units']['id'] == 'precincts_02_10':
        shapefile_code += '_02'
        state += '_02'
    elif plan['units']['id'] == 'precincts_12_16':
        shapefile_code += '_12'
        state += '_12'

    if shapefile_code not in state_shapefile_paths:
        return 'no shapefile available'

    if "assignment" in plan:
        assignment = plan["assignment"]
    else:
        assignment = {}
    id_column_key = plan["idColumn"]["key"]

    geometries = gpd.read_file(state_shapefile_paths[shapefile_code])
    if 'pennsylvania' in state:
        geometries = geometries.to_crs(epsg=26918)
    elif state == 'michigan_bg':
        geometries = geometries.to_crs(epsg=6493)
        #geometries['GEOID10'] = geometries['GEOID10'].astype('str')
        #geometries['GEOID10'] = geometries['GEOID10'].astype('int')


    def coloration(row):
        cs_bright = ["#555555", "#0099cd",
    "#ffca5d",
    "#00cd99",
    "#99cd00",
    "#cd0099",
    "#9900cd",
    "#8dd3c7",
    "#bebada",
    "#fb8072",
    "#80b1d3",
    "#fdb462",
    "#b3de69",
    "#fccde5",
    "#bc80bd",
    "#ccebc5",
    "#ffed6f",
    "#ffffb3",
    "#a6cee3",
    "#1f78b4",
    "#b2df8a",
    "#33a02c",
    "#fb9a99",
    "#e31a1c",
    "#fdbf6f",
    "#ff7f00",
    "#cab2d6",
    "#6a3d9a",
    "#b15928",
    "#64ffda",
    "#00B8D4",
    "#A1887F",
    "#76FF03",
    "#DCE775",
    "#B388FF",
    "#FF80AB",
    "#D81B60",
    "#26A69A",
    "#FFEA00",
    "#6200EA"]
        if (row[id_column_key] in assignment):
            idx = assignment[row[id_column_key]]
            if isinstance(idx, list):
                idx = idx[0]
            idx += 1
            if idx >= len(cs_bright) - 1:
                idx = (idx % (len(cs_bright) - 1)) + 1
            return cs_bright[idx]
        elif (str(row[id_column_key]) in assignment):
            idx = assignment[str(row[id_column_key])]
            if isinstance(idx, list):
                idx = idx[0]
            idx += 1
            if idx >= len(cs_bright) - 1:
                idx = (idx % (len(cs_bright) - 1)) + 1
            return cs_bright[idx]
        else:
            return cs_bright[0]

    geometries['color'] = geometries.apply(lambda row: coloration(row), axis=1)
    plt = geometries.plot(figsize=(2.8, 2.8), color=geometries['color'])

    statewide = [
        'ma',
        'ma_02',
        'ma_12',
        'nc',
        'new_mexico',
        'new_mexico_bg',
        'wadc',
        'dc',
        'indianaprec',
        'wisco2019acs',
        'puertorico_prec',
    ]

    select = geometries[geometries['color'] != '#555555']
    if 'state' not in plan['place']:
        plan['place']['state'] = plan['placeId']
    if (len(select) > 0) and ((len(select) < len(geometries) / 3) or ((plan['place']['state'].lower().replace(' ', '') not in plan['placeId']) and (plan['placeId'] not in statewide))):
        minx, miny, maxx, maxy = select.total_bounds
        plt.set_xlim([minx,maxx])
        plt.set_ylim([miny,maxy])

    plt.set_axis_off()

    pic_IObytes = io.BytesIO()
    plt.figure.savefig(pic_IObytes, format='png')
    pic_IObytes.seek(0)
    pic_hash = str(base64.b64encode(pic_IObytes.read()))
    #plt.plot.close()

    mdb.plans.update_one({ 'simple_id': int(origin) }, { '$set': { 'screenshot2': 'data:image/png;base64,' + pic_hash[2:-1] } })

    return "done"

@app.route('/picture', methods=['POST'])
def plan_pic():
    plan = request.get_json()

    state = plan['placeId'] # get the plan id of the Districtr plan

    shapefile_code = state
    if plan['units']['id'] == 'blockgroups' and '_bg' not in shapefile_code:
        shapefile_code += '_bg'
        if state in ['indiana', 'colorado', 'michigan']:
            state += '_bg'
    elif plan['units']['id'] == 'precincts_02_10':
        shapefile_code += '_02'
        state += '_02'
    elif plan['units']['id'] == 'precincts_12_16':
        shapefile_code += '_12'
        state += '_12'

    if shapefile_code not in state_shapefile_paths:
        return 'no shapefile available'

    assignment = plan["assignment"]
    id_column_key = plan["idColumn"]["key"]

    geometries = gpd.read_file(state_shapefile_paths[shapefile_code])
    if 'pennsylvania' in state:
        geometries = geometries.to_crs(epsg=26918)
    elif state == 'michigan_bg':
        geometries = geometries.to_crs(epsg=6493)
        #geometries['GEOID10'] = geometries['GEOID10'].astype('str')
        #geometries['GEOID10'] = geometries['GEOID10'].astype('int')


    def coloration(row):
        cs_bright = ["#555555", "#0099cd",
    "#ffca5d",
    "#00cd99",
    "#99cd00",
    "#cd0099",
    "#9900cd",
    "#8dd3c7",
    "#bebada",
    "#fb8072",
    "#80b1d3",
    "#fdb462",
    "#b3de69",
    "#fccde5",
    "#bc80bd",
    "#ccebc5",
    "#ffed6f",
    "#ffffb3",
    "#a6cee3",
    "#1f78b4",
    "#b2df8a",
    "#33a02c",
    "#fb9a99",
    "#e31a1c",
    "#fdbf6f",
    "#ff7f00",
    "#cab2d6",
    "#6a3d9a",
    "#b15928",
    "#64ffda",
    "#00B8D4",
    "#A1887F",
    "#76FF03",
    "#DCE775",
    "#B388FF",
    "#FF80AB",
    "#D81B60",
    "#26A69A",
    "#FFEA00",
    "#6200EA"]
        if row[id_column_key] in assignment:
            idx = assignment[row[id_column_key]]
            if isinstance(idx, list):
                idx = idx[0]
            idx += 1
            if idx > len(cs_bright):
                idx = idx % len(cs_bright)
            return cs_bright[idx]
        else:
            return cs_bright[0]

    geometries['color'] = geometries.apply(lambda row: coloration(row), axis=1)
    plt = geometries.plot(figsize=(2.8, 2.8), color=geometries['color'])

    statewide = [
        'ma',
        'ma_02',
        'ma_12',
        'nc',
        'new_mexico',
        'new_mexico_bg',
        'wadc',
        'dc',
        'indianaprec',
        'wisco2019acs',
        'puertorico_prec',
    ]

    select = geometries[geometries['color'] != '#555555']
    if (len(select) > 0) and ((len(select) < len(geometries) / 3) or ((plan['place']['state'].lower().replace(' ', '') not in plan['placeId']) and (plan['placeId'] not in statewide))):
        minx, miny, maxx, maxy = select.total_bounds
        plt.set_xlim([minx,maxx])
        plt.set_ylim([miny,maxy])

    plt.set_axis_off()

    pic_IObytes = io.BytesIO()
    plt.figure.savefig(pic_IObytes, format='png')
    pic_IObytes.seek(0)
    pic_hash = base64.b64encode(pic_IObytes.read())

    return str(pic_hash)

@app.route('/findBBox', methods=['GET'])
def bboxmark():
    place = request.args.get('place', '')
    if place in state_shapefile_paths or (place + "_bg") in state_shapefile_paths:
        clearplace = place
    else:
        return "unrecognized shapefile / id"

    ids = request.args.get('ids', '')
    connection = psycopg2.connect(user=user,
                            password=passw,
                            host=host,
                            port=port,
                            database="access")
    if(connection):
        cursor = connection.cursor()
        cursor.execute("select api.bbox_" + clearplace + "(%s)", (ids,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return flask.jsonify(result)
    return "no connection"

@app.route('/findCenter', methods=['GET'])
def centermark():
    place = request.args.get('place', '')
    if place in state_shapefile_paths or (place + "_bg") in state_shapefile_paths:
        clearplace = place
    else:
        return "unrecognized shapefile / id"

    ids = request.args.get('ids', '')
    connection = psycopg2.connect(user=user,
                            password=passw,
                            host=host,
                            port=port,
                            database="access")
    if(connection):
        cursor = connection.cursor()
        cursor.execute("select api.merged_" + clearplace + "(%s)", (ids,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return flask.jsonify(result)
    return "no connection"

@app.route('/contigv2', methods=['POST'])
# Takes a Districtr JSON and returns whether or not it's contiguous and number of cut edges.
def contiguity():
    plan = request.get_json()

    state = plan['placeId'] # get the state of the Districtr plan
    # Check if we already have a dual graph of the state

    if (plan['units']['id'] == 'blockgroups') and (state in ['indiana', 'colorado']):
        state += '_bg'

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
    partition = gerrychain.Partition(state_graph, assignment, updaters={})
    end_2 = time.time()
    print(f"Time taken to form partition from assignment: {end_2 - start_2}")

    district_connections = {}
    for part in partition.parts:
        if part != -1:
            # build district subgraph
            district_nodes = partition.parts[part]
            #district_connections[part] = len(district_nodes)
            district_subgraph = partition.graph.subgraph(district_nodes)

            # get connected components, put it into dict
            pieces = []
            for piece in nx.connected_components(district_subgraph):
                pieces.append(list(map(lambda c: state_graph.nodes[c][id_column_key], list(piece))))
            district_connections[part] = pieces

    response = flask.jsonify(district_connections)
    return response

# Takes a Districtr JSON and returns islands of unassigned places
# based on contigv2
@app.route('/unassigned', methods=['POST'])
def unassigned():
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
    assignment = form_assignment_from_state_graph(districtr_assignment, node_to_id, state_graph)
    partition = gerrychain.Partition(state_graph, assignment, updaters={})

    district_connections = {}
    for part in partition.parts:
        if part == -1:
            # build district subgraph
            district_nodes = partition.parts[part]
            #district_connections[part] = len(district_nodes)
            district_subgraph = partition.graph.subgraph(district_nodes)

            # get connected components, put it into dict
            pieces = []
            for piece in nx.connected_components(district_subgraph):
                pieces.append(list(map(lambda c: state_graph.nodes[c][id_column_key], list(piece))))
            district_connections[part] = pieces

    response = flask.jsonify(district_connections)
    return response

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
