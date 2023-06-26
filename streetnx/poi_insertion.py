import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx

import rtree
import itertools

from shapely.geometry import MultiPoint, LineString, Point
from shapely.ops import snap, split

pd.options.mode.chained_assignment = None

def initialize_pois(G, city, tags, crs = 'epsg:4326'):
    """
    Initialize POIs from OSM.

    Parameters
    ----------
    G : networkx graph
        graph of the city
    city : String
        city name
    tags : dict
        POI tags
    crs : string
        coordinate reference system

    Returns
    -------
    pois : GeoDataFrame
        POIs GeoDataFrame
    nodes : GeoDataFrame
        nodes GeoDataFrame
    edges : GeoDataFrame
        edges GeoDataFrame
    """

    # retrieve nodes and undirected edges from graph
    # undirected edges are retrieved, becase we only identify the nearest edge to a POI
    # and in a later step the missing reverse edges are added
    nodes, edges = ox.utils_graph.graph_to_gdfs(ox.utils_graph.get_undirected(G))

    # set u,v,k columns to the edges gdf
    u = [u for u,v,k in list(edges.index)]
    v = [v for u,v,k in list(edges.index)]
    k = [k for u,v,k in list(edges.index)]
    edges.index = range(0, len(edges))
    edges['u'] = u
    edges['v'] = v
    edges['k'] = k

    # set nodes index to unique values, while saving the osmids
    nodes['osmid'] = nodes.index
    nodes.index = range(0, len(nodes))

    # retrieve pois from osm
    pois = ox.geometries.geometries_from_place(city, buffer_dist=100, tags=tags)
    pois = pois.to_crs('epsg:4326')

    # select only pois that are defined as points (nodes in osm)
    # and set longitude, latitude and drop the multi-index
    pois = pois[pois['geometry'].geom_type == 'Point']
    pois['lon'] = pois['geometry'].apply(lambda p: p.x)
    pois['lat'] = pois['geometry'].apply(lambda p: p.y)
    pois = pois.droplevel('element_type')
    
    # set a primary key column, the pois must have a unique id
    pois['key'] = pois.index 

    return pois, nodes, edges

def connect_poi(pois, nodes, edges, key_col=None, projected_footways = False, node_pois = False, dict_tags = None, threshold=200, knn=5, meter_epsg=4326):
    """Connect and integrate a set of POIs into an existing road network.

    Given a road network in the form of two GeoDataFrames: nodes and edges,
    link each POI to the nearest edge (road segment) based on its projection
    point (PP) and generate a new integrated road network including the POIs,
    the projected points, and the connection edge.

    Args:
        pois (GeoDataFrame): a gdf of POI (geom: Point)
        nodes (GeoDataFrame): a gdf of road network nodes (geom: Point)
        edges (GeoDataFrame): a gdf of road network edges (geom: LineString)
        key_col (str): a unique key column of pois should be provided,
                       e.g., 'index', 'osmid', 'poi_number', etc.
                       Currently, this will be renamed into 'osmid' in the output.
                       [NOTE] For use in pandana, you may want to ensure this
                              column is numeric-only to avoid processing errors.
                              Preferably use unique integers (int or str) only,
                              and be aware not to intersect with the node key,
                              'osmid' if you use OSM data, in the nodes gdf.
        projected_footways (bool): whether to generate projected footways.
        node_pois (bool): whether to generate additional nodes for POIs, 
                        these nodes are only connected to the graph if projected_footways is True.
        dict_tags (dict): a dictionary of tags that the projected nodes will contain.
        threshold (int): the max length of a POI connection edge, POIs with
                         connection edge beyond this length will be removed.
                         The unit is in meters as crs epsg is set to 3857 by
                         default during processing.
        knn (int): k nearest neighbors to query for the nearest edge.
                   Consider increasing this number up to 10 if the connection
                   output is slightly unreasonable. But higher knn number will
                   slow down the process.
        meter_epsg (int): preferred EPSG in meter units. Suggested 3857 or 3395.

    Returns:
        nodes (GeoDataFrame): the original gdf with POIs and PPs appended
        edges (GeoDataFrame): the original gdf with connection edges appended
                              and existing edges updated (if PPs are present)

    Note:
        1. Make sure all three input GeoDataFrames have defined crs attribute.
           Try something like `gdf.crs` or `gdf.crs = 'epsg:4326'`.
           They will then be converted into epsg:3857 or specified meter_epsg for processing.
    """

    ## STAGE 0: initialization
    # 0-1: helper functions
    def find_kne(point, lines):
        dists = np.array(list(map(lambda l: l.distance(point), lines)))
        kne_pos = dists.argsort()[0]
        kne = lines.iloc[[kne_pos]]
        kne_idx = kne.index[0]
        return kne_idx, kne.values[0]

    def get_pp(point, line):
        """Get the projected point (pp) of 'point' on 'line'."""
        # project new Point to be interpolated
        pp = line.interpolate(line.project(point))  # PP as a Point
        return pp

    def split_line(line, pps):
        """Split 'line' by all intersecting 'pps' (as multipoint).

        Returns:
            new_lines (list): a list of all line segments after the split
        """
        # IMPORTANT FIX for ensuring intersection between splitters and the line
        # but no need for updating edges_meter manually because the old lines will be
        # replaced anyway
        line = snap(line, pps, 1e-8)  # slow?

        try:
            new_lines = list(split(line, pps))  # split into segments
            return new_lines
        except TypeError as e:
            print('Error when splitting line: {}\n{}\n{}\n'.format(e, line, pps))
            return []

    def update_nodes(nodes, new_points, ptype, meter_epsg=meter_epsg):
        """Update nodes with a list (pp) or a GeoDataFrame (poi) of new_points.
        
        Args:
            ptype: type of Point list to append, 'pp' or 'poi'
        """
        # create gdf of new nodes (projected PAPs)
        if ptype == 'pp':
            new_nodes = gpd.GeoDataFrame(new_points, columns=['geometry'], crs=f'epsg:{meter_epsg}')
            n = len(new_nodes)
            new_nodes['highway'] = node_highway_pp
            new_nodes['osmid'] = [int(max(nodes['osmid']) + i + 1) for i in range(n)]
            for tag in dict_tags:
                if tag not in pois_meter.columns:
                    continue 
                new_nodes[tag] = list(pois_meter[tag])
 
        # create gdf of new nodes (original POIs)
        elif ptype == 'poi':
            new_nodes = new_points[['geometry', key_col]]
            new_nodes.columns = ['geometry', 'osmid']
            new_nodes['highway'] = node_highway_poi

        else:
            print("Unknown ptype when updating nodes.")

        # merge new nodes (it is safe to ignore the index for nodes)
        gdfs = [nodes, new_nodes]
        nodes = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True, sort=False),
                                 crs=gdfs[0].crs)

        return nodes, new_nodes  # all nodes, newly added nodes only

    def update_edges(edges, new_lines, replace):
        """
        Update edge info by adding new_lines; or,
        replace existing ones with new_lines (n-split segments).

        Args:
            replace: treat new_lines (flat list) as newly added edges if False,
                     else replace existing edges with new_lines (often a nested list)
        
        Note:
            kne_idx refers to 'fid in Rtree'/'label'/'loc', not positional iloc
        """
        # for interpolation (split by pp): replicate old line
        if replace:
            # create a flattened gdf with all line segs and corresponding kne_idx
            kne_idxs = list(line_pps_dict.keys())
            lens = [len(item) for item in new_lines]
            new_lines_gdf = gpd.GeoDataFrame(
                {'kne_idx': np.repeat(kne_idxs, lens),
                 'geometry': list(itertools.chain.from_iterable(new_lines))})
            # merge to inherit the data of the replaced line
            cols = list(edges.columns)
            cols.remove('geometry')  # don't include the old geometry
            new_edges = new_lines_gdf.merge(edges[cols], how='left', left_on='kne_idx', right_index=True)
            new_edges.drop('kne_idx', axis=1, inplace=True)
            new_lines = new_edges['geometry']  # now a flatten list
        # for connection (to external poi): append new lines
        else:
            new_edges = gpd.GeoDataFrame(pois[[key_col]], geometry=new_lines, columns=[key_col, 'geometry'])
            new_edges['oneway'] = False
            new_edges['reversed'] = False
            new_edges['highway'] = edge_highway
            new_edges['k'] = 0

        # update features (a bit slow)
        new_edges['from'] = new_edges['geometry'].map(
            lambda x: nodes_id_dict.get(list(x.coords)[0], None))
        new_edges['to'] = new_edges['geometry'].map(
            lambda x: nodes_id_dict.get(list(x.coords)[-1], None))
        new_edges['osmid'] = [list(x) for x in zip(new_edges['from'], new_edges['to'])]

        x = [coord.xy[0] for coord in new_edges['geometry']]
        y = [coord.xy[1] for coord in new_edges['geometry']]

        new_edges['length'] = list(distance(x, y))
        new_edges['length'][np.isnan(new_edges['length'])] = 0

        # remember to reindex to prevent duplication when concat
        start = edges.index[-1] + 1
        stop = start + len(new_edges)
        new_edges.index = range(start, stop)

        # for interpolation: remove existing edges
        if replace:
            edges = edges.drop(kne_idxs, axis=0)
        # for connection: filter invalid links
        else:
            valid_pos = np.where(new_edges['length'] <= threshold)[0]
            n = len(new_edges)
            n_fault = n - len(valid_pos)
            f_pct = n_fault / n * 100
            print("Remove faulty projections: {}/{} ({:.2f}%)".format(n_fault, n, f_pct))
            new_edges = new_edges.iloc[valid_pos]  # use 'iloc' here

        # merge new edges
        dfs = [edges, new_edges]
        edges = gpd.GeoDataFrame(pd.concat(dfs, ignore_index=False, sort=False), crs=dfs[0].crs)

        # all edges, newly added edges only
        return edges, new_edges

    def distance(x, y):
        for i in range(len(x)):
            dist = 0
            for j in range(1, len(x[i])):
                lat1 = y[i][j - 1]
                lng1 = x[i][j - 1]
                lat2 = y[i][j]
                lng2 = x[i][j]
                dist += ox.distance.great_circle_vec(lat1, lng1, lat2, lng2)
            yield dist.round(3)

    # 0-2: configurations
    # set poi arguments
    node_highway_pp = 'projected_pap'  # POI Access Point
    node_highway_poi = 'poi'
    edge_highway = 'projected_footway'
    osmid_prefix = 9990000000

    # convert CRS
    pois_meter = pois.to_crs(epsg=meter_epsg)
    nodes_meter = nodes.to_crs(epsg=meter_epsg)
    edges_meter = edges.to_crs(epsg=meter_epsg)

    # add key_col to nodes
    if key_col not in pois_meter:
        pois[key_col] = [int(osmid_prefix + i) for i in range(len(pois))]
        pois_meter[key_col] = [int(osmid_prefix + i) for i in range(len(pois_meter))]

    # build rtree
    print("Building rtree...")
    Rtree = rtree.index.Index()
    [Rtree.insert(fid, geom.bounds) for fid, geom in edges_meter['geometry'].iteritems()]

    ## STAGE 1: interpolation
    # 1-1: update external nodes (pois)
    if node_pois:
        print("Updating external nodes...")
        nodes_meter, _ = update_nodes(nodes_meter, pois_meter, ptype='poi', meter_epsg=meter_epsg)

    # 1-2: update internal nodes (interpolated pps)
    # locate nearest edge (kne) and projected point (pp)
    print("Projecting POIs to the network...")
    pois_meter['near_idx'] = [list(Rtree.nearest(point.bounds, knn))
                              for point in pois_meter['geometry']]  # slow
    pois_meter['near_lines'] = [edges_meter['geometry'][near_idx]
                                for near_idx in pois_meter['near_idx']]  # very slow
    pois_meter['kne_idx'], knes = zip(
        *[find_kne(point, near_lines) for point, near_lines in
          zip(pois_meter['geometry'], pois_meter['near_lines'])])  # slow
    pois_meter['pp'] = [get_pp(point, kne) for point, kne in zip(pois_meter['geometry'], knes)]

    # update nodes
    print("Updating internal nodes...")
    nodes_meter, _ = update_nodes(nodes_meter, list(pois_meter['pp']), ptype='pp', meter_epsg=meter_epsg)
    nodes_coord = nodes_meter['geometry'].map(lambda x: x.coords[0])
    nodes_id_dict = dict(zip(nodes_coord, nodes_meter['osmid'])) # .astype('Int64')

    # 1-3: update internal edges (split line segments)
    print("Updating internal edges...")
    # split
    line_pps_dict = {k: MultiPoint(list(v)) for k, v in pois_meter.groupby(['kne_idx'])['pp']}
    new_lines = [
        split_line(edges_meter['geometry'][idx], pps) 
        for idx, pps in line_pps_dict.items()
        ]  # bit slow
    edges_meter, _ = update_edges(edges_meter, new_lines, replace=True)

    ## STAGE 2: connection
    # 2-1: update external edges (projected footways connected to pois)
    # establish new_edges
    if (projected_footways):
        print("Updating external links...")
        pps_gdf = nodes_meter[nodes_meter['highway'] == node_highway_pp]
        new_lines = [LineString([p1, p2]) for p1, p2 in zip(pois_meter['geometry'], pps_gdf['geometry'])]
        edges_meter, _ = update_edges(edges_meter, new_lines, replace=False)

    ## STAGE 3: output
    # convert CRS
    nodes = nodes_meter.to_crs(epsg=4326)
    edges = edges_meter.to_crs(epsg=4326)

    # preprocess for pandana
    nodes.index = nodes['osmid']  # IMPORTANT
    nodes['x'] = [p.x for p in nodes['geometry']]
    nodes['y'] = [p.y for p in nodes['geometry']]

    # report issues
    # - examine key duplication
    if len(nodes_meter) != len(nodes_id_dict):
        print("NOTE: duplication in node coordinates keys")
        print("Nodes count:", len(nodes_meter))
        print("Node coordinates key count:", len(nodes_id_dict))
    # - examine missing nodes
    print("Missing 'from' nodes:", len(edges[edges['from'] == None]))
    print("Missing 'to' nodes:", len(edges[edges['to'] == None]))

    return nodes, edges

def graph_from_gpd(edges, nodes, crs = 'epsg:4326'):
    """
    Create a graph from GeoDataFrame of edges and nodes.

    Parameters
    ----------
    edges : GeoDataFrame
        edges GeoDataFrame
    nodes : GeoDataFrame
        nodes GeoDataFrame
    crs : string
        coordinate reference system

    Returns
    -------
    V : networkx graph
        graph
    """

    def add_reverse_edges(G):
        from shapely.geometry import LineString
        oneway_values = {"yes", "true", "1", "-1", "reverse", "T", "F", 1, -1, True}
        for u, v, data in list(G.edges(data=True)):

            # check if the data contains a "oneway" indicator
            if "oneway" in data and (bool(set(list(data["oneway"])) & oneway_values) if isinstance(data["oneway"], list) else data["oneway"] in oneway_values): 
                continue
            new_data = data.copy()
            new_data["reversed"] = not new_data["reversed"]
            new_data["geometry"] = LineString(list(new_data["geometry"].coords)[::-1])
            if "key" in new_data:
                new_data.pop("key")

            # check if edge v,u exists in G
            key_list = list(G[u][v])
            if G.has_edge(v, u):
                key_list += list(G[v][u])
            new_key = max(key_list) + 1

            G.add_edge(v,u, key = new_key, **new_data)

    # create graph based on edges gdf
    V = nx.from_pandas_edgelist(df = edges, source = 'from', target = 'to', edge_attr = True, create_using = nx.MultiDiGraph(), edge_key = 'k')

    # add node attributes to graph based on nodes gdf
    nx.set_node_attributes(V, nodes.set_index('osmid').to_dict('index'))

    # add crs to graph
    V.graph["crs"] = crs

    # add reverse edges to graph
    # because they were not in the edges gdf
    add_reverse_edges(V)

    return V

def graph_inserted_pois(G, pois, projected_ways = True, node_pois = True):

    # retrieve nodes and undirected edges from graph
    # undirected edges are retrieved, becase we only identify the nearest edge to a POI
    # and in a later step the missing reverse edges are added
    nodes, edges = ox.utils_graph.graph_to_gdfs(ox.utils_graph.get_undirected(G))

    if not nodes.crs or not edges.crs:
        nodes = nodes.set_crs("epsg:4326")
        edges = edges.set_crs("epsg:4326")

    # set u,v,k columns to the edges gdf
    u = [u for u,v,k in list(edges.index)]
    v = [v for u,v,k in list(edges.index)]
    k = [k for u,v,k in list(edges.index)]
    
    edges.index = range(0, len(edges))
    edges['u'] = u
    edges['v'] = v
    edges['k'] = k

    # set nodes index to unique values, while saving the osmids
    nodes['osmid'] = nodes.index
    nodes.index = range(0, len(nodes))

    # retrieve pois from osm
    pois = gpd.GeoDataFrame(pois)
    pois['geometry'] = [Point(point[0], point[1]) for point in pois[['lon', 'lat']].values]
    pois = pois.set_crs("epsg:4326")

    # set a primary key column, the pois must have a unique id
    pois['key'] = pois.index 

    new_nodes, new_edges = connect_poi(pois, 
        nodes, 
        edges, 
        key_col='osmid', 
        projected_footways=projected_ways, 
        node_pois=node_pois,
        dict_tags={'name', 'amenity'}
    )

    return graph_from_gpd(new_edges, new_nodes)
