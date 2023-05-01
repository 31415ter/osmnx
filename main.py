import streetnx as snx
import osmnx as ox
import networkx as nx
from streetnx import utils as nsx_utils

if __name__ == '__main__':
    ox.settings.log_file=True
    ox.settings.log_console=True
    ox.settings.use_cache=True

    # ### GLADHEIDBESTRIJDING
    # depots = {
    #     "name" : ["Giesenweg", "Laagjes"],
    #      "lon" : [4.4279192, 4.5230457], 
    #      "lat" : [51.9263550, 51.8837905], 
    #     "amenity" : ["depot", "depot"]
    # }

    depots = {
        "name" : ["Giesenweg"],
         "lon" : [4.4279192], 
         "lat" : [51.9263550], 
        "amenity" : ["depot"]
    }


    # ### DELFT
    # depots = {
    #     "name": ["Depot"],
    #     "lon": [4.3575636],
    #     "lat": [52.0197675],
    #     "amenity": ["depot"]
    # }

    use_custom = False # Adjust which streetnetwork 
    cities = ["Rotterdam"]
    name = "_".join(cities)

    # ### Downloading graph and processing deadends
    # G = snx.download_graph(cities, use_custom = use_custom)
    # G = snx.process_deadends(G, depots)
    # 
    #
    # def get_required_edges():
    #     required_edges_df = snx.load_required_edges(G, required_cities=["Bedrijvenpark Noord-West"], buffer_dist = 0)
    #     gdf_nodes, gdf_edges = ox.utils_graph.graph_to_gdfs(G)
    # 
    #     required_edges_mask = gdf_edges.index.isin(required_edges_df.index.values)
    #     attr_required_bool = {gdf_edges.index[index] : required_edges_mask[index] for index in range(len(gdf_edges))}
    #     attr_avg_geometry = {required_edges_df.index[index] : required_edges_df.iloc[index]['average_geometry'] for index in range(len(required_edges_df))}
    # 
    #     nx.set_edge_attributes(G, attr_required_bool, name='required')
    #     nx.set_edge_attributes(G, attr_avg_geometry, name='average_geometry')
    #
    #
    # get_required_edges()
    # snx.save_graph(G, name + ("_road_network" if not use_custom else "_custom_network"))


    # ### Loading graph and saving distances
    # G = snx.load_graph(name + ("_road_network" if not use_custom else "_custom_network"))
    # snx.add_penalties(G)
    #
    #
    # def load_required_edges():
    #     nodes, edges = ox.utils_graph.graph_to_gdfs(G)
    #     mask = (edges['required'] == 'True')
    #     return edges.loc[mask, ["lanes", "length", "lanes:forward", "lanes:backward", "turn:lanes", "speed_kph", "oneway", "average_geometry"]]
    #
    #
    # required_edges_df = load_required_edges()
    # distances, predecessors = snx.get_all_shortest_paths(G, required_edges_df=required_edges_df, cores=8, name=name, size=500, max_speed=100)
    # snx.save_shortest_paths(name=name)

    # ### Saving lanes for the routing optimization  
    # G = snx.load_graph(name + ("_road_network" if not use_custom else "_custom_network"))
    # nodes, edges = ox.utils_graph.graph_to_gdfs(G)
    # mask = (edges['required'] == 'True')
    # required_edges_df = edges.loc[mask, ["lanes", "length", "lanes:forward", "lanes:backward", "turn:lanes", "speed_kph", "oneway", "average_geometry"]]


    # for col in required_edges_df.columns:
    #     if 'geometry' in col:
    #         continue
    #     elif not required_edges_df[col].apply(lambda x: not isinstance(x, list)).all():
    #         required_edges_df[col] = [[value] if not isinstance(value, list) else value for value in required_edges_df[col]]


    # distances_df, paths_df = snx.load_shortest_paths(name)
    # depots_list = nsx_utils.get_depot_nodes(G)
    # snx.save_lanes(name, required_edges_df, distances_df, depots_list)








#     ### Visualizing a solution
#     G = snx.load_graph(name + ("_road_network" if not use_custom else "_custom_network"))
#     distances, paths = snx.load_shortest_paths(name)

#     #required_edges_df = snx.load_required_edges(G, required_cities=["Rotterdam"])
#     nodes, edges = ox.utils_graph.graph_to_gdfs(G)
#     mask = (edges['required'] == 'True')
#     required_edges_df = edges.loc[mask, ["lanes", "length", "lanes:forward", "lanes:backward", "turn:lanes", "speed_kph", "oneway", "average_geometry"]]

#     depot_dict = nsx_utils.load_depot_indices(G, required_edges_df)
#     solution = [9990000001, 1855,1001,996,1003,1953,973,947,905,2108,2107,903,2556,1834,1829,918,937,935,932,934,928,951,958,2438,2436,933,914,897,1914,884,881,880,883,818,800,794,786,785,2414,2339,2416,2338,799,801,854,851,876,2063,853,875,877,2060,2059,2055,852,2056,2057,802,2337,772,2415,778,779,775,787,1955,784,773,774,793,790,796,795,789,766,765,691,453,674,611,668,2597,688,693,704,760,763,768,769,767,703,694,690,686,689,692,687,681,2347,2029,2026,2027,565,2028,2030,762,753,756,755,747,750,741,744,1836,1825,735,1827,1828,740,1823,1824,1826,2580,2579,1964,2576,745,2520,1918,1920,1917,1919,771,761,2025,746,715,2577,732,2581,739,748,757,764,770,798,797,819,2064,879,1913,906,1915,941,939,938,2731,1831,2574,1832,1833,956,2151,1010,1006,1009,2733,1017,2380,2516,2448,2350,2352,2573,2452,1959,2318,2322,2498,2190,2189,2513,2295,2496,2455,1069,2688,1931,1052,1053,457,1044,1043,1042,1049,2366,1068,1961,1935,1938,1076,1077,2495,2293,2191,2321,1966,1099,2699,1101,2036,2525,1145,1147,2250,1175,2582,2039,1146,1162,1839,1841,2526,2700,2527,1176,1179,1188,2044,2043,1180,1214,2592,2184,1155,1142,2764,2394,1132,1128,1134,1135,1939,1135,1822,1820,1121,1109,1123,1131,1129,1190,1217,1218,2627,1258,2628,2584,1283,1280,1282,1330,1365,1362,2501,2499,1353,1356,2732,1852,1849,1850,1848,2024,2023,1354,1359,1363,1366,2166,2164,2165,1491,1494,1519,1520,2168,2171,2050,2172,1571,1574,1585,2175,2181,2179,2180,1630,1865,1637,1640,1643,1642,2405,1868,1648,2162,1658,1661,1650,1664,1656,1659,2161,1652,1647,1867,2406,1635,1638,2221,2222,2218,1646,2224,2226,2779,2228,1668,1672,1670,2780,2227,2225,2219,1976,2220,1639,1866,1632,2401,1629,1594,2178,1628,2177,2176,1586,2174,1570,1320,1322,1329,1331,2714,1864,1312,1315,1317,1316,1324,1323,1321,1314,1584,1978,2409,1573,1575,1572,1570,1328,1326,2714,1312,1334,1336,1340,1373,2617,2614,2612,2611,2615,2616,1383,1387,1389,1392,1401,1396,1408,1413,1416,1427,1404,1412,1414,1420,1429,1441,1439,2214,2208,1451,2215,1453,1440,1381,1375,1374,1437,2211,2213,1438,2212,1454,2209,2207,2210,1508,1510,1529,1557,1559,1567,1569,1595,1607,1613,1620,1662,1685,1689,1687,1684,2216,2679,1876,1678,1869,1871,1673,1674,1671,1666,1665,1667,1669,1872,1675,1873,1874,1870,1875,1683,1686,1882,1880,1698,1878,1879,1697,1881,1707,1706,1709,1710,1877,1688,2453,2683,2682,2680,2678,2684,2681,2217,1634,1621,1606,2590,1587,1589,1591,1579,1580,2589,1977,2409,1537,1530,1989,1522,1502,1887,2671,2708,1481,1476,1475,1469,1468,1447,1424,1400,1369,1371,1847,1851,1358,1351,1357,1343,2500,1327,1346,1360,1347,1372,2709,2672,2674,2670,2675,1486,2673,2742,1986,1562,1990,1987,2340,2734,2481,2231,2230,2377,1561,2403,2418,2404,2402,1984,1905,1908,1907,2476,2478,2474,2471,2473,1550,1551,2480,2479,1906,1983,1555,1560,1991,2748,2586,2752,2505,2434,2433,1988,1563,1549,2743,1525,1521,1524,1527,1538,1989,1526,2280,1514,1479,2531,1350,1301,1300,2624,2282,2357,2236,1268,1271,2235,2623,2522,1191,1197,1223,1253,1261,1273,1288,2281,1297,1296,2643,1309,1310,1325,1308,1295,2566,2621,1278,1290,1303,1306,1302,1294,2620,2619,1948,1266,1263,2528,2736,1157,1154,2563,2320,2379,2451,2349,2571,2570,1835,2400,1020,994,991,987,986,983,2595,978,980,993,998,792,737
# ]
#     route_map = snx.plot_route(G, solution=solution, depot_dict=depot_dict, paths=paths)
#     snx.save_route(route_map, name + "_1A")
#     #save_ar3(route_map, "1")