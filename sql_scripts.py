setup_script = """
CREATE TABLE WORKOUT (
    WORKOUT_ID TEXT PRIMARY KEY,
    WORKOUT_START_TIME TEXT,
    WORKOUT_DURATION TEXT,
    WORKOUT_NAME TEXT,
    WORKOUT_NOTES TEXT
);

CREATE TABLE EXERCISE (
    EXERCISE_ID TEXT PRIMARY KEY,
    EXERCISE_NAME TEXT
);

CREATE TABLE WORKOUT_EXERCISE (
    WORKOUT_EXERCISE_ID TEXT,
    WORKOUT_ID TEXT,
    EXERCISE_ID TEXT,
    FOREIGN KEY(WORKOUT_ID) REFERENCES WORKOUT(WORKOUT_ID),
    FOREIGN KEY(EXERCISE_ID) REFERENCES EXERCISE(EXERCISE_ID)
);

CREATE TABLE EXERCISE_SET (
    SET_ID TEXT PRIMARY KEY,
    WORKOUT_EXERCISE_ID TEXT,
    SET_ORDER INTEGER,
    WEIGHT REAL,
    WEIGHT_UNIT TEXT,
    REPS REAL,
    RPE REAL,
    DISTANCE REAL,
    DISTANCE_UNIT TEXT,
    SECONDS REAL,
    NOTES TEXT,
    FOREIGN KEY(WORKOUT_EXERCISE_ID) REFERENCES WORKOUT_EXERCISE(WORKOUT_EXERCISE_ID)
);
"""

create_indexes = """
    CREATE INDEX idx_ex_id on WORKOUT_EXERCISE(EXERCISE_ID);
    CREATE INDEX idx_workout_id ON WORKOUT_EXERCISE(WORKOUT_ID);
    CREATE INDEX idx_ex_workout_id ON EXERCISE_SET(WORKOUT_EXERCISE_ID);
"""


create_rep_maxes_view = """
CREATE VIEW REP_MAXES AS 
SELECT c.EXERCISE_NAME, CAST(a.reps as int) as  REP_MAX, MAX(a.WEIGHT) AS WEIGHT  FROM EXERCISE_SET a
	join WORKOUT_EXERCISE b on b.WORKOUT_EXERCISE_ID = a. WORKOUT_EXERCISE_ID
   JOIN EXERCISE c ON c.EXERCISE_ID = b.EXERCISE_ID
where a.reps is not null
group by c.EXERCISE_NAME,a.reps
order by c.EXERCISE_NAME,a.reps
"""