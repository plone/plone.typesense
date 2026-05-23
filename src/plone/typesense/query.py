from plone.typesense.filters import TypesenseFilterBuilder
from plone.typesense.indexes import getIndex
from plone.typesense.indexes import TZCTextIndex, TDateIndex, TExtendedPathIndex
from plone.typesense.indexes import TDateRangeIndex, TBooleanIndex
from plone.typesense.interfaces import IQueryAssembler
from plone.typesense.utils import get_ts_only_indexes
from plone.typesense import log
from DateTime import DateTime
from zope.interface import implementer


@implementer(IQueryAssembler)
class TypesenseQueryAssembler:
    def __init__(self, request, manager):
        self.catalog = manager.catalog
        self.request = request

    def normalize(self, query):
        """Extract and convert sort params, remove pagination params.

        Returns (cleaned_query, sort_by_string).
        """
        sort_by_parts = []
        sort = query.pop("sort_on", None)
        sort_order = query.pop("sort_order", "asc")
        if sort_order in ("descending", "reverse", "desc"):
            sort_order = "desc"
        else:
            sort_order = "asc"

        if sort:
            for sort_str in sort.split(","):
                sort_by_parts.append(f"{sort_str.strip()}:{sort_order}")

        # Always add text match relevance as tiebreaker
        sort_by_parts.append("_text_match:desc")

        sort_by = ",".join(sort_by_parts)

        # Remove pagination params
        for key in ("b_size", "b_start", "sort_limit"):
            query.pop(key, None)

        return query, sort_by

    def __call__(self, dquery):
        """Assemble a Typesense search params dict from Plone catalog query."""
        fb = TypesenseFilterBuilder()
        q_parts = []
        query_by_fields = []

        catalog = self.catalog._catalog
        idxs = set(catalog.indexes.keys()) if hasattr(catalog.indexes, 'keys') else set(catalog.indexes)
        ts_only_indexes = get_ts_only_indexes()

        for key, value in dquery.items():
            if key not in idxs and key not in ts_only_indexes:
                continue

            index = getIndex(catalog, key)

            # ZCTextIndex or ts-only text index → contribute to q and query_by
            if isinstance(index, TZCTextIndex) or (index is None and key in ts_only_indexes):
                text = self._extract_text(value)
                if text:
                    q_parts.append(text)
                    query_by_fields.append(key)
                continue

            if index is None:
                continue

            # DateIndex → range filter
            if isinstance(index, TDateIndex):
                self._add_date_filter(fb, key, value)
                continue

            # DateRangeIndex → range filter pair
            if isinstance(index, TDateRangeIndex):
                self._add_date_range_filter(fb, key, value)
                continue

            # ExtendedPathIndex → path filter
            if isinstance(index, TExtendedPathIndex):
                self._add_path_filter(fb, key, value)
                continue

            # BooleanIndex
            if isinstance(index, TBooleanIndex):
                bool_val = value
                if isinstance(bool_val, dict):
                    bool_val = bool_val.get("query", bool_val)
                fb.equals(key, bool(bool_val))
                continue

            # FieldIndex, KeywordIndex, UUIDIndex, etc. → equality filter
            self._add_equality_filter(fb, key, value)

        # Build final params
        params = {}

        if q_parts:
            params["q"] = " ".join(q_parts)
        else:
            params["q"] = "*"

        if query_by_fields:
            params["query_by"] = ",".join(query_by_fields)

        filter_str = fb.build()
        if filter_str:
            params["filter_by"] = filter_str

        return params

    def _extract_text(self, value):
        """Extract search text from a query value."""
        if isinstance(value, dict):
            value = value.get("query", "")
        if isinstance(value, (list, tuple)):
            value = " ".join(str(v) for v in value)
        text = str(value).strip().strip("*")
        return text if text else None

    def _add_equality_filter(self, fb, key, value):
        """Add an equality filter for FieldIndex/KeywordIndex/etc."""
        if isinstance(value, dict):
            query_val = value.get("query", value)
            operator = value.get("operator", "or")
            not_val = value.get("not", False)
            if isinstance(query_val, (list, tuple, set)):
                if not_val:
                    fb.not_equals(key, list(query_val))
                else:
                    fb.equals(key, list(query_val))
            else:
                if not_val:
                    fb.not_equals(key, query_val)
                else:
                    fb.equals(key, query_val)
        elif isinstance(value, (list, tuple, set)):
            fb.equals(key, list(value))
        else:
            fb.equals(key, value)

    def _add_date_filter(self, fb, key, value):
        """Add a date filter for DateIndex."""
        if isinstance(value, dict):
            range_ = value.get("range")
            query = value.get("query")
            if query is None:
                return
            if isinstance(query, (list, tuple)):
                if range_ is None:
                    range_ = "min"
                if range_ in ("min:max", "minmax") and len(query) == 2:
                    ts1 = self._to_timestamp(query[0])
                    ts2 = self._to_timestamp(query[1])
                    fb.range(key, ts1, ts2)
                    return
                query = query[0]
            ts = self._to_timestamp(query)
            if range_ == "min":
                fb.greater_equal(key, ts)
            elif range_ == "max":
                fb.less_equal(key, ts)
            else:
                fb.equals(key, ts)
        else:
            ts = self._to_timestamp(value)
            fb.equals(key, ts)

    def _add_date_range_filter(self, fb, key, value):
        """Add filter for DateRangeIndex (effectiveRange)."""
        if isinstance(value, dict):
            value = value.get("query", value)
        ts = self._to_timestamp(value)
        fb.less_equal(f"{key}1", ts)
        fb.greater_equal(f"{key}2", ts)

    def _add_path_filter(self, fb, key, value):
        """Add path filter for ExtendedPathIndex."""
        if isinstance(value, str):
            path = value
        elif isinstance(value, dict):
            path = value.get("query", "")
            if isinstance(path, (list, tuple)):
                path = path[0] if path else ""
        elif isinstance(value, (list, tuple)):
            path = value[0] if value else ""
        else:
            return
        if path:
            fb.equals(key, path)

    def _to_timestamp(self, value):
        """Convert a date value to a Unix timestamp integer."""
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, DateTime):
            return int(value.utcdatetime().strftime("%s"))
        if isinstance(value, str):
            try:
                return int(DateTime(value).utcdatetime().strftime("%s"))
            except Exception:
                return 0
        if hasattr(value, "strftime"):
            return int(value.strftime("%s"))
        return 0


# Keep the old name as alias for backward compatibility
QueryAssembler = TypesenseQueryAssembler
