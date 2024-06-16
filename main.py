import csv
import datetime
import dataclasses
import time
import sqlite3
import random
import string
from sql_scripts import setup_script, create_indexes, create_rep_maxes_view
import argparse


parser = argparse.ArgumentParser(
    prog="strong-csv-to-sqlite",
    description="Converts an exported strong csv to a sqlite database",
    epilog="EXAMPLE: strong-csv-to-sqlite strong.csv strong.db",
)

parser.add_argument("input_csv")
parser.add_argument("output_db")


alphabet = string.ascii_lowercase + string.digits + string.ascii_uppercase


def random_choice():
    return "".join(random.choices(alphabet, k=8))


@dataclasses.dataclass
class DenormedRow:
    date: datetime.datetime
    workout_name: str
    exercise_name: str
    set_order: int
    weight: float | None
    weight_unit: str | None
    reps: float | None
    rpe: float | None
    distance: float | None
    distance_unit: str | None
    seconds: float | None
    notes: str | None
    workout_notes: str | None
    workout_duration: str | None


class ExerciseSet:
    set_id: str
    workout_exercise_id: str
    set_order: int
    weight: float | None = None
    weight_unit: str | None = None
    reps: float | None = None
    rpe: float | None = None
    distance: float | None = None
    distance_unit: str | None = None
    seconds: float | None = None
    notes: str | None = None

    def to_insert_tuple(self):
        return (
            str(self.set_id),
            str(self.workout_exercise_id),
            self.set_order,
            self.weight,
            self.weight_unit,
            self.reps,
            self.rpe,
            self.distance,
            self.distance_unit,
            self.seconds,
            self.notes,
        )

    def __init__(self, row: DenormedRow, workout_exercise_id: str):
        self.set_id = random_choice()
        self.workout_exercise_id = workout_exercise_id
        self.set_order = row.set_order
        self.weight = row.weight
        self.weight_unit = row.weight_unit
        self.reps = row.reps
        self.rpe = row.rpe
        self.distance = row.distance
        self.distance_unit = row.distance_unit
        self.seconds = row.seconds
        self.notes = row.notes


EXERCISE_IDS: dict[str, str] = {}


def get_exercise_id(exercise_name: str) -> str:
    if EXERCISE_IDS.get(exercise_name):
        return EXERCISE_IDS[exercise_name]
    else:
        EXERCISE_IDS[exercise_name] = random_choice()
        return EXERCISE_IDS[exercise_name]


class WorkoutExercise:
    workout_id: str
    workout_exercise_id: str
    exercise_id: str
    exercise_sets: list[ExerciseSet]

    def to_insert_tuple(self):
        return (
            str(self.workout_exercise_id),
            str(self.workout_id),
            str(self.exercise_id),
        )

    def __init__(
        self,
        exercise_name: str,
        workout_id: str,
        denormed_rows: list[DenormedRow],
    ):
        self.exercise_sets = []
        self.workout_exercise_id = random_choice()
        self.workout_id = workout_id
        self.exercise_id = get_exercise_id(exercise_name)
        for row in denormed_rows:
            ex_set = ExerciseSet(row=row, workout_exercise_id=self.workout_exercise_id)
            self.exercise_sets.append(ex_set)


class Workout:
    workout_id: str
    start_time: datetime.datetime
    duration: str | None = None
    name: str | None = None
    notes: str | None = None
    exercises: list[WorkoutExercise]

    def to_insert_tuple(self):
        return (
            str(self.workout_id),
            str(self.start_time),
            self.duration,
            self.name,
            self.notes,
        )

    def __init__(self, denormed_rows: list[DenormedRow]):
        self.workout_id = random_choice()
        denormed_indexed_by_exercises: dict[str, list[DenormedRow]] = {}
        self.exercises = []
        for row in denormed_rows:
            if denormed_indexed_by_exercises.get(row.exercise_name):
                denormed_indexed_by_exercises[row.exercise_name].append(row)
            else:
                denormed_indexed_by_exercises[row.exercise_name] = [row]
            self.start_time = row.date
            if row.workout_duration:
                self.duration = row.workout_duration
            if row.workout_name:
                self.name = row.workout_name
            if row.workout_notes:
                self.notes = row.workout_notes
        for key, value in denormed_indexed_by_exercises.items():
            exercise = WorkoutExercise(
                exercise_name=key, denormed_rows=value, workout_id=self.workout_id
            )
            self.exercises.append(exercise)


# def denormed_row_list_to_workout(denormed_rows_id_by_datetime:list[DenormedRow]):


def parse_float_or_none(maybe_float) -> float | None:
    if maybe_float:
        try:
            return float(maybe_float)
        except Exception as e:
            return None
    else:
        return None


def parse_int_or_none(maybe_int) -> int | None:
    if maybe_int:
        try:
            return int(maybe_int)
        except Exception as e:
            return None
    else:
        return None


def parse_datetime_or_none(maybe_date) -> datetime.datetime | None:
    if maybe_date:
        try:
            return datetime.datetime.fromisoformat(maybe_date)
        except Exception as e:
            return None
    else:
        return None


def parse_to_denormed(raw_row: dict) -> DenormedRow:
    date = parse_datetime_or_none(raw_row.get("Date"))
    workout_name = raw_row.get("Workout Name")
    exercise_name = raw_row.get("Exercise Name")
    set_order = parse_int_or_none(raw_row.get("Set Order"))
    weight = parse_float_or_none(raw_row.get("Weight"))
    weight_unit = raw_row.get("Weight Unit")
    reps = parse_float_or_none(raw_row.get("Reps"))
    rpe = parse_float_or_none(raw_row.get("RPE"))
    distance = parse_float_or_none(raw_row.get("Distance"))
    distance_unit = raw_row.get("Distance Unit")
    seconds = parse_float_or_none(raw_row.get("Seconds"))
    notes = raw_row.get("Notes")
    workout_notes = raw_row.get("Workout Notes")
    workout_duration = raw_row.get("Workout Duration")
    return DenormedRow(
        date=date,
        workout_name=workout_name,
        exercise_name=exercise_name,
        set_order=set_order,
        weight=weight,
        weight_unit=weight_unit,
        reps=reps,
        rpe=rpe,
        distance=distance,
        distance_unit=distance_unit,
        seconds=seconds,
        notes=notes,
        workout_notes=workout_notes,
        workout_duration=workout_duration,
    )


def main():
    args = parser.parse_args()
    workouts: list[Workout] = []
    with open(args.input_csv) as handle:
        reader = csv.DictReader(handle, delimiter=";")
        denormed_rows = [parse_to_denormed(raw_row) for raw_row in reader]
        # (time.mktime(date_time.timetuple())))
        denormed_indexed_by_datetimes: dict[float, list[DenormedRow]] = {}
        for denormed_row in denormed_rows:
            key = time.mktime(denormed_row.date.timetuple())
            if denormed_indexed_by_datetimes.get(key):
                denormed_indexed_by_datetimes[key].append(denormed_row)
            else:
                denormed_indexed_by_datetimes[key] = [denormed_row]
        for key, value in denormed_indexed_by_datetimes.items():
            if value:
                workout = Workout(value)
                workouts.append(workout)

    conn = sqlite3.connect(args.output_db)
    statements = setup_script.split(";")
    for stm in statements:
        conn.execute(stm)
    ex_inserts: list[tuple[str, str]] = []

    for exercise_name, exercise_id in EXERCISE_IDS.items():
        ex_inserts.append((str(exercise_id), exercise_name))
    conn.executemany("INSERT INTO EXERCISE VALUES(?,?)", ex_inserts)

    workout_tuples: list[tuple] = []
    workout_ex_tuples: list[tuple] = []
    ex_tuples: list[tuple] = []
    for workout in workouts:
        workout_tuples.append(workout.to_insert_tuple())
        for workout_ex in workout.exercises:
            workout_ex_tuples.append(workout_ex.to_insert_tuple())
            for ex in workout_ex.exercise_sets:
                ex_tuples.append(ex.to_insert_tuple())

    conn.executemany(
        "INSERT INTO WORKOUT VALUES(?,?,?,?,?)",
        workout_tuples,
    )
    conn.executemany("INSERT INTO WORKOUT_EXERCISE VALUES(?,?,?)", workout_ex_tuples)
    conn.executemany(
        "INSERT INTO EXERCISE_SET VALUES(?,?,?,?,?,?,?,?,?,?,?)", ex_tuples
    )
    for stm in create_indexes.split(";"):
        conn.execute(stm)
    conn.execute(create_rep_maxes_view)
    conn.commit()


main()
