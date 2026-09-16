import sqlite3
import os
from laboratorio.config import DATABASE_PATH, DRAW_NUMBERS


class DatabaseManager:
    def __init__(self, db_path=DATABASE_PATH, draw_n=DRAW_NUMBERS):
        self.db_path = db_path
        self.draw_n = draw_n
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._initialize_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _col_names(self):
        bolas = [f"bola{i}" for i in range(1, self.draw_n + 1)]
        dezenas = [f"dezena{i}" for i in range(1, self.draw_n + 1)]
        return bolas + dezenas

    def _initialize_db(self):
        cols = ", ".join(f"{c} INTEGER" for c in self._col_names())
        with self._get_connection() as conn:
            conn.execute(f'''
                CREATE TABLE IF NOT EXISTS resultados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concurso INTEGER UNIQUE,
                    data TEXT,
                    {cols}
                )
            ''')
            conn.commit()

    def insert_result(self, result_data):
        cols = ["concurso", "data"] + self._col_names()
        placeholders = ", ".join(["?"] * len(cols))
        bolas = list(result_data["bolas"])
        dezenas = list(result_data["dezenas"])
        if len(bolas) < self.draw_n:
            bolas += [None] * (self.draw_n - len(bolas))
        if len(dezenas) < self.draw_n:
            dezenas += [None] * (self.draw_n - len(dezenas))
        params = [result_data["concurso"], result_data["data"], *bolas[:self.draw_n], *dezenas[:self.draw_n]]
        with self._get_connection() as conn:
            conn.execute(
                f"INSERT OR IGNORE INTO resultados ({', '.join(cols)}) VALUES ({placeholders})",
                params,
            )
            conn.commit()

    def get_all_results(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM resultados ORDER BY concurso ASC").fetchall()
            return [dict(row) for row in rows]
