from datetime import date, datetime
import time
from Acquisition import aq_base, aq_parent
from DateTime import DateTime
from Missing import MV
from plone.folder.nogopip import GopipIndex
from Products.ExtendedPathIndex.ExtendedPathIndex import ExtendedPathIndex
from Products.PluginIndexes.BooleanIndex.BooleanIndex import BooleanIndex
from Products.PluginIndexes.DateIndex.DateIndex import DateIndex
from Products.PluginIndexes.DateRangeIndex.DateRangeIndex import DateRangeIndex
from Products.PluginIndexes.FieldIndex.FieldIndex import FieldIndex
from Products.PluginIndexes.KeywordIndex.KeywordIndex import KeywordIndex
from Products.PluginIndexes.util import safe_callable
from Products.PluginIndexes.UUIDIndex.UUIDIndex import UUIDIndex
from Products.ZCTextIndex.ZCTextIndex import ZCTextIndex

from plone.typesense import log


def _one(val):
    """
    if list, return first
    otherwise, return value
    """
    if isinstance(val, (list, set, tuple)):
        return val[0]
    return val


def _zdt(val):
    if isinstance(val, datetime):
        val = DateTime(val)
    elif isinstance(val, date):
        val = DateTime(datetime.fromordinal(val.toordinal()))
    elif isinstance(val, str):
        val = DateTime(val)
    return val


def get_index(catalog, name):
    catalog = getattr(catalog, "_catalog", catalog)
    try:
        index = aq_base(catalog.getIndex(name))
    except KeyError:
        return None
    index_type = type(index)
    if index_type in INDEX_MAPPING:
        return INDEX_MAPPING[index_type](catalog, index)
    return None


class BaseIndex:
    filter_query = True

    def __init__(self, catalog, index):
        self.catalog = catalog
        self.index = index

    def get_value(self, obj):
        value = None
        attrs = self.index.getIndexSourceNames()
        if len(attrs) > 0:
            attr = attrs[0]
        else:
            attr = ""
        if hasattr(self.index, "index_object"):
            value = self.index._get_object_datum(obj, attr)
        else:
            log.info(f"catalogObject was passed bad index object {self.index}.")
        if value == MV:
            return None
        if isinstance(value, list) and len(value) == 0:
            return None
        return value


class TKeywordIndex(BaseIndex):
    def extract(self, name, data):
        return data[name] or []


class TFieldIndex(BaseIndex):
    pass


class TDateIndex(BaseIndex):
    """
    """

    missing_date = DateTime("1900/01/01")

    def create_mapping(self, name):
        return {"type": "date", "store": True}

    def get_value(self, obj):
        value = super().get_value(obj)
        if isinstance(value, list):
            if len(value) == 0:
                value = None
            else:
                value = value[0]
        if value in ("None", MV, None, ""):
            value = self.missing_date
        if isinstance(value, str):
            value = DateTime(value)
            utcvalue = value.utcdatetime()
            return int(utcvalue.strftime("%s"))
        if isinstance(value, DateTime):
            utcvalue = value.utcdatetime()
            return int(utcvalue.strftime("%s"))
        return value

    def get_query(self, name, value):
        range_ = value.get("range")
        query = value.get("query")
        if query is None:
            return None
        if range_ is None:
            if type(query) in (list, tuple):
                range_ = "min"

        first = _zdt(_one(query)).ISO8601()
        if range_ == "min":
            return {"range": {name: {"gte": first}}}
        if range_ == "max":
            return {"range": {name: {"lte": first}}}
        if (
            range_ in ("min:max", "minmax")
            and (type(query) in (list, tuple))
            and len(query) == 2
        ):
            return {"range": {name: {"gte": first, "lte": _zdt(query[1]).ISO8601()}}}
        return None

    def extract(self, name, data):
        try:
            return DateTime(super().extract(name, data))
        except Exception:  # NOQA W0703
            return None


class TZCTextIndex(BaseIndex):
    filter_query = False

    def create_mapping(self, name):
        return {"type": "text", "index": True, "store": False}

    def get_value(self, obj):
        try:
            fields = self.index._indexed_attrs
        except Exception:  # NOQA W0703
            fields = [self.index._fieldname]
        all_texts = []
        for attr in fields:
            text = getattr(obj, attr, None)
            if text is None:
                continue
            if safe_callable(text):
                text = text()
            if text is None:
                continue
            if text:
                if isinstance(
                    text,
                    (
                        list,
                        tuple,
                    ),
                ):
                    all_texts.extend(text)
                else:
                    all_texts.append(text)
        # Check that we're sending only strings
        all_texts = filter(lambda text: isinstance(text, str), all_texts)
        if all_texts:
            return "\n".join(all_texts)
        return None

    def get_query(self, name, value):
        value = self._normalize_query(value)
        # ES doesn't care about * like zope catalog does
        clean_value = value.strip("*") if value else ""
        queries = [{"match_phrase": {name: {"query": clean_value, "slop": 2}}}]
        if name in ("Title", "SearchableText"):
            # titles have most importance... we override here...
            queries.append(
                {"match_phrase_prefix": {"Title": {"query": clean_value, "boost": 2}}}
            )
        if name != "Title":
            queries.append({"match": {name: {"query": clean_value}}})

        return queries


class TBooleanIndex(BaseIndex):
    def create_mapping(self, name):
        return {"type": "boolean"}


class TUUIDIndex(BaseIndex):
    pass


class TExtendedPathIndex(BaseIndex):
    filter_query = True

    def create_mapping(self, name):
        return {
            "properties": {
                "path": {"type": "keyword", "index": True, "store": True},
                "depth": {"type": "integer", "store": True},
            }
        }

    def get_value(self, obj):
        attrs = self.index.indexed_attrs
        index = self.index.id if attrs is None else attrs[0]
        path = getattr(obj, index, None)
        if path is not None:
            if safe_callable(path):
                path = path()
            if not isinstance(path, (str, tuple)):
                raise TypeError(
                    f"path value must be string or tuple of "
                    f"strings: ({index}, {repr(path)})"
                )
        else:
            try:
                path = obj.getPhysicalPath()
            except AttributeError:
                return None
        return "/".join(path)

    def extract(self, name, data):
        return data[name]["path"]

    def get_query(self, name, value):
        if isinstance(value, str):
            paths = value
            depth = -1
            navtree = False
            navtree_start = 0
        else:
            depth = value.get("depth", -1)
            paths = value.get("query")
            navtree = value.get("navtree", False)
            navtree_start = value.get("navtree_start", 0)
        if not paths:
            return None
        if isinstance(paths, str):
            paths = [paths]
        andfilters = []
        for path in paths:
            spath = path.split("/")
            gtcompare = "gt"
            start = len(spath) - 1
            if navtree:
                start = start + navtree_start
                end = navtree_start + depth
            else:
                end = start + depth
            if navtree or depth == -1:
                gtcompare = "gte"
            filters = []
            if depth == 0:
                andfilters.append(
                    {"bool": {"filter": {"term": {f"{name}.path": path}}}}
                )
                continue
            filters = [
                {"prefix": {f"{name}.path": path}},
                {"range": {f"{name}.depth": {gtcompare: start}}},
            ]
            if depth != -1:
                filters.append({"range": {f"{name}.depth": {"lte": end}}})
            andfilters.append({"bool": {"must": filters}})
        if len(andfilters) > 1:
            return {"bool": {"should": andfilters}}
        return andfilters[0]


class TGopipIndex(BaseIndex):
    def create_mapping(self, name):
        return {"type": "integer", "store": True}

    def get_value(self, obj):
        parent = aq_parent(obj)
        if hasattr(parent, "getObjectPosition"):
            return parent.getObjectPosition(obj.getId())
        return None


class TDateRangeIndex(BaseIndex):
    def create_mapping(self, name):
        return {
            "properties": {
                f"{name}1": {"type": "date", "store": True},
                f"{name}2": {"type": "date", "store": True},
            }
        }

    def get_value(self, obj):
        if self.index._since_field is None:
            return None
        since = getattr(obj, self.index._since_field, None)
        if safe_callable(since):
            since = since()
        until = getattr(obj, self.index._until_field, None)
        if safe_callable(until):
            until = until()
        if not since or not until:
            return None
        return {
            f"{self.index.id}1": since.strftime("%s"),
            f"{self.index.id}2": until.strftime("%s"),
        }

    def get_query(self, name, value):
        value = self._normalize_query(value)
        date_iso = value.ISO8601()
        return [
            {"range": {f"{name}.{name}1": {"lte": date_iso}}},
            {"range": {f"{name}.{name}2": {"gte": date_iso}}},
        ]


class TRecurringIndex(TDateIndex):
    pass


INDEX_MAPPING = {
    KeywordIndex: TKeywordIndex,
    FieldIndex: TFieldIndex,
    DateIndex: TDateIndex,
    ZCTextIndex: TZCTextIndex,
    BooleanIndex: TBooleanIndex,
    UUIDIndex: TUUIDIndex,
    ExtendedPathIndex: TExtendedPathIndex,
    GopipIndex: TGopipIndex,
    DateRangeIndex: TDateRangeIndex,
}

try:
    from Products.DateRecurringIndex.index import DateRecurringIndex  # NOQA C0412

    INDEX_MAPPING[DateRecurringIndex] = TRecurringIndex
except ImportError:
    pass



