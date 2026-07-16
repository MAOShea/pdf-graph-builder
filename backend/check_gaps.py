import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
d = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
)
db = os.getenv("NEO4J_DATABASE", "morkborg")
with d.session(database=db) as s:
    for name in [
        "CorpsePlunderTable", "NameTable", "TrapsTable", "WeatherTable",
        "OccultTreasuresTable", "WeaponTable", "ArmorTable",
        "BasilisksDemandTable", "ArcaneCatastrophesTable", "AdventureSparkTable",
        "WanderTable", "DwellsHereTable", "ImminentDangerTable",
        "DistinctiveFeatureTable",
    ]:
        r = s.run(
            "MATCH (t:IngestNode {name: $n})-[:HAS_ENTRY]->(row) RETURN count(row) AS c",
            {"n": name},
        ).single()
        print(f"{name}: {r['c'] if r else 0}")
    print("RulePassage:", s.run("MATCH (n:RulePassage) RETURN count(n) AS c").single()["c"])
    print("DR APPLIES_TO:", s.run(
        "MATCH (t:DRTable)-[:APPLIES_TO]->(x) RETURN labels(x), x.name"
    ).data())
d.close()
