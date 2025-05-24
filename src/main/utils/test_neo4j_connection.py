from neo4j import GraphDatabase
driver = GraphDatabase.driver("neo4j+s://6a91c5ff.databases.neo4j.io",
                              auth=("neo4j", "xzSlajLW5_ThyHtqZvpI_WLlniax_WlkznE3s6dizdg"))
def test_query(tx):
    result = tx.run("RETURN 'Connected!' AS message")
    return result.single()[0]
with driver.session() as session:
    print(session.execute_write(test_query))
driver.close()