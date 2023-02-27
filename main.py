import streetnx as snx
import osmnx as ox

from streetnx import utils as nsx_utils

if __name__ == '__main__':

    ox.settings.log_file=True
    ox.settings.log_console=True
    ox.settings.use_cache=True

    depots = {
        "name" : ["Giesenweg", "Laagjes"],
         "lon" : [4.4279192, 4.5230457], 
         "lat" : [51.9263550, 51.8837905], 
        "amenity" : ["depot", "depot"]
    }

    # depots = {
    #     "name": ["Depot"],
    #     "lon": [4.3575636],
    #     "lat": [52.0197675],
    #     "amenity": ["depot"]
    # }

    use_custom = False # Adjust which streetnetwork 
    cities = ["Rotterdam", "Hoogvliet", "Schiedam"]
    name = "_".join(cities)

    ### Downloading graph and processing deadends
    # G = snx.download_graph(cities, use_custom = use_custom)
    # G = snx.process_deadends(G, depots)

    # # TODO PLACE THIS INTO FUNCTION...
    # import networkx as nx
    # required_edges_df = snx.load_required_edges(G, required_cities=["Rotterdam", "Hoogvliet"], buffer_dist = 0)
    # gdf_nodes, gdf_edges = ox.utils_graph.graph_to_gdfs(G)

    # required_edges_mask = gdf_edges.index.isin(required_edges_df.index.values)
    # attr_required_bool = {gdf_edges.index[index] : required_edges_mask[index] for index in range(len(gdf_edges))}
    # attr_avg_geometry = {required_edges_df.index[index] : required_edges_df.iloc[index]['average_geometry'] for index in range(len(required_edges_df))}

    # nx.set_edge_attributes(G, attr_required_bool, name='required')
    # nx.set_edge_attributes(G, attr_avg_geometry, name='average_geometry')

    # snx.save_graph(G, name + ("_road_network" if not use_custom else "_custom_network"))


    # # ### Loading graph and saving distances
    # G = snx.load_graph(name + ("_road_network" if not use_custom else "_custom_network"))
    # snx.add_penalties(G)
    
    # ## TODO LOAD REQUIRED_EDGES_DF
    # nodes, edges = ox.utils_graph.graph_to_gdfs(G)
    # mask = (edges['required'] == 'True')
    # required_edges_df = edges.loc[mask, ["lanes", "length", "lanes:forward", "lanes:backward", "turn:lanes", "speed_kph", "oneway", "average_geometry"]]

    # distances, predecessors = snx.get_all_shortest_paths(G, required_edges_df=required_edges_df, cores=8, name = name, size=500, max_speed=100)
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



    def save_ar3(route_map, route_name):
        import folium
        polylines = []

        for key, val in route_map._children.items():
            if isinstance(val, folium.features.PolyLine):
                polylines.append(val)

        lat_pts = []
        lng_pts = []
        change_pts = []
        # Print the polyline options and data
        for ii in range(len(polylines)):
            type = ''
            if polylines[ii].options['color'] == '#ffff00':
                type = 'heenweg'
                print('heenweg')
            elif polylines[ii].options['color'] == '#FF0000':
                type = 'actie'
                print('actie')
            elif polylines[ii].options['color'] == '#0000FF':
                type = 'deadhead'
                print('deadhead')
            elif polylines[ii].options['color'] == '#fb00ff':
                type = 'terugweg'
                print('terugweg')

            if ii == (len(polylines) - 1):
                lng = [coord[0] for coord in polylines[ii].locations]
                lat = [coord[1] for coord in polylines[ii].locations]
            else:
                lng = [coord[0] for coord in polylines[ii].locations[:-1]]
                lat = [coord[1] for coord in polylines[ii].locations[:-1]]

            # remove duplicates, stupid polylines...
            temp_lat = []
            temp_lng = []

            for ii in range(len(lat)):
                if (lat[ii] not in temp_lat) or (lng[ii] not in temp_lng):
                    temp_lat.append(lat[ii])
                    temp_lng.append(lng[ii])

            lat = temp_lat
            lng = temp_lng

            lat_pts.extend(lat)
            lng_pts.extend(lng)
            if type != 'actie':
                change_pts.extend([0] * len(lat))
            else:
                change_pts.extend([1] * len(lat))

        distances = []
        cum_distance = 0
        status = 0
        changes = []
        for ii in range(len(lat_pts)):
            if ii == 0:
                dist = 0
            else:
                dist = int(ox.distance.great_circle_vec(lat_pts[ii-1], lng_pts[ii-1], lat_pts[ii], lng_pts[ii]) * 100)
                assert dist > 0, "wtf!"
            cum_distance += dist
            distances.append(cum_distance)

            if change_pts[ii] != status:
                status = change_pts[ii]
                changes.append((cum_distance, status))

        FILE_PATH = "./data/"
        # Open a new text file in write mode
        with open(FILE_PATH + name + f'_{route_name}.ar3', 'w') as file:

            # Write some lines of text to the file
            file.write('Ar3Version: 3\n')
            file.write('Creator: PAJ Versfelt\n')
            file.write('Last edited by: unknown\n')
            file.write('MachineType: standardspreader\n')
            file.write('SoundFiles: \n')
            file.write('RouteID:Test_route_20230227\n')
            file.write('RouteTimestamp: 20230227 12.00.00\n')
            file.write('WayPoints: Longitude, Latitude, DistanceFromStartInCm\n')

            for ii in range(len(lat_pts)):
                file.write(f'WayPoint[{ii}]:{lat_pts[ii]},{lng_pts[ii]},{distances[ii]}\n')

            file.write('ChangePoints: DistanceFromStartInCm, SpreadSprayOnOff, SprayModeOnOff, Max, SecMat,Dosage, WidthLeft, WidthRight, SecDos, WidthLeftSpraying, WidthRightSpraying, CombiPercentage, HopperSelection, Marker, Message, TankSelection\n')
            file.write('ChangePoint[0]:0,0,0,0,1,1000,500,200,500,0,600,30,0,1,,0\n')
            for ii in range(1, len(changes)):
                file.write(f'ChangePoint[{ii}]:{changes[ii][0]},{changes[ii][1]},,,,,,,,,,,,,,\n')

    ### Visualizing a solution
    G = snx.load_graph(name + ("_road_network" if not use_custom else "_custom_network"))
    distances, paths = snx.load_shortest_paths(name)

    #required_edges_df = snx.load_required_edges(G, required_cities=["Rotterdam"])
    nodes, edges = ox.utils_graph.graph_to_gdfs(G)
    mask = (edges['required'] == 'True')
    required_edges_df = edges.loc[mask, ["lanes", "length", "lanes:forward", "lanes:backward", "turn:lanes", "speed_kph", "oneway", "average_geometry"]]

    depot_dict = nsx_utils.load_depot_indices(G, required_edges_df)
    solution = [9990000001, 1855,1001,996,1003,1953,973,947,905,2108,2107,903,2556,1834,1829,918,937,935,932,934,928,951,958,2438,2436,933,914,897,1914,884,881,880,883,818,800,794,786,785,2414,2339,2416,2338,799,801,854,851,876,2063,853,875,877,2060,2059,2055,852,2056,2057,802,2337,772,2415,778,779,775,787,1955,784,773,774,793,790,796,795,789,766,765,691,453,674,611,668,2597,688,693,704,760,763,768,769,767,703,694,690,686,689,692,687,681,2347,2029,2026,2027,565,2028,2030,762,753,756,755,747,750,741,744,1836,1825,735,1827,1828,740,1823,1824,1826,2580,2579,1964,2576,745,2520,1918,1920,1917,1919,771,761,2025,746,715,2577,732,2581,739,748,757,764,770,798,797,819,2064,879,1913,906,1915,941,939,938,2731,1831,2574,1832,1833,956,2151,1010,1006,1009,2733,1017,2380,2516,2448,2350,2352,2573,2452,1959,2318,2322,2498,2190,2189,2513,2295,2496,2455,1069,2688,1931,1052,1053,457,1044,1043,1042,1049,2366,1068,1961,1935,1938,1076,1077,2495,2293,2191,2321,1966,1099,2699,1101,2036,2525,1145,1147,2250,1175,2582,2039,1146,1162,1839,1841,2526,2700,2527,1176,1179,1188,2044,2043,1180,1214,2592,2184,1155,1142,2764,2394,1132,1128,1134,1135,1939,1135,1822,1820,1121,1109,1123,1131,1129,1190,1217,1218,2627,1258,2628,2584,1283,1280,1282,1330,1365,1362,2501,2499,1353,1356,2732,1852,1849,1850,1848,2024,2023,1354,1359,1363,1366,2166,2164,2165,1491,1494,1519,1520,2168,2171,2050,2172,1571,1574,1585,2175,2181,2179,2180,1630,1865,1637,1640,1643,1642,2405,1868,1648,2162,1658,1661,1650,1664,1656,1659,2161,1652,1647,1867,2406,1635,1638,2221,2222,2218,1646,2224,2226,2779,2228,1668,1672,1670,2780,2227,2225,2219,1976,2220,1639,1866,1632,2401,1629,1594,2178,1628,2177,2176,1586,2174,1570,1320,1322,1329,1331,2714,1864,1312,1315,1317,1316,1324,1323,1321,1314,1584,1978,2409,1573,1575,1572,1570,1328,1326,2714,1312,1334,1336,1340,1373,2617,2614,2612,2611,2615,2616,1383,1387,1389,1392,1401,1396,1408,1413,1416,1427,1404,1412,1414,1420,1429,1441,1439,2214,2208,1451,2215,1453,1440,1381,1375,1374,1437,2211,2213,1438,2212,1454,2209,2207,2210,1508,1510,1529,1557,1559,1567,1569,1595,1607,1613,1620,1662,1685,1689,1687,1684,2216,2679,1876,1678,1869,1871,1673,1674,1671,1666,1665,1667,1669,1872,1675,1873,1874,1870,1875,1683,1686,1882,1880,1698,1878,1879,1697,1881,1707,1706,1709,1710,1877,1688,2453,2683,2682,2680,2678,2684,2681,2217,1634,1621,1606,2590,1587,1589,1591,1579,1580,2589,1977,2409,1537,1530,1989,1522,1502,1887,2671,2708,1481,1476,1475,1469,1468,1447,1424,1400,1369,1371,1847,1851,1358,1351,1357,1343,2500,1327,1346,1360,1347,1372,2709,2672,2674,2670,2675,1486,2673,2742,1986,1562,1990,1987,2340,2734,2481,2231,2230,2377,1561,2403,2418,2404,2402,1984,1905,1908,1907,2476,2478,2474,2471,2473,1550,1551,2480,2479,1906,1983,1555,1560,1991,2748,2586,2752,2505,2434,2433,1988,1563,1549,2743,1525,1521,1524,1527,1538,1989,1526,2280,1514,1479,2531,1350,1301,1300,2624,2282,2357,2236,1268,1271,2235,2623,2522,1191,1197,1223,1253,1261,1273,1288,2281,1297,1296,2643,1309,1310,1325,1308,1295,2566,2621,1278,1290,1303,1306,1302,1294,2620,2619,1948,1266,1263,2528,2736,1157,1154,2563,2320,2379,2451,2349,2571,2570,1835,2400,1020,994,991,987,986,983,2595,978,980,993,998,792,737
]
    route_map = snx.plot_route(G, solution=solution, depot_dict=depot_dict, paths=paths)
    # snx.save_route(route_map, name + "_1A")
    save_ar3(route_map, "1")

    solution = [9990000001, 708,2336,2766,2767,670,634,601,595,1844,612,617,602,600,599,594,593,592,2657,630,666,655,654,657,656,582,571,570,564,562,561,558,557,2069,555,2072,2073,556,559,560,588,653,2054,2659,585,2656,525,1859,1860,2635,523,2633,1858,2631,2630,519,520,2324,2632,1857,2629,520,2325,522,524,525,2642,579,578,1838,624,2695,631,645,636,2693,2692,1893,2694,1894,1893,1892,1891,1889,1890,1859,1860,2634,347,342,337,332,335,334,415,339,361,345,340,336,330,325,322,329,380,321,295,291,284,384,385,425,422,370,252,243,236,372,396,238,237,399,397,371,395,394,234,235,413,233,393,409,410,407,406,408,411,231,240,261,262,402,278,403,290,441,442,301,305,307,451,434,275,274,269,266,450,259,2445,482,467,470,471,482,484,480,473,469,466,470,472,484,486,467,483,485,489,507,505,500,479,477,462,465,2111,2079,2075,2076,2080,2083,2110,463,476,478,501,509,512,518,517,521,527,569,566,568,572,642,646,648,677,678,2388,2725,647,650,651,2560,639,2104,2103,640,2561,2562,658,649,2726,2724,2722,575,573,2685,576,591,2153,563,528,526,515,2721,513,510,566,567,2686,583,587,608,643,659,662,676,697,2391,702,710,2662,2664,759,2665,2392,809,2667,859,886,2140,861,2669,2668,807,2667,859,866,2199,2198,2201,2203,2197,885,2131,895,2127,2206,2195,878,2188,2609,915,1055,1066,2454,1075,2728,1102,1922,1114,1117,1103,1100,2015,2017,2012,2010,1260,1241,1240,1238,2489,2490,2488,1232,1228,1208,1813,1200,26,25,213,159,216,47,48,36,46,40,45,146,29,28,31,32,30,41,39,34,44,43,49,42,37,33,215,27,1201,1814,1815,1943,1206,2484,2485,1239,1242,1246,1245,2009,1274,1277,1278,1305,2446,2648,1444,2502,2263,1517,1539,1540,1542,1547,1543,2544,2468,2465,1515,2601,1465,1461,2378,2427,2696,1455,1449,2100,2753,1352,2303,2306,2022,1183,1079,1078,2192,2186,2362,2385,727,2541,684,683,682,669,633,596,2411,607,610,614,613,2105,616,598,605,606,2106,2413,2412,628,629,667,2541,730,2287,2289,777,780,812,811,2384,2331,783,776,2603,2604,733,736,2287,2288,781,783,776,2604,719,2603,734,721,720,714,706,705,699,615,597,551,2066,2097,2094,2065,553,537,536,529,2067,533,2068,530,535,546,2070,2074,2071,554,545,547,542,534,541,532,531,538,539,544,543,548,549,2092,2096,2093,2085,2082,2081,2084,2077,2078,2091,2088,2090,2086,475,2087,2089,2095,552,550,604,609,675,698,711,2098,712,2540,2538,722,685,731,729,726,720,718,711,713,725,721,718,717,712,2540,2539,728,736,2289,780,2606,805,816,827,825,891,865,840,2330,822,2291,2387,2286,872,870,869,847,836,821,2386,810,813,817,2292,577,580,581,641,1846,664,663,652,2658,584,589,1845,603,635,671,696,2769,2768
]
    route_map = snx.plot_route(G, solution=solution, depot_dict=depot_dict, paths=paths)
    # snx.save_route(route_map, name + "_2A")
    save_ar3(route_map, "2")

    solution = [9990000000, 35,38,1942,1945,1816,1812,1811,1944,1207,1211,1210,1227,1225,1231,2483,2482,2486,2491,2487,1237,1259,2008,1999,1998,1086,1080,1072,1937,1936,2523,1040,2193,874,459,867,2559,806,808,2707,2666,758,2663,709,701,700,2389,2723,586,590,621,627,632,637,2137,661,673,672,644,665,660,2136,2138,638,2594,625,619,622,680,2135,2655,2654,456,894,901,909,910,2129,2421,2205,1033,1054,1932,1085,1957,1996,1997,2000,2005,2020,2021,2304,2393,1458,1631,2713,2494,2558,1614,1610,2590,1599,1598,2233,1590,1588,1593,1597,2407,1899,2591,2587,1626,1631,2712,1624,1622,1619,1618,1617,2558,1621,1609,1605,1600,1568,1566,2750,1558,1556,1528,1511,1509,1507,2408,1452,1442,1430,1426,1417,1418,1403,1395,1393,1388,1384,2613,2610,1368,1341,1338,1337,1333,1335,1324,1319,1321,1863,1119,1136,1138,1133,1940,1822,1821,1106,1126,1112,1122,1125,1127,2417,1137,2395,2765,1141,2396,2182,2183,2661,2046,1181,2706,2705,2252,2038,2037,2035,2033,2034,2450,2348,2515,2514,1019,1018,1015,2157,2155,2156,977,1967,943,892,893,919,931,2652,959,965,2147,2145,2146,979,985,982,940,2419,2343,962,961,2716,967,2345,963,921,922,902,890,841,2329,824,828,2334,2333,829,830,831,820,834,835,1856,842,844,845,846,848,858,857,863,898,2557,908,904,856,855,843,839,838,2519,832,826,823,822,2290,814,2332,782,2605,815,833,837,849,2285,871,873,2187,2608,2429,2390,2130,2363,927,925,2126,912,911,455,2121,458,2653,2690,2691,864,2134,679,626,623,620,2152,574,2555,516,2721,503,2118,377,2120,492,490,491,480,474,481,488,498,497,499,352,374,344,341,362,343,445,348,447,353,374,373,342,336,333,331,327,323,312,306,381,291,283,284,384,385,271,421,389,429,431,288,438,437,432,433,288,285,449,264,401,263,265,452,260,249,232,229,405,412,414,398,244,248,368,247,245,369,241,242,246,254,255,257,251,253,258,256,267,423,428,417,416,282,287,298,300,297,364,294,293,363,314,309,308,313,316,318,383,382,334,415,338,376,375,446,355,346,448,358,404,357,350,351,349,354,356,360,359,378,493,495,2119,504,508,511,514,506,502,496,491,487,468,400,268,276,277,280,403,286,289,303,304,302,292,439,436,391,387,392,281,388,420,390,427,426,418,270,273,365,367,272,271,421,424,279,430,435,440,386,419,416,296,299,379,444,310,319,320,317,311,315,324,326,328,443,335
]
    route_map = snx.plot_route(G, solution=solution, depot_dict=depot_dict, paths=paths)
    # snx.save_route(route_map, name + "_3A")
    save_ar3(route_map, "3")

    solution = [9990000001, 738,997,1002,1954,2492,2676,2677,2618,1026,1027,1035,1041,1046,1048,2572,2354,2452,2564,2565,1158,1166,1299,1318,1308,1303,2567,2435,1345,2588,1349,2647,1311,1302,1948,1275,1266,1264,2014,2016,2019,1265,1262,2307,1274,1289,1299,1313,1307,1304,2636,1291,1287,1286,1276,2283,2529,1279,1292,2710,1234,2622,1974,1222,1243,1224,2328,1930,1172,1171,1168,2735,1163,1151,1140,1927,1928,1924,1923,1116,1113,1115,1925,1926,2234,1139,1144,1143,1150,1152,1170,2749,2563,2323,2379,2353,2351,1818,2449,1024,1025,2569,2568,2711,1951,973,945,2109,882,862,860,850,898,1830,2602,1916,950,1583,1582,2410,1593,1596,2407,1899,1608,1611,2591,1615,1616,2587,1623,1625,2575,1679,1680,1705,1701,1704,1716,1712,1714,1713,1711,1708,1715,1699,1702,1717,1732,1737,1735,1733,1721,1722,1720,1725,1731,1741,1743,1748,1751,1769,1777,1782,1783,1789,1790,1792,1791,1969,2510,1970,1895,1897,2506,2535,2517,2114,2430,2117,2432,2431,2509,2113,2115,2507,2116,2508,2518,2533,2534,2512,1973,1896,1972,1971,2511,1793,1785,1784,1775,1768,1759,1758,1760,1774,1776,1779,1767,1752,1749,1719,1724,1729,1734,1736,1718,1703,1700,2447,1690,2442,2443,1547,1543,1541,1532,1531,2469,2312,2459,2460,1504,1497,1495,2311,2302,2309,1485,83,139,143,142,1402,1434,2031,1352,2011,2013,2007,1235,1204,2006,2002,2001,2003,2004,460,2018,2021,2305,1817,1432,2754,1435,1436,2730,1398,1409,1411,1415,1419,1423,1428,1949,1950,65,66,77,79,84,80,134,76,74,71,72,78,81,85,86,112,153,158,130,102,105,198,107,109,221,217,163,209,220,211,2546,2361,2644,2740,2759,2645,2360,2358,2554,2553,2550,2548,2547,2549,2551,2552,2359,1653,2368,1794,1912,2284,2441,2440,2444,1809,1807,1806,2771,2786,2770,2784,2772,2757,2738,2746,1962,1761,1682,120,132,131,119,111,113,227,154,152,153,156,121,1681,1946,1747,132,131,119,110,228,199,150,195,194,192,98,190,188,187,189,126,99,191,193,100,200,207,201,155,91,133,1397,1405,1421,1433,1431,1450,2426,2503,2504,2383,2423,1489,1460,1456,1443,1457,1459,1466,2649,1445,2259,2502,2260,2261,2650,1488,2424,1483,1482,1473,2099,1394,1410,157,130,114,117,118,115,202,196,103,164,223,226,218,222,212,108,106,203,204,116,129,1744,1963,2747,2744,2739,2756,1884,1808,2755,1810,2781,1800,1911,1805,2785,2783,2782,2787,1898,1804,1803,1798,1799,1797,1786,1780,1772,1771,1765,1762,1763,1753,1755,1757,1764,1781,1788,1801,1802,1910,1756,1754,1738,1728,1695,1861,1693,1862,1694,1691,1676,1649,1660,2232,1644,1636,2174,1577,1576,2173,2052,2051,2169,1518,1490,1492,2167,1379,1361,1364,2163,1332,1285,1281,1284,2585,1257,1219,1182,1130,1124,1108,1110,1107,1118,2356,1111,1106,1107,974,2437,941,936,2574,907,957,948,929,2061,913,930,949,946,955,964,2151,1007,1011,2256,1037,1039,2720,2255,1064,2718,1062,1038,1028,1014,1960,1952,1005,981,2150,990,1004,923,2703,803,788
]
    route_map = snx.plot_route(G, solution=solution, depot_dict=depot_dict, paths=paths)
    # snx.save_route(route_map, name + "_4A")
    save_ar3(route_map, "4")

    solution = [9990000001, 791,900,1854,924,1000,2149,989,988,984,2148,976,972,2159,2160,2158,992,1013,1012,1016,2761,1047,2448,1819,1959,2041,2778,2253,2697,1091,1090,2237,2238,2399,2397,1096,2493,2399,2398,2376,2776,2774,2240,2243,2245,2247,2777,2040,2701,1148,2251,1149,1840,1174,1196,1197,1203,1975,2522,1193,1195,1194,1187,1186,1929,1172,2687,461,1928,1924,1956,1992,1958,1094,2729,2727,1995,1994,1993,1056,1059,1933,2607,2196,888,895,2132,2139,2204,868,2200,2194,887,2133,917,2125,926,916,2123,2420,2128,2364,2365,896,920,952,944,942,2715,954,953,2344,2346,2141,2717,969,970,975,971,1968,2142,960,968,966,2704,2154,2143,2144,2122,2202,1065,2189,2294,2524,2355,2626,2455,1074,1073,1071,1843,1070,1067,1050,1045,454,1030,1023,1022,1979,1947,1982,1034,179,167,0,135,50,51,144,52,54,57,58,61,63,180,68,70,75,69,67,180,128,87,90,161,92,95,96,184,186,127,97,181,185,162,93,94,160,88,183,75,64,60,62,206,205,149,147,59,56,55,53,165,16,5,6,8,10,17,20,21,19,18,136,15,12,14,13,145,7,8,2,4,9,11,166,171,170,168,182,177,175,174,176,169,0,17,23,54,57,58,148,205,149,147,59,125,122,124,137,140,73,125,122,123,141,138,82,1484,2308,2299,2298,2301,2310,2297,2300,2317,2313,1503,2596,2315,1534,2341,1900,1902,2751,2467,2462,1516,2458,1505,2651,2425,2422,2600,1472,2382,1471,2428,1463,1464,2599,2598,1462,2649,1446,1407,1406,1386,1385,1376,1377,1888,2647,1311,2342,1367,2446,1378,1444,2260,2381,1487,1506,2262,2461,2464,1904,1903,1535,1548,1909,2470,2472,2477,2475,1901,1496,2316,2314,2536,2537,2463,2466,1544,1546,1552,2583,1578,1592,1564,2032,1601,1602,1612,1645,2367,2370,2758,2741,2374,2646,2373,2760,2371,1654,1787,1883,1796,1795,1886,1885,2439,2372,2369,1655,2101,1604,1603,1565,1554,2544,1533,1536,1542,1545,1541,1533,1536,1544,1941,1553,2521,1554,22,165,136,15,3,1,171,182,172,173,178,1032,1031,1980,1981,1021,1051,1059,1934,1077,2456,2457,2296,2497,2191,1965,2319,1156,1160,1178,1164,1159,1165,1169,1167,1173,1185,1189,2327,2326,1177,1184,1186,1202,1236,1267,1256,1255,1249,1229,2593,2042,2045,1216,1213,1215,2185,2047,1230,1248,1254,1269,1270,2530,2660,2272,2273,2276,2641,1391,1390,2274,2275,2277,2278,2279,2639,2543,2638,1500,1499,2268,2267,1478,2048,1501,1513,1523,1985,2270,2269,2640,2264,1422,2532,1342,1339,2625,1293,1298,1272,1250,1233,1192,2248,2249,1842,1161,2246,2253,2698,2254,2244,1120,2241,1105,2242,2773,2775,1098,1095,1097,2239,2375,1104,1093,1092,1087,1063,1061,2719,1084,1081,2258,1082,2702,1060,1036,1029,2257,1008,999,995,1853,899,724
]
    route_map = snx.plot_route(G, solution=solution, depot_dict=depot_dict, paths=paths)
    # snx.save_route(route_map, name + "_5A")
    save_ar3(route_map, "5")

    # ### Save solution to AR3 format
    # distances, paths = snx.load_shortest_paths(name)
    # depot_indices = nsx_utils.load_depot_indices(G, required_edges_df)
    # snx.ar3_route(G, solution = [35, 120, 66], depot_indices=depot_indices, paths=paths)


