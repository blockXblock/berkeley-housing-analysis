Q='[out:json][timeout:120];
area["name"="Berkeley"]["boundary"="administrative"]["admin_level"="8"]->.a;
(
 node(area.a)["power"="pole"];
 node(area.a)["power"="tower"];
 node(area.a)["power"="transformer"];
 node(area.a)["transformer"];
 node(area.a)["power"="substation"];
 way(area.a)["power"="substation"];
 node(area.a)["highway"="street_lamp"];
 way(area.a)["power"="line"];
 way(area.a)["power"="minor_line"];
);
out tags;'
curl -s --max-time 180 -d "data=$Q" https://overpass-api.de/api/interpreter
