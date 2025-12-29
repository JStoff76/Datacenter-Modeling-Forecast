import csv
from pathlib import Path
from typing import Any, Dict, List, Optional


class Series:
    def __init__(self, data: Dict[Any, Any]):
        self.data = data

    def isnull(self):
        return Series({k: v is None for k, v in self.data.items()})

    def notnull(self):
        return Series({k: v is not None for k, v in self.data.items()})

    def sum(self):
        return sum(v for v in self.data.values() if isinstance(v, (int, float, bool)))

    def min(self):
        numeric = [v for v in self.data.values() if isinstance(v, (int, float))]
        return min(numeric) if numeric else None

    def max(self):
        numeric = [v for v in self.data.values() if isinstance(v, (int, float))]
        return max(numeric) if numeric else None

    def any(self):
        return any(self.data.values())

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __iter__(self):
        return iter(self.data.values())

    def __getitem__(self, key):
        return self.data[key]

    def __len__(self):
        return len(self.data)

    def __eq__(self, other):
        return Series({k: v == other for k, v in self.data.items()})

    def __and__(self, other):
        keys = set(self.data.keys()) | set(other.data.keys())
        return Series({k: bool(self.data.get(k)) and bool(other.data.get(k)) for k in keys})


class LocAccessor:
    def __init__(self, df: "DataFrame"):
        self.df = df

    def __getitem__(self, key):
        if self.df.index_map is None:
            raise KeyError("DataFrame has no index")
        if key not in self.df.index_map:
            raise KeyError(key)
        return self.df.index_map[key]


class IlocAccessor:
    def __init__(self, df: "DataFrame"):
        self.df = df

    def __getitem__(self, idx):
        return Series(self.df.data[idx])


class DataFrame:
    def __init__(self, data: Optional[List[Dict[str, Any]]] = None, columns: Optional[List[str]] = None):
        self.data = data or []
        if columns:
            self.columns = list(columns)
        elif self.data:
            all_keys = set()
            for row in self.data:
                all_keys.update(row.keys())
            self.columns = list(all_keys)
        else:
            self.columns = []
        self.index_map = None

    @property
    def empty(self) -> bool:
        return len(self.data) == 0

    @property
    def index(self):
        if self.index_map is not None:
            return list(self.index_map.keys())
        return list(range(len(self.data)))

    def __len__(self):
        return len(self.data)

    def copy(self):
        return DataFrame([row.copy() for row in self.data], columns=self.columns.copy())

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key):
        if isinstance(key, str):
            return Series({i: row.get(key) for i, row in enumerate(self.data)})
        elif isinstance(key, list):
            return DataFrame([{k: row.get(k) for k in key} for row in self.data])
        elif isinstance(key, Series):
            filtered = []
            for idx, row in enumerate(self.data):
                if key.data.get(idx):
                    filtered.append(row)
            return DataFrame(filtered)
        else:
            raise KeyError(key)

    def __setitem__(self, key: str, value: Any):
        if isinstance(value, (list, tuple)):
            for row, v in zip(self.data, value):
                row[key] = v
        else:
            if not self.data:
                self.data.append({key: value})
            else:
                for row in self.data:
                    row[key] = value
        if key not in self.columns:
            self.columns.append(key)

    def iterrows(self):
        for idx, row in enumerate(self.data):
            yield idx, Series(row)

    def groupby(self, by: str, dropna: bool = True):
        return GroupBy(self, by)

    def reset_index(self, name: Optional[str] = None):
        return self

    def rename(self, columns: Dict[str, str]):
        new_data = []
        for row in self.data:
            new_row = {}
            for k, v in row.items():
                new_key = columns.get(k, k)
                new_row[new_key] = v
            new_data.append(new_row)
        return DataFrame(new_data)

    def sort_values(self, by: List[str], ascending: List[bool]):
        df = self.copy()
        for col, asc in reversed(list(zip(by, ascending))):
            df.data.sort(key=lambda r: r.get(col), reverse=not asc)
        return df

    def to_csv(self, path, index: bool = False):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as f:
            if not self.data:
                return
            writer = csv.DictWriter(f, fieldnames=self.columns)
            writer.writeheader()
            for row in self.data:
                writer.writerow({col: row.get(col, "") for col in self.columns})

    def to_excel(self, writer, index: bool = False, sheet_name: str = "Sheet1"):
        writer._write_sheet(sheet_name, self, index=index)

    def set_index(self, column: str):
        index_map = {}
        for row in self.data:
            index_map[row.get(column)] = row
        df = self.copy()
        df.index_map = index_map
        return df

    @property
    def loc(self):
        return LocAccessor(self)

    @property
    def iloc(self):
        return IlocAccessor(self)


class GroupBy:
    def __init__(self, df: DataFrame, by: str):
        self.df = df
        self.by = by

    def __iter__(self):
        groups: Dict[Any, List[Dict[str, Any]]] = {}
        for row in self.df.data:
            key = row.get(self.by)
            groups.setdefault(key, []).append(row)
        for key, rows in groups.items():
            yield key, DataFrame(rows)

    def size(self):
        counts = {}
        for row in self.df.data:
            key = row.get(self.by)
            counts[key] = counts.get(key, 0) + 1
        data = [{self.by: k, "size": v} for k, v in counts.items()]
        return DataFrame(data)


class ExcelWriter:
    def __init__(self, path):
        self.path = Path(path)
        self.sheets: Dict[str, DataFrame] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.save()

    def _write_sheet(self, name: str, df: DataFrame, index: bool = False):
        self.sheets[name] = df

    def save(self):
        base = self.path
        base.parent.mkdir(parents=True, exist_ok=True)
        with base.open("w") as f:
            for name, df in self.sheets.items():
                f.write(f"# Sheet: {name}\n")
                if df.data:
                    writer = csv.DictWriter(f, fieldnames=df.columns)
                    writer.writeheader()
                    for row in df.data:
                        writer.writerow({col: row.get(col, "") for col in df.columns})
                f.write("\n")


def concat(dfs: List[DataFrame], ignore_index: bool = False):
    data = []
    for df in dfs:
        data.extend(df.data)
    return DataFrame(data)


def read_csv(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]
    return DataFrame(data, columns=reader.fieldnames)


def read_excel(path):
    return read_csv(path)


class TimestampClass:
    @staticmethod
    def utcnow():
        from datetime import datetime

        return datetime.utcnow()

    @staticmethod
    def now():
        from datetime import datetime

        return datetime.now()

    @staticmethod
    def isoformat():
        return TimestampClass.utcnow().isoformat()


Timestamp = TimestampClass
