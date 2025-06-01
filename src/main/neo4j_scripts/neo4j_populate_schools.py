import logging
import os
import sqlite3
import uuid
from neo4j import GraphDatabase
from random import choice, randint
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Neo4jPopulator:
    def __init__(self, uri, username, password, checkpoint_db="checkpoint.db"):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.checkpoint_db = checkpoint_db
        self.setup_checkpoint_db()
        self.schools = [
            {"id": "SCH001", "name": "VIBGYOR School"},
            {"id": "SCH002", "name": "Cambridge Public School"},
            {"id": "SCH003", "name": "Euro School"}
        ]
        self.standards = [f"STD{str(i).zfill(2)}" for i in range(1, 11)]
        self.subjects = [
            {"id": "SUB001", "name": "Mathematics"},
            {"id": "SUB002", "name": "Science"},
            {"id": "SUB003", "name": "English"},
            {"id": "SUB004", "name": "Social Studies"},
            {"id": "SUB005", "name": "Hindi"}
        ]
        self.activities = [
            "Cricket", "Football", "Bharatnatyam Dance", "Kalaripayattu Martial Art",
            "Karate Martial Art", "Carnatic Music", "Guitar Classes", "Piano Classes",
            "Indian Flute Classes", "Drama", "Debates", "Science Club"
        ]

    def setup_checkpoint_db(self):
        """Initialize SQLite database for checkpointing."""
        with sqlite3.connect(self.checkpoint_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    entity_type TEXT,
                    entity_id TEXT,
                    PRIMARY KEY (entity_type, entity_id)
                )
            """)
            conn.commit()

    def is_committed(self, entity_type: str, entity_id: str) -> bool:
        """Check if an entity has been committed."""
        with sqlite3.connect(self.checkpoint_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM checkpoints WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id)
            )
            return cursor.fetchone() is not None

    def mark_committed(self, entity_type: str, entity_id: str):
        """Mark an entity as committed."""
        with sqlite3.connect(self.checkpoint_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO checkpoints (entity_type, entity_id) VALUES (?, ?)",
                (entity_type, entity_id)
            )
            conn.commit()

    def close(self):
        if self.driver is not None:
            self.driver.close()

    def create_indexes(self):
        """Create indexes to prevent duplicates."""
        try:
            with self.driver.session() as session:
                session.write_transaction(self._create_indexes)
                logger.info("Created indexes")
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
            raise

    @staticmethod
    def _create_indexes(tx):
        tx.run("CREATE INDEX school_id IF NOT EXISTS FOR (s:School) ON (s.school_id)")
        tx.run("CREATE INDEX standard_id IF NOT EXISTS FOR (std:Standard) ON (std.standard_id)")
        tx.run("CREATE INDEX student_id IF NOT EXISTS FOR (stu:Student) ON (stu.student_id)")
        tx.run("CREATE INDEX parent_id IF NOT EXISTS FOR (p:Parent) ON (p.parent_id)")
        tx.run("CREATE INDEX subject_id IF NOT EXISTS FOR (sub:Subject) ON (sub.subject_id)")
        tx.run("CREATE INDEX activity_id IF NOT EXISTS FOR (act:Activity) ON (act.activity_id)")

    def populate_database(self):
        try:
            # Create indexes first
            self.create_indexes()
            # Create schools
            for school in self.schools:
                if not self.is_committed("School", school["id"]):
                    with self.driver.session() as session:
                        session.write_transaction(self._create_school, school)
                        self.mark_committed("School", school["id"])
                        logger.info(f"Created school {school['name']}")

            # Create standards, students, subjects, parents, activities
            for school in self.schools:
                for std_id in self.standards:
                    std_key = f"{school['id']}_{std_id}"
                    if not self.is_committed("Standard", std_key):
                        with self.driver.session() as session:
                            session.write_transaction(self._create_standard, school["id"], std_id)
                            self.mark_committed("Standard", std_key)
                            logger.info(f"Created standard {std_id} for {school['name']}")

                    # Create subjects
                    for subject in self.subjects:
                        if not self.is_committed("Subject", subject["id"]):
                            with self.driver.session() as session:
                                session.write_transaction(self._create_subject, subject)
                                self.mark_committed("Subject", subject["id"])
                                logger.info(f"Created subject {subject['name']}")

                    # Create activities
                    for activity in self.activities:
                        act_id = f"ACT{str(uuid.uuid4())[:8]}"
                        if not self.is_committed("Activity", act_id):
                            with self.driver.session() as session:
                                session.write_transaction(self._create_activity, act_id, activity)
                                self.mark_committed("Activity", act_id)
                                logger.info(f"Created activity {activity}")

                    # Create students and related data
                    for i in range(1, 11):  # 10 students per standard
                        student_id = f"STU{school['id'][-3:]}{std_id[-2:]}{str(i).zfill(2)}"
                        if not self.is_committed("Student", student_id):
                            with self.driver.session() as session:
                                session.write_transaction(
                                    self._create_student_and_related,
                                    school["id"], std_id, student_id, i
                                )
                                self.mark_committed("Student", student_id)
                                logger.info(f"Created student {student_id}")

        except Exception as e:
            logger.error(f"Error populating database: {str(e)}")
            raise

    @staticmethod
    def _create_school(tx, school: Dict):
        query = """
        MATCH (s:School {school_id: $school_id})
        WITH s, count(s) AS cnt
        WHERE cnt = 0
        CREATE (s:School {school_id: $school_id, name: $name})
        """
        tx.run(query, school_id=school["id"], name=school["name"])

    @staticmethod
    def _create_standard(tx, school_id: str, std_id: str):
        query = """
        MATCH (s:School {school_id: $school_id})
        MATCH (std:Standard {standard_id: $std_id, school_id: $school_id})
        WITH s, std, count(std) AS cnt
        WHERE cnt = 0
        CREATE (std:Standard {standard_id: $std_id, school_id: $school_id, name: $name})
        CREATE (std)-[:BELONGS_TO]->(s)
        """
        tx.run(query, school_id=school_id, std_id=std_id, name=f"Standard {std_id[-2:]}")

    @staticmethod
    def _create_subject(tx, subject: Dict):
        query = """
        MATCH (sub:Subject {subject_id: $subject_id})
        WITH sub, count(sub) AS cnt
        WHERE cnt = 0
        CREATE (sub:Subject {subject_id: $subject_id, name: $name})
        """
        tx.run(query, subject_id=subject["id"], name=subject["name"])

    @staticmethod
    def _create_activity(tx, act_id: str, activity: str):
        query = """
        MATCH (act:Activity {activity_id: $act_id})
        WITH act, count(act) AS cnt
        WHERE cnt = 0
        CREATE (act:Activity {activity_id: $act_id, name: $name})
        """
        tx.run(query, act_id=act_id, name=activity)

    @staticmethod
    def _create_student_and_related(tx, school_id: str, std_id: str, student_id: str, index: int):
        # Generate data
        name = f"Student {index} {std_id[-2:]} {school_id[-3:]}"
        scores = {sub["name"]: randint(60, 95) for sub in [
            {"name": "Mathematics"}, {"name": "Science"}, {"name": "English"},
            {"name": "Social Studies"}, {"name": "Hindi"}
        ]}
        attendance = randint(85, 95)
        remarks = f"Good performance in {choice(['Math', 'Science', 'English'])}"
        mother_id = f"PAR{student_id}M"
        father_id = f"PAR{student_id}F"
        has_activity = randint(0, 1) == 1  # 50% chance
        activity_id = f"ACT{str(uuid.uuid4())[:8]}" if has_activity else None

        query = """
        MATCH (std:Standard {standard_id: $std_id, school_id: $school_id})
        MATCH (stu:Student {student_id: $student_id})
        WITH std, stu, count(stu) AS stu_cnt
        WHERE stu_cnt = 0
        CREATE (stu:Student {
            student_id: $student_id,
            name: $name,
            academic_scores: $scores,
            attendance: $attendance,
            remarks: $remarks
        })
        CREATE (stu)-[:ENROLLED_IN]->(std)
        WITH stu
        MATCH (m:Parent {parent_id: $mother_id}), (f:Parent {parent_id: $father_id})
        WITH stu, m, f, count(m) AS m_cnt, count(f) AS f_cnt
        WHERE m_cnt = 0 AND f_cnt = 0
        CREATE (m:Parent {parent_id: $mother_id, name: $mother_name, role: 'Mother'})
        CREATE (f:Parent {parent_id: $father_id, name: $father_name, role: 'Father'})
        CREATE (m)-[:PARENT_OF]->(stu)
        CREATE (f)-[:PARENT_OF]->(stu)
        WITH stu
        MATCH (sub:Subject)
        WHERE sub.subject_id IN $subject_ids
        CREATE (stu)-[:STUDIES {score: $scores[sub.name]}]->(sub)
        """
        params = {
            "school_id": school_id,
            "std_id": std_id,
            "student_id": student_id,
            "name": name,
            "scores": scores,
            "attendance": attendance,
            "remarks": remarks,
            "mother_id": mother_id,
            "mother_name": f"Mrs. {name} Mother",
            "father_id": father_id,
            "father_name": f"Mr. {name} Father",
            "subject_ids": [sub["id"] for sub in [
                {"id": "SUB001", "name": "Mathematics"},
                {"id": "SUB002", "name": "Science"},
                {"id": "SUB003", "name": "English"},
                {"id": "SUB004", "name": "Social Studies"},
                {"id": "SUB005", "name": "Hindi"}
            ]]
        }
        tx.run(query, **params)

        if has_activity:
            # Create activity relationship in the same transaction
            act_query = """
            MATCH (stu:Student {student_id: $student_id})
            MATCH (act:Activity)
            WHERE act.name = $activity_name
            WITH stu, act, count(*) AS act_cnt
            WHERE act_cnt > 0
            MERGE (stu)-[:PARTICIPATES_IN]->(act)
            """
            tx.run(act_query, student_id=student_id, activity_name=choice([
                "Cricket", "Football", "Bharatnatyam Dance", "Kalaripayattu Martial Art",
                "Karate Martial Art", "Carnatic Music", "Guitar Classes", "Piano Classes",
                "Indian Flute Classes", "Drama", "Debates", "Science Club"
            ]))

def main():
    NEO4J_URI = os.getenv("NEO4J_URI")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

    populator = Neo4jPopulator(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    try:
        populator.populate_database()
    finally:
        populator.close()

if __name__ == "__main__":
    main()